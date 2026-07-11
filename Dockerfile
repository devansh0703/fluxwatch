FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*

COPY agent/ /app/agent/
COPY collector/ /app/collector/
COPY alerting/ /app/alerting/
COPY cli/ /app/cli/
COPY demo/ /app/demo/
COPY pyproject.toml /app/

RUN pip install --no-cache-dir /app/agent/ /app/

EXPOSE 9100

CMD ["python", "-m", "collector.pipeline"]
