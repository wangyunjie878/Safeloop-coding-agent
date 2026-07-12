.PHONY: test demo web

test:
	python -m pytest

demo:
	python -m safeloop demo

web:
	python -m safeloop web --host 0.0.0.0 --port 8000

