#!/usr/bin/env python3
"""
NETSCAPE — Coordinator Service (Phase 2)
Runs on ThinkCentre (always-on coordinator node).

Phase 2:
  - Two-step routing: filter by capability THEN score
  - GPU/load-aware scoring via heartbeat metrics
  - Context payload forwarding (4K token stub)
  - /infer endpoint — proxied inference with auto-routing
  - Richer /health with last routing decision
  - Routing log (JSONL) for analysis
"""

import asyncio
import json
import time
import logging
from dataclasses import dataclass, field
from pathlib import Path
from aiohttp import web, ClientSession, ClientTimeout

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [NETSCAPE] %(message)s",
    datefmt="%H:%M:%S"
)
log = logging.getLogger("netscape")

# --- Configuration ---

CONFIG_PATH = Path.home() / ".netscape" / "config.json"
STATE_PATH = Path.home() / ".netscape" / "state.json"
ROUTING_LOG_PATH = Path.home() / ".netscape" / "routing.log"

DEFAULT_CONFIG = {
    "coordinator_port": 7070,
    "heartbeat_interval_sec": 15,
    "node_timeout_sec": 45,
    "ollama_port": 11434,
    "max_context_tokens": 4096,
}


def load_config() -> dict:
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            return {**DEFAULT_CONFIG, **json.load(f)}
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(DEFAULT_CONFIG, f, indent=2)
    return DEFAULT_CONFIG.copy()


# --- Data Structures ---

@dataclass
class OllamaModel:
    name: str
    size_gb: float
    quantization: str = ""
    family: str = ""


@dataclass
class NodeMetrics:
    """Live metrics sent with each heartbeat."""
    cpu_util: float = 0.0
    ram_available_gb: float = 0.0
    gpu_available: bool = False
    gpu_util: float = 0.0
    gpu_vram_free_mb: int = 0
    inference_active: bool = False


@dataclass
class Node:
    node_id: str
    tailscale_ip: str
    role: str = "worker"
    hardware: str = ""
    inference_backend: str = "ollama"
    ollama_port: int = 11434
    models: list = field(default_factory=list)
    status: str = "offline"
    last_heartbeat: float = 0.0
    capabilities: dict = field(default_factory=dict)
    metrics: NodeMetrics = field(default_factory=NodeMetrics)


@dataclass
class RoutingDecision:
    timestamp: float = 0.0
    model_requested: str = ""
    node_chosen: str = ""
    score: float = 0.0
    candidates_count: int = 0
    had_context: bool = False


@dataclass
class RoutingTable:
    nodes: dict = field(default_factory=dict)
    last_decision: RoutingDecision = field(default_factory=RoutingDecision)

    def online_nodes(self) -> list:
        return [n for n in self.nodes.values() if n.status == "online"]

    def find_model(self, model_name: str) -> list:
        """STEP 1: Filter — only nodes that HAVE the model."""
        results = []
        for node in self.online_nodes():
            for m in node.models:
                if model_name in m.name:
                    results.append((node, m))
        return results

    def score_node(self, node: Node) -> float:
        """STEP 2: Score — rank among capable nodes."""
        m = node.metrics

        cpu_score = (1.0 - m.cpu_util) * 0.3
        ram_score = min(m.ram_available_gb / 32.0, 1.0) * 0.3

        gpu_score = 0.0
        if m.gpu_available and node.capabilities.get("gpu", False):
            gpu_score = (1.0 - m.gpu_util) * 0.3

        busy_penalty = -0.15 if m.inference_active else 0.0

        staleness = time.time() - node.last_heartbeat
        fresh_score = max(0, 1.0 - (staleness / 60.0)) * 0.1

        return cpu_score + ram_score + gpu_score + fresh_score + busy_penalty

    def best_node_for(self, model_name: str) -> "tuple[Node, float] | None":
        """Two-step routing: filter then score."""
        candidates = self.find_model(model_name)
        if not candidates:
            return None

        scored = [(node, self.score_node(node)) for node, model in candidates]
        scored.sort(key=lambda x: -x[1])
        best_node, best_score = scored[0]

        self.last_decision = RoutingDecision(
            timestamp=time.time(),
            model_requested=model_name,
            node_chosen=best_node.node_id,
            score=best_score,
            candidates_count=len(candidates),
        )
        return (best_node, best_score)


# --- Coordinator Server ---

