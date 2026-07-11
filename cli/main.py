from __future__ import annotations

import click
import sys


@click.group()
@click.version_option(version="0.1.0")
def cli() -> None:
    """FluxWatch - Trading System Observability Platform"""
    pass


@cli.command()
@click.option("--output", "-o", default=".", help="Output directory for fluxwatch config")
def init(output: str) -> None:
    """Interactive setup wizard for FluxWatch."""
    from cli.init_cmd import run_init_wizard
    run_init_wizard(output)


@cli.command()
@click.option("--redis-url", envvar="FLUXWATCH_REDIS_URL", default="redis://localhost:6379")
@click.option("--es-url", envvar="FLUXWATCH_ES_URL", default="http://localhost:9200")
def status(redis_url: str, es_url: str) -> None:
    """Check connections to Redis, Elasticsearch, Prometheus."""
    import asyncio
    asyncio.run(_check_status(redis_url, es_url))


async def _check_status(redis_url: str, es_url: str) -> None:
    import httpx

    click.echo("FluxWatch Status Check")
    click.echo("=" * 40)

    # Redis
    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url(redis_url, socket_connect_timeout=3)
        await r.ping()
        info = await r.info("server")
        click.echo(f"  Redis:       OK ({info.get('redis_version', '?')})")
        await r.aclose()
    except Exception as e:
        click.echo(f"  Redis:       FAIL ({e})")

    # Elasticsearch
    try:
        async with httpx.AsyncClient(timeout=3) as c:
            resp = await c.get(f"{es_url}/_cluster/health")
            if resp.status_code == 200:
                data = resp.json()
                click.echo(f"  ES:          OK (status={data.get('status', '?')})")
            else:
                click.echo(f"  ES:          FAIL (status={resp.status_code})")
    except Exception as e:
        click.echo(f"  ES:          FAIL ({e})")

    # Prometheus
    try:
        async with httpx.AsyncClient(timeout=3) as c:
            resp = await c.get("http://localhost:9090/-/healthy")
            if resp.status_code == 200:
                click.echo(f"  Prometheus:  OK")
            else:
                click.echo(f"  Prometheus:  FAIL (status={resp.status_code})")
    except Exception as e:
        click.echo(f"  Prometheus:  FAIL ({e})")

    # Grafana
    try:
        async with httpx.AsyncClient(timeout=3) as c:
            resp = await c.get("http://localhost:3000/api/health")
            if resp.status_code == 200:
                click.echo(f"  Grafana:     OK")
            else:
                click.echo(f"  Grafana:     FAIL (status={resp.status_code})")
    except Exception as e:
        click.echo(f"  Grafana:     FAIL ({e})")

    click.echo("=" * 40)


@cli.command()
@click.option("--channel", type=click.Choice(["slack", "pagerduty", "email", "webhook"]), default="webhook")
@click.option("--target", default="http://localhost:9095", help="Channel target URL/address")
def test_alert(channel: str, target: str) -> None:
    """Send a test alert through the specified channel."""
    import asyncio
    asyncio.run(_send_test_alert(channel, target))


async def _send_test_alert(channel: str, target: str) -> None:
    alert = {
        "rule": "test_alert",
        "severity": "warning",
        "message": "This is a test alert from FluxWatch CLI",
        "timestamp": __import__("time").time(),
        "data": {"service": "cli", "test": True},
    }

    click.echo(f"Sending test alert via {channel} to {target}...")

    if channel == "webhook":
        from alerting.channels.webhook import WebhookChannel
        ch = WebhookChannel(url=target)
        await ch.send(alert)
    elif channel == "slack":
        from alerting.channels.slack import SlackChannel
        ch = SlackChannel(webhook_url=target)
        await ch.send(alert)
    elif channel == "pagerduty":
        from alerting.channels.pagerduty import PagerDutyChannel
        ch = PagerDutyChannel(routing_key=target)
        await ch.send(alert)
    elif channel == "email":
        from alerting.channels.email import EmailChannel
        ch = EmailChannel(to_addrs=[target])
        await ch.send(alert)

    click.echo("Alert sent successfully.")


if __name__ == "__main__":
    cli()
