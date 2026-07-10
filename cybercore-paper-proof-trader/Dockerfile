FROM python:3.11-slim

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
COPY config ./config

RUN pip install --no-cache-dir .

ENV PYTHONUNBUFFERED=1
CMD ["python", "-m", "cybercore_trader.cli", "run-loop"]
