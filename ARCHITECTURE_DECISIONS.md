# NETSCAPE — Architecture Decision Document

**Purpose:** This document is designed for relay between Claude Opus and Kimi K2.5 (Boo2). Each AI reviews, critiques, and proposes improvements. Boo acts as liaison.

**Current iteration:** Draft 1 (Opus)  
**Next reviewer:** Kimi K2.5  

---

## What Is Netscape?

A personal AI mesh network that allows any machine to join or leave the network dynamically while maintaining continuous AI inference capability. The human (Boo) should never be the router, switchboard, or failover mechanism — the system handles this automatically.

## Current Infrastructure

| Node | Hardware | Role | Status |
|------|----------|------|--------|
| ThinkCentre M70q Gen 5 | i5-14400T, 32GB DDR5 | Always-on coordinator, Ollama CPU inference, OpenClaw/Boo2 host | 24/7 |
| GPD Pocket 4 | AMD HX 370, 32GB, RDNA 3.5 (890M) | Mobile GPU inference appliance | On-demand |
| Cloud (Opus) | Anthropic API | Strategy, complex reasoning, personality | Always available |
| Cloud (Kimi K2.5) | Moonshot API via OpenClaw | Async task execution, browser automation | Always available |

## What Exists Today

- Tailscale mesh connects both machines
- Ollama runs on ThinkCentre (CPU inference, 7B models)
- Boo2 runs on ThinkCentre via OpenClaw + Chrome relay
- Boo manually routes prompts between Opus and Boo2
- GPD joins via Tailscale but requires manual Ollama setup

## What We're Building

### Phase 1: Auto-Join Node Discovery (BUILT — this commit)

**Flow:**
```
GPD powers on
  → Tailscale connects automatically (already configured)
  → netscape-agent systemd service starts
  → Agent waits for Tailscale IP
  → Agent POSTs /join to ThinkCentre coordinator
  → Coordinator probes GPD's Ollama /api/tags
  → Coordinator registers GPD + its models in routing table
  → Heartbeat loop begins (10s intervals)

GPD powers off or disconnects:
  → Graceful: agent sends /leave
  → Ungraceful: coordinator detects heartbeat timeout (45s)
  → Node marked offline, routing table updates
```

### Phase 2: Intelligent Routing (NEEDS DESIGN)

**Open questions for Kimi to consider:**

1. **Routing rules engine:** How should we define which tasks go where? Options:
   - Simple keyword/tag matching (e.g., "transform" → local, "reason" → cloud)
   - Model capability matching (context window, speed, quality tiers)
   - Hybrid: user-defined rules + automatic capability scoring
   
2. **Token conservation:** The goal is to minimize cloud API spend. Should the routing brain:
   - Try local first, escalate to cloud on failure/low-confidence?
   - Use a classifier (itself local) to predict which tier is needed?
   - Let the user set a "cloud budget" per day/session?

3. **Context handoff:** When a task moves between nodes or between local and cloud:
   - How much context travels with the task?
   - Should there be a shared context store (on the coordinator)?
   - Is there a compression/summarization step before handoff?

### Phase 3: Orchestration Layer (NEEDS DESIGN)

This is the "sysprompt + tooling + context management" that the tweet references. The orchestrator sits above the routing layer and handles:

- Task decomposition (break complex prompts into subtasks)
- Parallel dispatch (send independent subtasks to different nodes)
- Result aggregation (combine outputs into coherent response)
- Session state management (persist conversation context across node changes)

**Open questions:**

4. **Where does the orchestrator live?** Options:
   - On the ThinkCentre as another service
   - As middleware between Telegram/chat interface and the inference backends
   - As an Opus-driven meta-agent that issues commands to the mesh

5. **How does Boo2 fit in?** Currently Boo2 does browser automation via OpenClaw. Should it:
   - Be registered as a "node" in Netscape with non-inference capabilities?
   - Stay separate as a sidecar agent?
   - Become the browser/web tool for the orchestrator?

6. **Telegram integration:** Boo talks to Kimi via Telegram. Should Netscape:
   - Intercept Telegram messages and route them?
   - Leave Telegram as a direct Boo2 channel?
   - Create a unified chat interface that multiplexes to all agents?

---

## Constraints

- ThinkCentre has NO GPU (CPU inference only, good for 7B Q4)
- GPD has Radeon 890M — ROCm is ~2.5x slower than CPU; use Vulkan via `OLLAMA_VULKAN=1` (Ollama v0.13+)
- BIOS must be set to fixed UMA VRAM for GPU detection on GPD
- Both machines are 32GB RAM
- Tailscale is the network layer — no port forwarding, no public IPs
- Power conservation matters: GPD is mobile, may be on battery

## Decision Points for Next Reviewer

**Kimi K2.5 — please address:**

1. Which routing architecture (Phase 2, Q1-3) do you recommend and why?
2. How would you design the context handoff to minimize token waste?
3. Should the orchestrator be a standalone service or embedded in an existing agent?
4. How should Boo2 (you) integrate into the mesh — as a node or a sidecar?
5. What's missing from this architecture that would make it production-grade for a single-user mesh?
6. Any security considerations for the Tailscale mesh coordination?

---

**Routing instructions:**
- Boo sends this to Kimi K2.5 via Telegram
- Kimi responds with critiques + proposals in the same markdown format
- Boo relays Kimi's response back to Opus
- Iterate until architecture is solid, then build Phase 2
