"""Load test orchestrator."""

import asyncio
import time
from dataclasses import dataclass
from typing import List

from .client import SimulatedClient, ClientConfig, ClientMetrics


@dataclass
class LoadTestConfig:
    """Configuration for load test."""

    server_url: str = "wss://localhost:5000/ws"
    num_clients: int = 10
    duration: int = 60  # seconds
    message_rate: float = 1.0  # per client per second
    connect_delay: float = 0.1  # stagger connections
    include_deletions: bool = False
    verify_ssl: bool = False


@dataclass
class LoadTestResults:
    """Aggregated results from load test."""

    total_clients: int
    successful_connects: int
    total_messages_sent: int
    total_messages_received: int
    total_errors: int
    avg_connect_time_ms: float
    avg_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    messages_per_second: float
    duration_seconds: float


class LoadTestRunner:
    """Orchestrates load testing with multiple simulated clients."""

    def __init__(self, config: LoadTestConfig):
        self.config = config
        self.clients: List[SimulatedClient] = []
        self.results: List[ClientMetrics] = []

    async def run(self) -> LoadTestResults:
        """Run load test and return aggregated results."""
        print(f"Starting load test:")
        print(f"  Clients: {self.config.num_clients}")
        print(f"  Duration: {self.config.duration}s")
        print(f"  Message rate: {self.config.message_rate}/s per client")
        print(f"  Server: {self.config.server_url}")
        print()

        start_time = time.time()

        # Create and start clients with staggered connections
        tasks = []
        for i in range(self.config.num_clients):
            client = SimulatedClient(ClientConfig(
                server_url=self.config.server_url,
                station_name=f"LoadTest-{i + 1:04d}",
                message_rate=self.config.message_rate,
                include_deletions=self.config.include_deletions,
                verify_ssl=self.config.verify_ssl,
            ))
            self.clients.append(client)
            tasks.append(asyncio.create_task(client.run(self.config.duration)))

            # Progress indicator
            if (i + 1) % 10 == 0 or i == self.config.num_clients - 1:
                print(f"  Started {i + 1}/{self.config.num_clients} clients...")

            if self.config.connect_delay > 0 and i < self.config.num_clients - 1:
                await asyncio.sleep(self.config.connect_delay)

        print()
        print("All clients started. Running test...")
        print()

        # Wait for all clients to complete
        self.results = await asyncio.gather(*tasks)

        elapsed = time.time() - start_time
        return self._aggregate_results(elapsed)

    def _aggregate_results(self, elapsed: float) -> LoadTestResults:
        """Aggregate individual client metrics."""
        all_latencies = []
        total_sent = 0
        total_received = 0
        total_errors = 0
        connect_times = []
        successful = 0

        for m in self.results:
            total_sent += m.messages_sent
            total_received += m.messages_received
            total_errors += m.errors
            all_latencies.extend(m.latencies)

            if m.connect_time_ms > 0:
                connect_times.append(m.connect_time_ms)
                successful += 1

        # Sort latencies for percentile calculation
        all_latencies.sort()

        def percentile(data: List[float], p: float) -> float:
            if not data:
                return 0.0
            idx = int(len(data) * p / 100)
            return data[min(idx, len(data) - 1)]

        return LoadTestResults(
            total_clients=self.config.num_clients,
            successful_connects=successful,
            total_messages_sent=total_sent,
            total_messages_received=total_received,
            total_errors=total_errors,
            avg_connect_time_ms=sum(connect_times) / len(connect_times) if connect_times else 0,
            avg_latency_ms=sum(all_latencies) / len(all_latencies) if all_latencies else 0,
            p50_latency_ms=percentile(all_latencies, 50),
            p95_latency_ms=percentile(all_latencies, 95),
            p99_latency_ms=percentile(all_latencies, 99),
            messages_per_second=total_sent / elapsed if elapsed > 0 else 0,
            duration_seconds=elapsed,
        )
