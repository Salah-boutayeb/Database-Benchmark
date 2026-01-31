"""
Docker Resource Monitor - Reusable component for monitoring container resources.
"""
import subprocess
import threading
import time
import re
from typing import Dict, List


def get_docker_stats(container_name: str) -> Dict[str, float]:
    """Get real-time CPU and Memory usage from Docker container."""
    try:
        result = subprocess.run(
            ["docker", "stats", container_name, "--no-stream", "--format",
             "{{.CPUPerc}},{{.MemUsage}},{{.MemPerc}}"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            parts = result.stdout.strip().split(',')
            cpu_percent = float(parts[0].replace('%', ''))
            mem_usage = parts[1].split('/')[0].strip()
            mem_percent = float(parts[2].replace('%', ''))

            mem_value = float(re.findall(r'[\d.]+', mem_usage)[0])
            if 'GiB' in mem_usage:
                mem_value *= 1024

            return {"cpu": cpu_percent, "mem_mb": mem_value, "mem_percent": mem_percent}
    except Exception:
        pass
    return {"cpu": 0, "mem_mb": 0, "mem_percent": 0}


class DockerResourceMonitor(threading.Thread):
    """Monitor Docker container resources during benchmark operations."""

    def __init__(self, container_name: str, interval: float = 0.5):
        super().__init__()
        self.container_name = container_name
        self.interval = interval
        self.running = True
        self.cpu_usages: List[float] = []
        self.memory_usages_mb: List[float] = []
        self.memory_usages_percent: List[float] = []

    def run(self) -> None:
        while self.running:
            stats = get_docker_stats(self.container_name)
            self.cpu_usages.append(stats["cpu"])
            self.memory_usages_mb.append(stats["mem_mb"])
            self.memory_usages_percent.append(stats["mem_percent"])
            time.sleep(self.interval)

    def stop(self) -> Dict[str, float]:
        """Stop monitoring and return aggregated statistics."""
        self.running = False
        self.join()

        avg_cpu = sum(self.cpu_usages) / len(self.cpu_usages) if self.cpu_usages else 0
        max_cpu = max(self.cpu_usages) if self.cpu_usages else 0
        avg_mem_mb = sum(self.memory_usages_mb) / len(self.memory_usages_mb) if self.memory_usages_mb else 0
        max_mem_mb = max(self.memory_usages_mb) if self.memory_usages_mb else 0
        avg_mem_pct = sum(self.memory_usages_percent) / len(self.memory_usages_percent) if self.memory_usages_percent else 0

        return {
            "container_cpu_avg": round(avg_cpu, 2),
            "container_cpu_max": round(max_cpu, 2),
            "container_mem_avg_mb": round(avg_mem_mb, 2),
            "container_mem_max_mb": round(max_mem_mb, 2),
            "container_mem_avg_percent": round(avg_mem_pct, 2)
        }