class NetscapeCoordinator:
    def __init__(self, config: dict):
        self.config = config
        self.table = RoutingTable()
        self.app = web.Application()
        self._setup_routes()

    def _setup_routes(self):
        self.app.router.add_post("/join", self.handle_join)
        self.app.router.add_post("/heartbeat", self.handle_heartbeat)
        self.app.router.add_get("/nodes", self.handle_list_nodes)
        self.app.router.add_get("/route/{model}", self.handle_route)
        self.app.router.add_post("/infer", self.handle_infer)
        self.app.router.add_post("/leave", self.handle_leave)
        self.app.router.add_get("/health", self.handle_health)

    async def handle_join(self, request: web.Request) -> web.Response:
        data = await request.json()
        node_id = data["node_id"]
        capabilities = data.get("capabilities", {})

        node = Node(
            node_id=node_id,
            tailscale_ip=data["tailscale_ip"],
            role=data.get("role", "worker"),
            hardware=data.get("hardware", "unknown"),
            inference_backend=data.get("inference_backend", "ollama"),
            ollama_port=data.get("ollama_port", self.config["ollama_port"]),
            capabilities=capabilities,
            status="online",
            last_heartbeat=time.time(),
        )

        models = await self._probe_ollama(node.tailscale_ip, node.ollama_port)
        node.models = models
        node.metrics.gpu_available = capabilities.get("gpu", False)
        node.metrics.ram_available_gb = capabilities.get("ram_gb", 0)

        self.table.nodes[node_id] = node
        self._save_state()

        log.info(f"NODE JOINED: {node_id} ({node.tailscale_ip})")
        log.info(f"  GPU: {capabilities.get('gpu', False)} | "
                 f"Backend: {node.inference_backend} | "
                 f"RAM: {capabilities.get('ram_gb', '?')}GB | "
                 f"Models: {len(models)}")
        for m in models:
            log.info(f"  └─ {m.name} ({m.size_gb:.1f}GB) [{m.quantization}]")

        return web.json_response({
            "status": "joined",
            "node_id": node_id,
            "models_detected": len(models),
        })

    async def handle_heartbeat(self, request: web.Request) -> web.Response:
        data = await request.json()
        node_id = data["node_id"]

        if node_id not in self.table.nodes:
            return web.json_response({"status": "unknown_node"}, status=404)

        node = self.table.nodes[node_id]
        node.last_heartbeat = time.time()
        node.status = "online"

        if "metrics" in data:
            m = data["metrics"]
            node.metrics = NodeMetrics(
                cpu_util=m.get("cpu_util", 0.0),
                ram_available_gb=m.get("ram_available_gb", 0.0),
                gpu_available=m.get("gpu_available", False),
                gpu_util=m.get("gpu_util", 0.0),
                gpu_vram_free_mb=m.get("gpu_vram_free_mb", 0),
                inference_active=m.get("inference_active", False),
            )

        if data.get("refresh_models", False):
            node.models = await self._probe_ollama(
                node.tailscale_ip, node.ollama_port
            )

        return web.json_response({"status": "ok"})

    async def handle_list_nodes(self, request: web.Request) -> web.Response:
        nodes = {}
        for nid, node in self.table.nodes.items():
            m = node.metrics
            nodes[nid] = {
                "status": node.status,
                "hardware": node.hardware,
                "ip": node.tailscale_ip,
                "backend": node.inference_backend,
                "models": [mod.name for mod in node.models],
                "capabilities": node.capabilities,
                "metrics": {
                    "cpu_util": round(m.cpu_util, 2),
                    "ram_available_gb": round(m.ram_available_gb, 1),
                    "gpu_available": m.gpu_available,
                    "gpu_util": round(m.gpu_util, 2),
                    "inference_active": m.inference_active,
                },
                "score": round(self.table.score_node(node), 3),
                "last_seen": node.last_heartbeat,
            }
        return web.json_response(nodes)

    async def handle_route(self, request: web.Request) -> web.Response:
        model = request.match_info["model"]
        result = self.table.best_node_for(model)

        if result is None:
            return web.json_response({
                "error": f"No online node has model: {model}",
                "available_models": self._all_available_models(),
            }, status=404)

        node, score = result
        self._log_routing(model, node.node_id, score)

        return web.json_response({
            "node_id": node.node_id,
            "tailscale_ip": node.tailscale_ip,
            "ollama_port": node.ollama_port,
            "ollama_url": f"http://{node.tailscale_ip}:{node.ollama_port}",
            "score": round(score, 3),
            "backend": node.inference_backend,
        })

    async def handle_infer(self, request: web.Request) -> web.Response:
        """
        Proxied inference endpoint — the main entry point.
        POST { model, prompt, context?, stream? }
        Auto-routes to best available node.
        """
        data = await request.json()
        model = data.get("model", "")
        prompt = data.get("prompt", "")
        context = data.get("context", "")
        stream = data.get("stream", False)

        if not model or not prompt:
            return web.json_response(
                {"error": "model and prompt required"}, status=400
            )

        # Enforce context limit (~4K tokens ≈ 16K chars)
        max_chars = self.config["max_context_tokens"] * 4
        if len(context) > max_chars:
            context = context[-max_chars:]
            log.info("Context truncated to ~4K tokens")

        # Route
        result = self.table.best_node_for(model)
        if result is None:
            return web.json_response({
                "error": f"No node for model: {model}",
                "available_models": self._all_available_models(),
            }, status=404)

        node, score = result
        self.table.last_decision.had_context = bool(context)
        self._log_routing(model, node.node_id, score)

        # Forward to Ollama
        ollama_url = f"http://{node.tailscale_ip}:{node.ollama_port}/api/generate"
        payload = {"model": model, "prompt": prompt, "stream": stream}
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
                            "routed_to": node.node_id,
                            "score": round(score, 3),
                            "model": model,
                            "had_context": bool(context),
                        })
                    else:
                        err = await resp.text()
                        return web.json_response(
                            {"error": f"Ollama error on {node.node_id}: {err}"},
                            status=502
                        )
        except Exception as e:
            log.error(f"Inference failed on {node.node_id}: {e}")
            return web.json_response(
                {"error": f"Node unreachable: {node.node_id}: {e}"}, status=503
            )

    async def handle_leave(self, request: web.Request) -> web.Response:
        data = await request.json()
        node_id = data["node_id"]
        if node_id in self.table.nodes:
            self.table.nodes[node_id].status = "offline"
            log.info(f"NODE LEFT: {node_id}")
            self._save_state()
            return web.json_response({"status": "removed"})
        return web.json_response({"status": "unknown_node"}, status=404)

    async def handle_health(self, request: web.Request) -> web.Response:
        online = len(self.table.online_nodes())
        total = len(self.table.nodes)
        ld = self.table.last_decision

        health = {
            "coordinator": "online",
            "nodes_online": online,
            "nodes_total": total,
            "models_available": self._all_available_models(),
        }

        if ld.timestamp > 0:
            health["last_routing"] = {
                "model": ld.model_requested,
                "node": ld.node_chosen,
                "score": round(ld.score, 3),
                "candidates": ld.candidates_count,
                "had_context": ld.had_context,
                "ago_sec": round(time.time() - ld.timestamp, 1),
            }

        return web.json_response(health)

    def _all_available_models(self) -> list:
        models = set()
        for node in self.table.online_nodes():
            for m in node.models:
                models.add(m.name)
        return sorted(models)

    def _log_routing(self, model: str, node_id: str, score: float):
        entry = {"ts": time.time(), "model": model, "node": node_id,
                 "score": round(score, 3)}
        log.info(f"ROUTED: {model} → {node_id} (score: {score:.3f})")
        try:
            ROUTING_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(ROUTING_LOG_PATH, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception:
            pass

    async def _probe_ollama(self, ip: str, port: int) -> list:
        url = f"http://{ip}:{port}/api/tags"
        timeout = ClientTimeout(total=10)
        try:
            async with ClientSession(timeout=timeout) as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        models = []
                        for m in data.get("models", []):
                            size_gb = round(m.get("size", 0) / (1024**3), 2)
                            models.append(OllamaModel(
                                name=m.get("name", "unknown"),
                                size_gb=size_gb,
                                family=m.get("details", {}).get("family", ""),
                                quantization=m.get("details", {}).get(
                                    "quantization_level", ""),
                            ))
                        return models
        except Exception as e:
            log.warning(f"Ollama probe failed at {url}: {e}")
        return []

    async def _heartbeat_monitor(self):
        while True:
            await asyncio.sleep(self.config["heartbeat_interval_sec"])
            now = time.time()
            timeout = self.config["node_timeout_sec"]
            for node in self.table.nodes.values():
                if node.status == "online" and (now - node.last_heartbeat) > timeout:
                    node.status = "offline"
                    log.warning(f"NODE TIMEOUT: {node.node_id}")
                    self._save_state()

    def _save_state(self):
        STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        state = {}
        for nid, node in self.table.nodes.items():
            state[nid] = {
                "node_id": node.node_id, "tailscale_ip": node.tailscale_ip,
                "role": node.role, "hardware": node.hardware,
                "status": node.status, "capabilities": node.capabilities,
                "last_heartbeat": node.last_heartbeat,
            }
        with open(STATE_PATH, "w") as f:
            json.dump(state, f, indent=2)

    async def start(self):
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", self.config["coordinator_port"])
        await site.start()
        log.info(f"NETSCAPE v2 live on :{self.config['coordinator_port']}")
        log.info("Endpoints: /join /heartbeat /nodes /route/{model} /infer /health")
        await self._heartbeat_monitor()


async def main():
    config = load_config()
    coordinator = NetscapeCoordinator(config)
    await coordinator.start()

if __name__ == "__main__":
    asyncio.run(main())
