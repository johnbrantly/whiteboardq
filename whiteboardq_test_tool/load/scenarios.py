"""Pre-defined load test scenarios."""

import asyncio

import click

from .runner import LoadTestRunner, LoadTestConfig


SCENARIOS = {
    "burst": {
        "description": "50 clients connect simultaneously, 10 msgs each",
        "clients": 50,
        "duration": 30,
        "connect_delay": 0,
        "message_rate": 2.0,
    },
    "gradual": {
        "description": "20 clients join over 60 seconds, steady messaging",
        "clients": 20,
        "duration": 120,
        "connect_delay": 3.0,
        "message_rate": 0.5,
    },
    "churn": {
        "description": "30 clients with rapid connect/disconnect pattern",
        "clients": 30,
        "duration": 60,
        "connect_delay": 0.5,
        "message_rate": 1.0,
    },
    "heavy": {
        "description": "10 clients, high message volume (5 msg/sec each)",
        "clients": 10,
        "duration": 60,
        "connect_delay": 0.2,
        "message_rate": 5.0,
    },
    "soak": {
        "description": "5 clients for 10 minutes, steady load",
        "clients": 5,
        "duration": 600,
        "connect_delay": 1.0,
        "message_rate": 0.2,
    },
    "quick": {
        "description": "Quick test: 3 clients, 10 seconds",
        "clients": 3,
        "duration": 10,
        "connect_delay": 0.1,
        "message_rate": 1.0,
    },
}


async def run_scenario(name: str, server_url: str = "wss://localhost:5000/ws", verify_ssl: bool = False) -> None:
    """Run a pre-defined test scenario."""
    if name not in SCENARIOS:
        raise ValueError(f"Unknown scenario: {name}")

    scenario = SCENARIOS[name]

    config = LoadTestConfig(
        server_url=server_url,
        num_clients=scenario["clients"],
        duration=scenario["duration"],
        message_rate=scenario["message_rate"],
        connect_delay=scenario["connect_delay"],
        include_deletions=False,
        verify_ssl=verify_ssl,
    )

    runner = LoadTestRunner(config)
    results = await runner.run()

    # Print results
    click.echo("")
    click.echo("=" * 50)
    click.echo(f"SCENARIO '{name}' RESULTS")
    click.echo("=" * 50)
    click.echo(f"Clients: {results.successful_connects}/{results.total_clients} connected")
    click.echo(f"Duration: {results.duration_seconds:.1f}s")
    click.echo("")
    click.echo("Messages:")
    click.echo(f"  Sent: {results.total_messages_sent}")
    click.echo(f"  Received: {results.total_messages_received}")
    click.echo(f"  Errors: {results.total_errors}")
    click.echo(f"  Throughput: {results.messages_per_second:.1f} msg/sec")
    click.echo("")
    click.echo("Latency (round-trip):")
    click.echo(f"  Avg: {results.avg_latency_ms:.1f}ms")
    click.echo(f"  P50: {results.p50_latency_ms:.1f}ms")
    click.echo(f"  P95: {results.p95_latency_ms:.1f}ms")
    click.echo(f"  P99: {results.p99_latency_ms:.1f}ms")
    click.echo("")
    click.echo(f"Avg Connect Time: {results.avg_connect_time_ms:.1f}ms")
