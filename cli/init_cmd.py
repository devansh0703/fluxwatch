from __future__ import annotations

from pathlib import Path

import click
import yaml


def run_init_wizard(output_dir: str) -> None:
    click.echo("FluxWatch Setup Wizard")
    click.echo("=" * 40)

    service = click.prompt("Service name", default="strategy_alpha")
    env = click.prompt(
        "Environment",
        default="production",
        type=click.Choice(["production", "staging", "demo"]),
    )
    redis_url = click.prompt("Redis URL", default="redis://localhost:6379")
    es_url = click.prompt("Elasticsearch URL", default="http://localhost:9200")
    grafana_url = click.prompt("Grafana URL", default="http://localhost:3000")
    prometheus_url = click.prompt("Prometheus URL", default="http://localhost:9090")
    min_level = click.prompt(
        "Min log level",
        default="info",
        type=click.Choice(["debug", "info", "warning", "error"]),
    )
    format_choice = click.prompt(
        "Log format", default="json", type=click.Choice(["json", "logfmt", "human"])
    )
    sample_rate = (
        click.prompt("Sample rate (0.0-1.0, empty for none)", default="", type=float)
        or None
    )

    slack_webhook = click.prompt("Slack webhook URL (optional)", default="")
    pagerduty_key = click.prompt("PagerDuty routing key (optional)", default="")

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    config = {
        "service": service,
        "env": env,
        "redis_url": redis_url,
        "elasticsearch_url": es_url,
        "grafana_url": grafana_url,
        "prometheus_url": prometheus_url,
        "min_level": min_level,
        "format": format_choice,
        "sample_rate": sample_rate,
        "channels": {},
    }
    if slack_webhook:
        config["channels"]["slack"] = {
            "webhook_url": slack_webhook,
            "channel": "#alerts",
        }
    if pagerduty_key:
        config["channels"]["pagerduty"] = {"routing_key": pagerduty_key}

    with open(out / "fluxwatch.yaml", "w") as f:
        yaml.dump(config, f, default_flow_style=False)

    env_file = out / ".env"
    with open(env_file, "w") as f:
        f.write(f"FLUXWATCH_SERVICE={service}\n")
        f.write(f"FLUXWATCH_ENV={env}\n")
        f.write(f"FLUXWATCH_REDIS_URL={redis_url}\n")
        f.write(f"FLUXWATCH_ES_URL={es_url}\n")
        f.write(f"FLUXWATCH_MIN_LEVEL={min_level}\n")
        f.write(f"FLUXWATCH_FORMAT={format_choice}\n")
        if sample_rate:
            f.write(f"FLUXWATCH_SAMPLE_RATE={sample_rate}\n")

    click.echo(f"\nConfiguration written to {out / 'fluxwatch.yaml'}")
    click.echo(f"Environment variables written to {env_file}")
    click.echo("\nNext steps:")
    click.echo(f"  1. Review {out / 'fluxwatch.yaml'}")
    click.echo("  2. Copy .env to your deployment")
    click.echo("  3. Run: docker compose up -d")
