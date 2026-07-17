from __future__ import annotations

from collections.abc import Callable
from enum import StrEnum

from safeloop.actions import ActionParseError, parse_action
from safeloop.config import HarnessConfig, collect_runtime_redaction_secrets
from safeloop.events import EventLogStore
from safeloop.feedback import FeedbackClassifier
from safeloop.llm.base import LLMClient, LLMRequest
from safeloop.models import AgentAction, Event, Feedback, GuardrailDecision, RunRecord, ToolResult
from safeloop.run_manager import RunManager
from safeloop.security.guardrails import GuardrailEngine
from safeloop.tools.dispatcher import ToolDispatcher
from safeloop.tools.memory import MemoryStore
from safeloop.tools.base import ToolContext


class StopReason(StrEnum):
    MAX_STEPS = "max_steps"
    PARSE_ERRORS = "parse_errors"


ApprovalCallback = Callable[[AgentAction, GuardrailDecision], bool]


class AgentStateMachine:
    def __init__(
        self,
        run_manager: RunManager,
        event_store: EventLogStore,
        llm_client: LLMClient,
        feedback_classifier: FeedbackClassifier | None = None,
        approval_callback: ApprovalCallback | None = None,
    ) -> None:
        self._run_manager = run_manager
        self._event_store = event_store
        self._llm_client = llm_client
        self._feedback_classifier = feedback_classifier or FeedbackClassifier()
        self._approval_callback = approval_callback

    def run(self, task: str, config: HarnessConfig) -> RunRecord:
        run = self._run_manager.create_run(task, config)
        self._run_manager.update_status(run.id, "running")
        feedback: list[Feedback] = []
        parse_errors = 0
        known_secrets = collect_runtime_redaction_secrets(config)
        self._event_store.add_known_secrets(known_secrets)
        memory_store = MemoryStore(
            config.workspace,
            known_secrets=known_secrets,
        )

        try:
            for step in range(1, config.max_steps + 1):
                run = self._run_manager.update_step(run.id, step)
                dispatcher = ToolDispatcher(ToolContext(config=config, run_id=run.id, step=step))
                request = LLMRequest(
                    task=task,
                    feedback=feedback,
                    memories=memory_store.query(scope="project"),
                    events=self._event_store.list(run.id),
                    tool_schemas=dispatcher.tool_schemas(),
                    known_secrets=known_secrets,
                )
                raw_action = self._llm_client.complete(request)
                self._append_event(run.id, step, "llm_action", {"raw": raw_action})

                try:
                    action = parse_action(raw_action, dispatcher.available_tools())
                except ActionParseError as exc:
                    parse_errors += 1
                    item = self._feedback_classifier.from_parse_error(str(exc), known_secrets=known_secrets)
                    feedback.append(item)
                    self._append_feedback(run.id, step, item)
                    if parse_errors >= 2:
                        return self._stop(run.id, step, StopReason.PARSE_ERRORS)
                    continue

                parse_errors = 0
                self._append_event(run.id, step, "llm_action", {"action": action.model_dump(mode="json")})
                decision = GuardrailEngine(config).evaluate(action)
                self._append_guardrail(run.id, step, decision)
                if decision.decision == "deny":
                    item = self._feedback_classifier.from_guardrail(decision, known_secrets=known_secrets)
                    feedback.append(item)
                    self._append_feedback(run.id, step, item)
                    continue
                if decision.decision == "require_approval":
                    approved = self._approval_callback(action, decision) if self._approval_callback is not None else False
                    self._append_event(
                        run.id,
                        step,
                        "approval_decision",
                        {
                            "approved": approved,
                            "tool_name": action.tool_name,
                            "matched_rule": decision.matched_rule,
                        },
                    )
                    if not approved:
                        item = self._feedback_classifier.from_guardrail(decision, known_secrets=known_secrets)
                        feedback.append(item)
                        self._append_feedback(run.id, step, item)
                        continue
                    dispatcher = ToolDispatcher(
                        ToolContext(config=config, run_id=run.id, step=step, approval_granted=True)
                    )

                result = dispatcher.dispatch(action)
                self._append_tool_result(run.id, step, result)
                if action.tool_name == "finish" and result.success:
                    self._append_event(run.id, step, "finished", {"message": result.stdout})
                    return self._run_manager.update_status(run.id, "finished", reason="finish")
                if not result.success:
                    item = self._feedback_classifier.from_tool_result(result, known_secrets=known_secrets)
                    feedback.append(item)
                    self._append_feedback(run.id, step, item)

            return self._stop(run.id, config.max_steps, StopReason.MAX_STEPS)
        except Exception as exc:  # Boundary errors must leave the run in a terminal state.
            return self._fail(run.id, run.current_step, exc)

    def _stop(self, run_id: str, step: int, reason: StopReason) -> RunRecord:
        self._append_event(run_id, step, "stopped", {"reason": reason.value})
        return self._run_manager.update_status(run_id, "stopped", reason=reason.value)

    def _fail(self, run_id: str, step: int, error: Exception) -> RunRecord:
        self._append_event(
            run_id,
            step,
            "failed",
            {"reason": "boundary_error", "error": f"{type(error).__name__}: {error}"},
        )
        return self._run_manager.update_status(run_id, "failed", reason="boundary_error")

    def _append_feedback(self, run_id: str, step: int, feedback: Feedback) -> None:
        self._append_event(run_id, step, "feedback_added", feedback.model_dump(mode="json"))

    def _append_guardrail(self, run_id: str, step: int, decision: GuardrailDecision) -> None:
        self._append_event(run_id, step, "guardrail_decision", decision.model_dump(mode="json"))

    def _append_tool_result(self, run_id: str, step: int, result: ToolResult) -> None:
        self._append_event(run_id, step, "tool_result", result.model_dump(mode="json"))

    def _append_event(self, run_id: str, step: int, event_type: str, payload: dict[str, object]) -> None:
        self._event_store.append(Event(run_id=run_id, step=step, type=event_type, payload=payload))
