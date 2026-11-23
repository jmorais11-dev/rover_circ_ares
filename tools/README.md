# tools/

Host-side tools that sit **outside** the ROS 2 workspace. Each folder has a
`COLCON_IGNORE`, so `colcon build` skips them; they run with plain Python on
the host (or on Render), talking to the simulation through rosbridge
(WebSocket, port 9090).

| Path | What it is |
|---|---|
| [`rover_mcp_safe/`](rover_mcp_safe/) | Restricted MCP proxy between an LLM and the rover. Wraps [ros-mcp](https://pypi.org/project/ros-mcp/) and adds high-level tools (`navigate_to`, `stop_navigation`, `set_exploration`, `get_robot_pose`, `run_mission`). Velocity commands (`/cmd_vel`) are refused in the proxy **and** in rosbridge. |
| [`rover_web/`](rover_web/) | Web chat: `server.py` (page + LLM, deployed on Render via [`render.yaml`](../render.yaml)) and `agent.py` (runs on the PC next to the simulation and dials out to the server, so no port is exposed). |
| [`rtf_meter.py`](rtf_meter.py) | Measures the Gazebo real-time factor (RTF) from `/clock`. Runs inside the container. |

Full documentation (Portuguese): [ROS-MCP](https://jmorais11-dev.github.io/rover_circ_ares/ros-mcp/),
[Chat Web](https://jmorais11-dev.github.io/rover_circ_ares/chat-web/),
[Simulation performance](https://jmorais11-dev.github.io/rover_circ_ares/desempenho-simulacao/).

## Setup (host)

```bash
pipx install ros-mcp==3.1.2 ollmcp    # ros-mcp brings fastmcp and websocket-client
PY=~/.local/share/pipx/venvs/ros-mcp/bin/python
```

## Tests, cheapest first

Start the simulation first (see the main [README](../README.md#3-run-the-simulation)),
except for test (a).

```bash
# a) proxy safety policy, offline (no ROS needed; also runs in CI: .github/workflows/tests.yml)
$PY -I tools/rover_mcp_safe/test_policy.py

# b) MCP end to end WITHOUT an LLM: reads /odom, tries /cmd_vel (must be refused),
#    sends a Nav2 goal 2 m ahead, pauses and resumes exploration
$PY -I tools/rover_mcp_safe/smoke_test.py --dx 2.0

# c) real LLM, non-interactive (Ollama; default prompts or your own)
$PY -u -I tools/rover_mcp_safe/llm_test.py --model qwen2.5:7b \
  "Where is the rover right now? Read its odometry and tell me x and y."

# d) interactive chat
tools/rover_mcp_safe/setup_ollmcp.sh        # once; real robot: setup_ollmcp.sh <Pi IP>
ollmcp -j ~/.config/ollmcp/rover-servers.json
```

Tips:
- Without a GPU, qwen2.5:7b next to Gazebo takes **minutes** per round. Keep
  prompts short; free the CPU with `ollama stop qwen2.5:7b`.
- `ollmcp` asks for confirmation on every tool call (human in the loop). That
  is intentional.
- Use temperature ≤ 0.1 and context ≥ 8192 (the tool schemas take ~2.7k
  tokens); `setup_ollmcp.sh` already sets this.
- When redirecting Python output to a file, use `python -u`.

## Web chat agent

```bash
$PY -I tools/rover_web/agent.py \
  --server wss://<your-app>.onrender.com --token '<AGENT_TOKEN from Render>'
```

Restart `agent.py` after updating the code: it loads `rover_mcp_safe` only at
startup.
