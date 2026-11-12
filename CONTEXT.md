# arpo-sim — Session Context

## What this project is
A Docker-based ROS2 (Humble) simulation environment for [FastSwarmSim](https://github.com/shupx/FastSwarmSim). The Docker image provides a full ROS2 desktop setup; FastSwarmSim is cloned and built automatically on first container start via an entrypoint script. The long-term goal is a swarm drone + edge device simulation inside Gillette Stadium.

## Current status (2026-11-12)
**Pipeline is fully working end-to-end.** Drone and stadium spawn in Gazebo, keyboard control moves the drone through FSS physics, and the bridge mirrors the pose into Gazebo smoothly at 20 Hz.

## Repo
`git@github.com:vtran0314/arpo-sim.git`

## Key files
| File | Purpose |
|---|---|
| `Dockerfile` | Builds the ROS2 Humble desktop image with the `dev` user |
| `docker-compose.yml` | Linux setup — bind-mounts `./ws` into the container |
| `docker-compose-window.yml` | Windows/WSL2 setup — bind-mounts `./ws` into the container |
| `entrypoint.sh` | Runs on container start; clones + builds FastSwarmSim if not present; sets `IGN_GAZEBO_RESOURCE_PATH` |
| `README.md` | User-facing startup guide (Linux + Windows) |
| `docker-installation-guide-windows.docx` | Detailed Windows/WSL2 Docker setup guide |
| `.gitattributes` | Forces LF line endings for `.sh` files (prevents CRLF issues on Windows) |
| `.gitignore` | Ignores `ws/` build artifacts and `.env` |
| `ws/src/.gitkeep` | Placeholder so the bind-mount directory exists after a fresh clone |
| `ws/source-env.sh` | Sets `IGN_GAZEBO_RESOURCE_PATH` and sources ROS/FSS setup files — must be `source`d, not executed |
| `ws/start-gazebo.sh` | Starts Gazebo, polls until `/world/default/create` is ready, then spawns stadium and drone models |
| `ws/models/gillette_stadium/` | Gazebo model for Gillette Stadium |
| `ws/models/iris_drone/` | Iris quadrotor visual model for Gazebo (pose driven by bridge) |
| `ws/src/arpo_gz_bridge/` | ROS2 package: bridges FastSwarmSim drone poses into Gazebo |

## How the entrypoint works
1. Sets `IGN_GAZEBO_RESOURCE_PATH=/home/dev/ws/models`
2. Checks if `ws/src/FastSwarmSim` exists
3. If **not**: clones repo → `rosdep update` → `apt-get update` → `rosdep install` → `colcon build`
4. If **yes**: skips straight to bash
5. `colcon build` and `rosdep install` must run from `WS` (`/home/dev/ws`), **not** from inside `FSS_DIR`

## Two separate install directories — IMPORTANT
FastSwarmSim was built inside its own directory, so there are two separate colcon installs:

| Install path | Contains |
|---|---|
| `ws/src/FastSwarmSim/install/` | `fss_px4_sim`, `fss_bringup`, `fss_sensing`, `fss_time`, `fss_time_interfaces` |
| `ws/install/` | `arpo_gz_bridge` (and future custom packages) |

**Always source both before running anything:**
```bash
source /opt/ros/humble/setup.bash
source /home/dev/ws/src/FastSwarmSim/install/setup.bash
source /home/dev/ws/install/setup.bash
```

## Gillette Stadium Gazebo model
- Blender source: `ws/gillette_stadium.blend`
- Exported as OBJ (`ws/models/gillette_stadium/meshes/gillette_stadium.obj`)
  - Export settings: Forward = X, Up = Z (matches Gazebo coordinate system)
- Model files: `ws/models/gillette_stadium/model.config` + `model.sdf`
- `model.sdf` has a pose correction on the link: `<pose>0 0 0 1.5708 0 1.5708</pose>`
- After these rotations, the playing field surface lands at **Gazebo Z = 0**
- Gazebo version: **Ignition Fortress 6.18.0** — use `ign gazebo`, NOT `gz sim`
- Supported mesh formats in Fortress: `.dae`, `.obj`, `.stl` — `.glb` is NOT supported

## Iris Drone Gazebo model
- Location: `ws/models/iris_drone/`
- Meshes copied from `ws/src/FastSwarmSim/src/fss_px4_sim/model/meshes/` (`iris.stl`, `iris_prop_cw.stl`, `iris_prop_ccw.stl`)
- `model.sdf`: body + 4 rotor links with revolute joints, **no inertial block** (Ignition rejected the PX4 inertia values as physically invalid — `ixx+iyy < izz`)
- **`<static>true</static>`** — required so Gazebo physics does not fight the bridge. Without this, the drone glitches up and down as physics and the bridge fight over the pose.
- Pose is set externally by `arpo_gz_bridge`, not by Gazebo physics

## arpo_gz_bridge ROS2 package
- Location: `ws/src/arpo_gz_bridge/`
- Node: `pose_bridge` — subscribes to `mavros/local_position/pose` with **BEST_EFFORT QoS** (must match FSS publisher), calls `/world/default/set_pose` via non-blocking `ign service` subprocess throttled to 20 Hz **wall-clock time**
- Launch file: `launch/sim.launch.py` — starts FastSwarmSim single drone + bridge node
- Build: `colcon build --packages-select arpo_gz_bridge --symlink-install` from `ws/`
- **`z_offset` parameter** (default 0.1 m): adds a vertical offset to the drone's Gazebo Z so it sits above the stadium playing field (field surface = Gazebo Z=0). Tune with `z_offset:=<value>` on the launch line.
- Bridge logs a `[bridge] recv=N sent=N pos=(x,y,z)` line once per second — use this to confirm data is flowing.

## Full startup sequence
```bash
# Terminal 1 — Gazebo (starts Gazebo, waits for readiness, spawns stadium + drone)
source ~/ws/source-env.sh
~/ws/start-gazebo.sh

# Terminal 2 — FastSwarmSim + bridge
source ~/ws/source-env.sh
ros2 launch arpo_gz_bridge sim.launch.py

# Terminal 3 — Keyboard control
source ~/ws/source-env.sh
ros2 run fss_px4_sim keyboard_control_ros2
# Required sequence: T (arm) → wait for armed=True → O (OFFBOARD) → WASD/QE to fly
```

## Keyboard control reference
| Key | Action |
|---|---|
| `T` | Arm |
| `O` | Switch to OFFBOARD mode (must arm first) |
| `W/S` | Forward / backward |
| `A/D` | Strafe left / right |
| `Q/E` | Climb / descend |
| `Z/C` | Yaw left / right |
| `Space` / `R` | Stop (hold position) |
| `+` / `-` | Adjust speed (default 1.0 m/s) |
| `X` | Stop + disarm |
| `Ctrl-C` | Disarm and exit |

## Monitoring drone state
```bash
ros2 topic echo /mavros/local_position/pose --field pose.position  # position (x, y, z)
ros2 topic echo /mavros/local_position/velocity_local               # velocity (vx, vy, vz)
ros2 topic echo /mavros/state                                        # armed flag + flight mode
ros2 topic list | grep mavros                                        # all available topics
```

## FastSwarmSim overview
- Lightweight ROS2 simulator for PX4-compatible multi-rotor drones
- Does **NOT** use Ignition Gazebo for physics — has its own simulator
- Visualizes in **RViz**, not Gazebo
- LiDAR simulation via `fss_sensing` using PCD maps (not Gazebo world)
- Key packages: `fss_px4_sim`, `fss_sensing`, `fss_bringup`, `fss_time`
- Drone pose topic: `mavros/local_position/pose` (`geometry_msgs/PoseStamped`, BEST_EFFORT QoS)
- MAVROS Lite is **embedded** in `px4_rotor_sim_node` — no separate MAVROS process needed with `direct_ros` transport

## Next steps
- Convert stadium `.obj` mesh to PCD map for LiDAR sensing via `fss_sensing`
- Scale up to multi-drone swarm using `px4_rotor_sim_multi.launch.py`

## Known gotchas
- **Two install directories**: Always source both `FastSwarmSim/install/setup.bash` and `ws/install/setup.bash` — missing either causes "package not found" errors.
- **QoS mismatch**: FSS publishes `mavros/local_position/pose` with BEST_EFFORT. Any subscriber must use `QoSProfile(reliability=ReliabilityPolicy.BEST_EFFORT)` or zero messages will be delivered.
- **`ignition.msgs.Pose` field format**: The correct protobuf text format is `name: "...", position: {x,y,z}, orientation: {x,y,z,w}` — there is NO `pose:` wrapper field. Using `pose: {position: ...}` silently fails (parse error, but service returns `data: true`).
- **Sim-time throttle**: FSS runs faster than real time. Any throttle in the bridge must use `time.monotonic()` (wall clock), NOT `self.get_clock()` (sim clock) — otherwise the bridge floods Gazebo with subprocesses.
- **`static=false` on iris_drone**: Causes the drone to glitch up/down — Gazebo physics and the bridge fight over the pose. The model must be `static=true`.
- **Drone clips into stadium ground**: The playing field surface is at Gazebo Z=0. The bridge's `z_offset` parameter (default 0.1 m) keeps the drone above it.
- **CRLF on Windows**: Shell scripts must have LF line endings. Fixed by `.gitattributes`.
- **Linux bind mount vs entrypoint path**: Fixed by using absolute path `/home/dev/entrypoint.sh` in the Dockerfile.
- **`IGN_GAZEBO_RESOURCE_PATH` not set**: Set manually if container not restarted: `export IGN_GAZEBO_RESOURCE_PATH=/home/dev/ws/models`.
- **`gz` vs `ign`**: Fortress (6.x) uses `ign` prefix only.
- **`.glb` not supported**: Use `.obj` or `.dae` for Ignition Fortress meshes.
- **Iris inertia invalid**: PX4's Iris inertia values (`ixx+iyy < izz`) are rejected by Ignition. The `iris_drone` SDF has no inertial block — Gazebo is visuals-only here.
- **`source-env.sh` must be sourced**: Running it directly (`./source-env.sh`) spawns a subshell — exports die on exit. Always use `source ~/ws/source-env.sh`. The script now detects and errors on direct execution.
- **`start-gazebo.sh` readiness poll**: The script polls `ign service -l` until `/world/default/create` appears before spawning models. If Gazebo never starts, this will loop forever — check that `ign gazebo` launched successfully.
- **`docker compose stop` not `down`**: `down` removes the container; the next `up` re-runs `rosdep install` and `colcon build`. Use `stop` to preserve the container.
- **Reinstalling FastSwarmSim**: Delete `ws/src/FastSwarmSim` on the host, then `docker compose up`.
- **`NodeShared::RecvSrvRequest() error sending response: Host unreachable`**: Harmless. Gazebo tries to send the `set_pose` reply back to the `ign service` subprocess, which has already exited. The pose IS set correctly.
