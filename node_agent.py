#!/usr/bin/env python3
"""
NETSCAPE — Antifragile Node Agent (Phase 2)
Runs on worker nodes (e.g., GPD Pocket 4).

Phase 2 — Antifragile design:
  - Agent operates independently if coordinator is unreachable
  - Local Ollama inference always works, coordinator is optimization layer
  - GPU detection from Ollama's own backend reporting (not rocminfo)
  - Live metrics (CPU, RAM, GPU) sent with each heartbeat
  - Graceful join/leave with automatic re-announce on coordinator amnesia
"""

import asyncio
import json
import os
import signal
import subprocess
import logging
import platform
from pathlib import Path
from aiohttp import web, ClientSession, ClientTimeout

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [NETSCAPE-AGENT] %(message)s",
    datefmt="%H:%M:%S"
)
log = logging.getLogger("netscape-agent")

# --- Configuration ---

AGENT_CONFIG_PATH = Path.home() / ".netscape" / "agent.json"
FALLBACK_LOG_PATH = Path.home() / ".netscape" / "fallback.log"

DEFAULT_AGENT_CONFIG = {
    "coordinator_ip": "",
    "coordinator_port": 7070,
    "node_id": "",
    "hardware": "",
    "ollama_port": 11434,
    "heartbeat_interval_sec": 10,
    "inference_backend": "ollama",
    "local_fallback_port": 7071,  # local API when coordinator is down
    "capabilities": {
        "gpu": False,
        "gpu_name": "",
        "vram_mb": 0,
        "ram_gb": 32,
    }
}


def load_agent_config() -> dict:
    if AGENT_CONFIG_PATH.exists():
        with open(AGENT_CONFIG_PATH) as f:
            return {**DEFAULT_AGENT_CONFIG, **json.load(f)}
    AGENT_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(AGENT_CONFIG_PATH, "w") as f:
        json.dump(DEFAULT_AGENT_CONFIG, f, indent=2)
    log.warning(f"Created config at {AGENT_CONFIG_PATH}")
    log.warning("Set coordinator_ip to join the mesh (optional — works standalone)")
    return DEFAULT_AGENT_CONFIG.copy()


def get_tailscale_ip() -> str:
    try:
        result = subprocess.run(
            ["tailscale", "ip", "-4"],
            capture_output=True, text=True, timeout=5
        )
        ip = result.stdout.strip()
        if ip:
            return ip
    except Exception:
        pass
    try:
        result = subprocess.run(
            ["tailscale", "status", "--json"],
            capture_output=True, text=True, timeout=5
        )
        data = json.loads(result.stdout)
        self_ip = data.get("Self", {}).get("TailscaleIPs", [None])[0]
        if self_ip:
            return self_ip
    except Exception:
        pass
    raise RuntimeError("Cannot determine Tailscale IP")


def get_hostname() -> str:
    return platform.node().split(".")[0].lower()


# --- System Metrics Collection ---

