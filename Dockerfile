FROM python:3.11-slim

WORKDIR /app
COPY . .
RUN python -m pip install --no-cache-dir .

EXPOSE 8000
CMD ["python", "-m", "safeloop", "web", "--host", "0.0.0.0", "--port", "8000"]
