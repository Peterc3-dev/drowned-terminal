# Drowned Terminal

Retro-futuristic TUI dashboard with distributed inference mesh networking.

## What It Does

**Drowned Terminal** is a Pip-Boy/Nostromo-inspired terminal dashboard built with Textual and Rich. It presents a modular 3x2 grid interface where each cell can host a different module — live 3D math animations, room maps, Pip-Boy stat trackers, music players, and more. Navigate with arrow keys, assign modules with letter keys, and zoom into any cell with a portal wormhole transition.

**Netscape** is the distributed LLM inference layer. It connects machines over a Tailscale mesh network, routing inference requests to the best available node based on GPU load, model availability, and real-time health metrics. A coordinator service discovers and scores nodes while antifragile worker agents ensure local Ollama inference always works, even when the coordinator is unreachable.

## Features

- Modular 3x2 grid dashboard with zoom-in/zoom-out portal transitions
- Phosphor CRT color themes (amber, green, cyan) switchable with F1/F2/F3
- Live 3D math animations rendered in terminal cells
- Distributed inference routing with GPU/load-aware scoring
- Antifragile node agents with automatic local Ollama fallback
- Systemd service templates for coordinator and agent deployment
- Sound effects engine for navigation and module events
- Room map module with 3D spatial layout visualization

## Architecture

| Component | File | Role |
|---|---|---|
| TUI Dashboard | `app.py` | Main Textual application — grid layout, input handling, transitions |
| Coordinator | `discovery.py` | Netscape coordinator — node registry, capability-based routing, `/infer` proxy |
| Node Agent | `node_agent.py` | Worker agent — heartbeats, GPU metrics, local inference fallback |
| Core | `core/` | Theme engine, module registry, sound engine, tiling system |
| Modules | `modules/` | Animation renderer, room map, Pip-Boy stats, music, video |
| Config | `config/` | Default configuration values |
| Services | `*.service` | Systemd unit templates for mesh deployment |

## Tech Stack

- **Python** with async throughout
- **Textual** + **Rich** for the TUI
- **aiohttp** for mesh networking (coordinator and agent HTTP APIs)
- **Ollama** as the local LLM inference backend
- **Tailscale** for secure mesh connectivity between nodes

## Quick Start

### TUI Dashboard

```bash
pip install textual rich
python app.py
```

### Netscape Coordinator (always-on node)

```bash
pip install aiohttp
python discovery.py
```

### Netscape Node Agent (worker nodes)

```bash
pip install aiohttp
python node_agent.py
```

### Systemd Deployment

```bash
# Install service templates
sudo cp netscape-coordinator@.service /etc/systemd/system/
sudo cp netscape-agent@.service /etc/systemd/system/

# Enable and start
sudo systemctl enable --now netscape-coordinator@$USER
sudo systemctl enable --now netscape-agent@$USER
```
