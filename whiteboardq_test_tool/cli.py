"""WhiteboardQ Test Tool CLI."""

import asyncio
from pathlib import Path

import click


@click.group()
@click.version_option(version="1.0.0")
def cli():
    """WhiteboardQ Test Tool - Load testing."""
    pass


# =============================================================================
# Load Test Commands
# =============================================================================

@cli.group()
def load():
    """Load testing commands."""
    pass


@load.command()
@click.option("--clients", "-c", default=10, help="Number of simulated clients")
@click.option("--duration", "-d", default=60, help="Test duration in seconds")
@click.option("--server", "-s", default="wss://localhost:5000/ws", help="Server WebSocket URL")
@click.option("--message-rate", "-r", default=1.0, help="Messages per second per client")
@click.option("--connect-delay", default=0.1, help="Delay between client connections")
@click.option("--include-deletions", is_flag=True, help="Include delete operations")
@click.option("--no-verify-ssl", is_flag=True, help="Disable SSL verification")
def run(clients, duration, server, message_rate, connect_delay, include_deletions, no_verify_ssl):
    """Run load test with specified parameters."""
    from .load.runner import LoadTestRunner, LoadTestConfig

    config = LoadTestConfig(
        server_url=server,
        num_clients=clients,
        duration=duration,
        message_rate=message_rate,
        connect_delay=connect_delay,
        include_deletions=include_deletions,
        verify_ssl=not no_verify_ssl,
    )

    runner = LoadTestRunner(config)
    results = asyncio.run(runner.run())

    click.echo("")
    click.echo("=" * 50)
    click.echo("LOAD TEST RESULTS")
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


@load.command()
@click.argument("name")
@click.option("--server", "-s", default="wss://localhost:5000/ws", help="Server WebSocket URL")
@click.option("--no-verify-ssl", is_flag=True, help="Disable SSL verification")
def scenario(name, server, no_verify_ssl):
    """Run a pre-defined test scenario."""
    from .load.scenarios import SCENARIOS, run_scenario

    if name not in SCENARIOS:
        click.echo(f"Unknown scenario: {name}", err=True)
        click.echo(f"Available: {', '.join(SCENARIOS.keys())}")
        return

    click.echo(f"Running scenario: {name}")
    click.echo(f"Description: {SCENARIOS[name]['description']}")
    click.echo("")

    asyncio.run(run_scenario(name, server, verify_ssl=not no_verify_ssl))


@load.command("scenarios")
def list_scenarios():
    """List available test scenarios."""
    from .load.scenarios import SCENARIOS

    click.echo("Available scenarios:")
    click.echo("")
    for name, info in SCENARIOS.items():
        click.echo(f"  {name:12} - {info['description']}")
        click.echo(f"               Clients: {info['clients']}, Duration: {info['duration']}s, Rate: {info['message_rate']} msg/s")
        click.echo("")


if __name__ == "__main__":
    cli()