class MetricsCollector:
    """Lightweight system metrics — no external dependencies."""

    @staticmethod
    def cpu_util() -> float:
        """CPU utilization from /proc/stat (Linux only)."""
        try:
            with open("/proc/stat") as f:
                line = f.readline()
            parts = line.split()
            idle = int(parts[4])
            total = sum(int(p) for p in parts[1:])
            # We need two readings — approximate with single read
            # Better: track between heartbeats
            return min(1.0, max(0.0, 1.0 - (idle / max(total, 1))))
        except Exception:
            return 0.0

    @staticmethod
    def ram_available_gb() -> float:
        """Available RAM in GB from /proc/meminfo."""
        try:
            with open("/proc/meminfo") as f:
                for line in f:
                    if line.startswith("MemAvailable:"):
                        kb = int(line.split()[1])
                        return round(kb / (1024 * 1024), 1)
        except Exception:
            pass
        return 0.0

    @staticmethod
    def detect_gpu_from_ollama(ollama_port: int = 11434) -> dict:
        """
        Detect GPU capability by checking Ollama's /api/version or logs.
        Let the inference engine be the source of truth.
        """
        gpu_info = {"gpu": False, "gpu_name": "", "backend": "cpu"}

        # Method 1: Check Ollama process for GPU environment vars
        ollama_env = os.environ.get("OLLAMA_VULKAN", "")
        if ollama_env == "1":
            gpu_info["gpu"] = True
            gpu_info["backend"] = "vulkan"

        # Method 2: Check journalctl for Ollama GPU detection logs
        try:
            result = subprocess.run(
                ["journalctl", "-u", "ollama", "--no-pager", "-n", "50",
                 "--output", "cat"],
                capture_output=True, text=True, timeout=5
            )
            output = result.stdout.lower()

            if "vulkan" in output and "gpu" in output:
                gpu_info["gpu"] = True
                gpu_info["backend"] = "vulkan"
            elif "rocm" in output:
                gpu_info["gpu"] = True
                gpu_info["backend"] = "rocm"
            elif "cuda" in output:
                gpu_info["gpu"] = True
                gpu_info["backend"] = "cuda"

            # Try to extract GPU name
            for line in result.stdout.split("\n"):
                if "gpu" in line.lower() and ("radeon" in line.lower()
                                              or "nvidia" in line.lower()
                                              or "amd" in line.lower()):
                    gpu_info["gpu_name"] = line.strip()[:80]
                    break
        except Exception:
            pass

        return gpu_info

    @staticmethod
    def is_ollama_busy(ollama_port: int = 11434) -> bool:
        """Check if Ollama is currently running inference (non-async check)."""
        try:
            result = subprocess.run(
                ["curl", "-s", "-m", "2",
                 f"http://localhost:{ollama_port}/api/ps"],
                capture_output=True, text=True, timeout=3
            )
            if result.returncode == 0:
                data = json.loads(result.stdout)
                models = data.get("models", [])
                return len(models) > 0
        except Exception:
            pass
        return False

    def collect(self, ollama_port: int = 11434) -> dict:
        """Collect all metrics for heartbeat."""
        gpu_info = self.detect_gpu_from_ollama(ollama_port)
        return {
            "cpu_util": round(self.cpu_util(), 2),
            "ram_available_gb": self.ram_available_gb(),
            "gpu_available": gpu_info["gpu"],
            "gpu_util": 0.0,  # TODO: parse from GPU-specific tools if needed
            "gpu_vram_free_mb": 0,
            "inference_active": self.is_ollama_busy(ollama_port),
        }


# --- Local Fallback Server ---

