# arpo-sim

A Dockerised ROS 2 Lyrical Luth + Gazebo Jetty environment for swarm simulation using [FastSwarmSim](https://github.com/shupx/FastSwarmSim).

| Component | Version |
|---|---|
| Base image | `osrf/ros:lyrical-desktop` (Ubuntu 26.04) |
| ROS 2 | Lyrical Luth |
| Gazebo | Jetty (installed through `ros-lyrical-ros-gz`) |

The ROS distro is set by the `ROS_DISTRO` build argument in the `Dockerfile` and the compose files.

---

## Prerequisites

| Requirement | Notes |
|---|---|
| Docker + Docker Compose | v2.x recommended |
| NVIDIA GPU + drivers | Linux only: the container uses the NVIDIA runtime for Gazebo rendering |
| X11 display server | Linux: native. Windows: WSL2 + WSLg (see `docker-installation-guide-windows.docx`). macOS: XQuartz |

---

## First-time startup

The first `docker compose up` automatically clones FastSwarmSim, installs ROS dependencies, and builds the workspace. **This takes several minutes.**

---

## Linux

### 1. Allow GUI passthrough

```bash
xhost +local:docker
```

> **Note:** This grants X11 access only to the local `docker` user. For this to work, your host user must be in the `docker` group. If you get permission errors running Docker commands or the GUI fails to open, check with:
> ```bash
> groups $USER
> ```
> If `docker` is not listed, add yourself and re-login:
> ```bash
> sudo usermod -aG docker $USER
> ```

### 2. Start the container

```bash
docker compose up -d
docker exec -it arpo-sim bash
```

### 3. Source the environment (inside the container)

```bash
source ~/ws/source-env.sh
```

> Must be `source`d, not executed directly, so the exports persist in your shell.

### 4. Start Gazebo and load models

```bash
~/ws/start-gazebo.sh
```

This launches Gazebo in the background, waits until it is ready, then spawns the Gillette Stadium and iris drone models automatically.

### 5. Launch the ROS 2 bridge (new terminal)

Open a second shell into the container:

```bash
docker exec -it arpo-sim bash
source ~/ws/source-env.sh
ros2 launch arpo_gz_bridge sim.launch.py
```

Optional arguments:

```bash
ros2 launch arpo_gz_bridge sim.launch.py world_name:=default model_name:=iris_drone
```

### 6. Control the drone (new terminal)

Open a third shell:

```bash
docker exec -it arpo-sim bash
source ~/ws/source-env.sh
ros2 run fss_px4_sim keyboard_control_ros2
```

---

## Windows (WSL2 + WSLg)

See `docker-installation-guide-windows.docx` for the full setup guide.

Once WSL2 is configured, use the Windows compose file instead:

```bash
docker compose -f docker-compose-window.yml up -d
docker exec -it fusion-sim bash
```

> **Note:** On Windows the container is named `fusion-sim`, not `arpo-sim`. Use `docker exec -it fusion-sim bash` wherever the Linux steps say `docker exec -it arpo-sim bash`.

Then follow steps 3–6 above inside the container.

To stop it, pass the same compose file:

```bash
docker compose -f docker-compose-window.yml stop
```

---

## macOS

1. Install [XQuartz](https://www.xquartz.org/), open its **Settings > Security** and enable **Allow connections from network clients**, then log out and back in.
2. In Docker Desktop (4.34 or later), enable host networking under **Settings > Resources > Network**.
3. Allow the container to use the display, then start it with the macOS compose file:

```bash
xhost + 127.0.0.1
docker compose -f docker-compose-mac.yml up -d
docker exec -it arpo-sim bash
```

Then follow steps 3–6 above inside the container. There is no GPU passthrough on macOS, so Gazebo renders in software (`LIBGL_ALWAYS_SOFTWARE=1`) and will be slower than on Linux.

To stop it:

```bash
docker compose -f docker-compose-mac.yml stop
```

---

## Stopping the simulation

```bash
docker compose stop
```

> **Note:** Use `stop`, not `down`. `docker compose down` removes the container, which means the next start will re-run the full setup (clone, rosdep install, colcon build). `stop` preserves the container so you can resume quickly with `docker compose start`.

---

## Repository structure

```
.
├── Dockerfile                          # ROS 2 Lyrical + Gazebo Jetty image
├── docker-compose.yml                  # Linux (NVIDIA GPU)
├── docker-compose-window.yml           # Windows WSL2 + WSLg
├── docker-compose-mac.yml              # macOS (XQuartz, software rendering)
├── entrypoint.sh                       # Auto-installs FastSwarmSim on first run
├── docker-installation-guide-windows.docx
└── ws/
    ├── source-env.sh                   # Sets GZ_SIM_RESOURCE_PATH and sources ROS + workspace setup files
    ├── start-gazebo.sh                 # Starts Gazebo, waits for readiness, then spawns models
    ├── models/
    │   ├── gillette_stadium/           # Stadium SDF model
    │   └── iris_drone/                 # Iris quadrotor SDF model
    └── src/
        └── arpo_gz_bridge/             # ROS 2 package: bridges FastSwarmSim pose → Gazebo set_pose
            └── launch/sim.launch.py    # Launches FSS single-drone + pose bridge node
```
