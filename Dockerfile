FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*

COPY agent/ /app/agent/
COPY collector/ /app/collector/
COPY alerting/ /app/alerting/
COPY cli/ /app/cli/
COPY demo/ /app/demo/
COPY storage/ /app/storage/
COPY dashboards/ /app/dashboards/
COPY pyproject.toml /app/

RUN pip install --no-cache-dir -e /app/agent/ -e /app/.

EXPOSE 9100 9101

ENTRYPOINT ["python", "-m", "cli.main"]
CMD ["--help"]