class LocalFallbackServer:
    """
    Minimal local inference API that works without the coordinator.
    If coordinator is down, this node can still serve inference directly.
    """

    def __init__(self, ollama_port: int, fallback_port: int):
        self.ollama_port = ollama_port
        self.fallback_port = fallback_port
        self.app = web.Application()
        self.app.router.add_post("/infer", self.handle_infer)
        self.app.router.add_get("/health", self.handle_health)

    async def handle_infer(self, request: web.Request) -> web.Response:
        """Direct local inference — no routing, just forward to local Ollama."""
        data = await request.json()
        model = data.get("model", "")
        prompt = data.get("prompt", "")
        context = data.get("context", "")

        if not model or not prompt:
            return web.json_response(
                {"error": "model and prompt required"}, status=400
            )

        # Log fallback usage for later analysis
        self._log_fallback(model)

        ollama_url = f"http://localhost:{self.ollama_port}/api/generate"
        payload = {"model": model, "prompt": prompt, "stream": False}
        if context:
            payload["system"] = context

        timeout = ClientTimeout(total=120)
        try:
            async with ClientSession(timeout=timeout) as session:
                async with session.post(ollama_url, json=payload) as resp:
                    if resp.status == 200:
                        body = await resp.json()
                        return web.json_response({
                            "response": body.get("response", ""),
                            "routed_to": "local_fallback",
                            "model": model,
                            "fallback": True,
                        })
                    else:
                        err = await resp.text()
                        return web.json_response(
                            {"error": f"Local Ollama error: {err}"}, status=502
                        )
        except Exception as e:
            return web.json_response(
                {"error": f"Local Ollama unreachable: {e}"}, status=503
            )

    async def handle_health(self, request: web.Request) -> web.Response:
        return web.json_response({
            "mode": "local_fallback",
            "ollama_port": self.ollama_port,
        })

    def _log_fallback(self, model: str):
        try:
            FALLBACK_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
            import time
            entry = {"ts": time.time(), "model": model, "reason": "coordinator_unreachable"}
            with open(FALLBACK_LOG_PATH, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception:
            pass

    async def start(self):
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", self.fallback_port)
        await site.start()
        log.info(f"Local fallback API on :{self.fallback_port}")


# --- Agent ---

class NetscapeAgent:
    def __init__(self, config: dict):
        self.config = config
        self.node_id = config["node_id"] or get_hostname()
        self.tailscale_ip = ""
        self.coordinator_url = ""
        self.coordinator_reachable = False
        self._running = True
        self.metrics = MetricsCollector()

    async def start(self):
        """Main agent lifecycle — works with or without coordinator."""

        # Start local fallback server immediately (antifragile: always available)
        fallback = LocalFallbackServer(
            self.config["ollama_port"],
            self.config["local_fallback_port"]
        )
        await fallback.start()

        # Detect GPU from Ollama's own reporting
        gpu_info = MetricsCollector.detect_gpu_from_ollama(self.config["ollama_port"])
        if gpu_info["gpu"]:
            self.config["capabilities"]["gpu"] = True
            self.config["capabilities"]["gpu_name"] = gpu_info.get("gpu_name", "")
            log.info(f"GPU detected via Ollama: {gpu_info['backend']} — {gpu_info.get('gpu_name', 'unknown')}")
        else:
            log.info("No GPU detected by Ollama — CPU inference mode")

        # Try to get Tailscale IP (non-fatal if it fails)
        try:
            self.tailscale_ip = await self._wait_for_tailscale(max_retries=10)
        except RuntimeError:
            log.warning("Tailscale not available — running in standalone mode")
            self.tailscale_ip = "127.0.0.1"

        # Set up coordinator connection if configured
        if self.config["coordinator_ip"]:
            self.coordinator_url = (
                f"http://{self.config['coordinator_ip']}:{self.config['coordinator_port']}"
            )
            log.info(f"Coordinator target: {self.coordinator_url}")
        else:
            log.info("No coordinator configured — standalone mode")

        log.info(f"Node: {self.node_id} | IP: {self.tailscale_ip} | "
                 f"Fallback: :{self.config['local_fallback_port']}")

        # Signal handlers
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(
                sig, lambda: asyncio.create_task(self.shutdown())
            )

        # Try to join mesh (non-fatal)
        if self.coordinator_url:
            await self._announce()

        # Heartbeat loop
        while self._running:
            await asyncio.sleep(self.config["heartbeat_interval_sec"])
            if self._running and self.coordinator_url:
                await self._heartbeat()

    async def _wait_for_tailscale(self, max_retries: int = 30) -> str:
        for i in range(max_retries):
            try:
                ip = get_tailscale_ip()
                log.info(f"Tailscale online: {ip}")
                return ip
            except RuntimeError:
                log.info(f"Waiting for Tailscale... ({i+1}/{max_retries})")
                await asyncio.sleep(2)
        raise RuntimeError("Tailscale timeout")

    async def _announce(self):
        payload = {
            "node_id": self.node_id,
            "tailscale_ip": self.tailscale_ip,
            "role": "worker",
            "hardware": self.config["hardware"],
            "inference_backend": self.config["inference_backend"],
            "ollama_port": self.config["ollama_port"],
            "capabilities": self.config["capabilities"],
        }

        timeout = ClientTimeout(total=10)
        try:
            async with ClientSession(timeout=timeout) as session:
                async with session.post(
                    f"{self.coordinator_url}/join", json=payload
                ) as resp:
                    data = await resp.json()
                    self.coordinator_reachable = True
                    log.info(f"JOINED mesh: {data}")
        except Exception as e:
            self.coordinator_reachable = False
            log.warning(f"Coordinator unreachable: {e}")
            log.info("Operating in standalone mode — local fallback active")

    async def _heartbeat(self):
        # Collect live metrics
        current_metrics = self.metrics.collect(self.config["ollama_port"])

        payload = {
            "node_id": self.node_id,
            "metrics": current_metrics,
        }

        timeout = ClientTimeout(total=5)
        try:
            async with ClientSession(timeout=timeout) as session:
                async with session.post(
                    f"{self.coordinator_url}/heartbeat", json=payload
                ) as resp:
                    if resp.status == 200:
                        if not self.coordinator_reachable:
                            log.info("Coordinator reconnected!")
                        self.coordinator_reachable = True
                    elif resp.status == 404:
                        log.warning("Coordinator forgot us — re-announcing")
                        await self._announce()
        except Exception as e:
            if self.coordinator_reachable:
                log.warning(f"Coordinator lost: {e} — fallback mode active")
            self.coordinator_reachable = False

    async def shutdown(self):
        log.info("Shutting down...")
        self._running = False

        if self.coordinator_url and self.coordinator_reachable:
            payload = {"node_id": self.node_id}
            timeout = ClientTimeout(total=5)
            try:
                async with ClientSession(timeout=timeout) as session:
                    async with session.post(
                        f"{self.coordinator_url}/leave", json=payload
                    ) as resp:
                        log.info(f"Left mesh: {await resp.json()}")
            except Exception:
                log.warning("Could not notify coordinator")


async def main():
    config = load_agent_config()
    agent = NetscapeAgent(config)
    await agent.start()


if __name__ == "__main__":
    asyncio.run(main())
