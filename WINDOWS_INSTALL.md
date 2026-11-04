# Windows Installation Guide — ROS 2 + Gazebo via Docker

This guide walks Windows users through setting up the `fusion-sim` environment using WSL 2, Docker Desktop, and the provided `docker-compose-window.yml`.

---

## Prerequisites

- Windows 10 version 2004 (Build 19041) or higher, or Windows 11
- Administrator access
- At least 20 GB of free disk space

---

## Step 1 — Install WSL 2

WSL 2 (Windows Subsystem for Linux) lets Docker containers run a full Linux kernel with GUI support via WSLg.

### 1.1 Enable WSL 2

Open **PowerShell as Administrator** and run:

```powershell
wsl --install
```

This installs WSL 2 and Ubuntu (the default distro) in one step. Restart your machine when prompted.

> If you already have WSL installed, upgrade to WSL 2:
> ```powershell
> wsl --set-default-version 2
> ```

### 1.2 Verify WSL 2 is running

After reboot, open PowerShell and confirm:

```powershell
wsl --list --verbose
```

You should see your Ubuntu distro listed with `VERSION 2`.

### 1.3 Update WSLg (for GUI / display support)

WSLg provides the X11/Wayland display server that Gazebo and RViz use. Keep it up to date:

```powershell
wsl --update
```

---

## Step 2 — Install Docker Desktop

### 2.1 Download and install

Download **Docker Desktop for Windows** from the official Docker website and run the installer.

During installation, ensure these options are checked:
- **Use WSL 2 instead of Hyper-V** (recommended)
- **Add shortcut to desktop** (optional)

Restart your machine after installation.

### 2.2 Configure Docker Desktop to use WSL 2

1. Open Docker Desktop.
2. Go to **Settings → General** and confirm *Use the WSL 2 based engine* is enabled.
3. Go to **Settings → Resources → WSL Integration**.
4. Enable integration for your Ubuntu distro (e.g., `Ubuntu`).
5. Click **Apply & Restart**.

### 2.3 Verify Docker is working inside WSL

Open your Ubuntu terminal (search *Ubuntu* in the Start menu) and run:

```bash
docker run hello-world
```

You should see a success message from Docker.

---

## Step 3 — Clone the Repository

Inside your **Ubuntu (WSL) terminal**, clone the project into your Linux home directory:

```bash
cd ~
git clone <repository-url> fusion-sim
cd fusion-sim
```

> Keep your files inside the Linux filesystem (`/home/<user>/...`) rather than under `/mnt/c/...`. This avoids filesystem performance issues and permission problems.

---

## Step 4 — Build and Start the Container

All commands below are run inside the **Ubuntu (WSL) terminal** from the `fusion-sim` directory.

### 4.1 Build the Docker image

```bash
docker compose -f docker-compose-window.yml build
```

This builds the `fusion-sim:humble` image containing:
- ROS 2 Humble Desktop
- Gazebo (via `ros-humble-ros-gz`)
- Colcon build tools

The first build takes 10–20 minutes depending on your connection speed.

### 4.2 Start the container

```bash
docker compose -f docker-compose-window.yml up -d
```

The `-d` flag runs the container in the background (detached mode).

### 4.3 Open a shell inside the container

```bash
docker compose -f docker-compose-window.yml exec sim bash
```

You are now inside the container as the `dev` user.

---

## Step 5 — Initialize FastSwarmSim (first time only)

Run these steps **once** after the container is first created.

### 5.1 Update package lists

```bash
sudo apt update
```

### 5.2 Build the workspace

```bash
rosdep update

cd ~/ws/src/FastSwarmSim

source /opt/ros/$ROS_DISTRO/setup.bash

rosdep install --from-paths src --ignore-src -r -y

colcon build --symlink-install

source install/setup.bash
```

---

## Daily Use

| Task | Command (from WSL terminal, in `fusion-sim/`) |
|---|---|
| Start the container | `docker compose -f docker-compose-window.yml up -d` |
| Open a shell | `docker compose -f docker-compose-window.yml exec sim bash` |
| Stop the container (keeps state) | `docker compose -f docker-compose-window.yml stop` |
| Remove the container (loses state) | `docker compose -f docker-compose-window.yml down` |

> **Important:** Use `stop` (not `down`) to preserve the container state. Using `down` deletes the container and you will need to repeat [Step 5](#step-5--initialize-fastswarmsimsimulation-first-time-only) on next start.

---

## Testing the GUI (Gazebo / RViz)

WSLg handles display forwarding automatically — no manual `DISPLAY` setup is needed.

Inside the container, launch Gazebo to verify:

```bash
source /opt/ros/$ROS_DISTRO/setup.bash
gz sim
```

A Gazebo window should appear on your Windows desktop.

---

## Troubleshooting

### "Cannot connect to the Docker daemon"

Docker Desktop is not running. Open Docker Desktop from the Start menu and wait for it to fully start, then retry.

### Gazebo window does not appear

Ensure WSLg is enabled and up to date:

```powershell
wsl --update
wsl --shutdown
```

Then restart your Ubuntu terminal and try again.

### "permission denied" on `/dev/dxg`

This device is the WSL GPU bridge. If it does not exist, your Windows or WSL version may be outdated. Run `wsl --update` in PowerShell and restart.

### Container exits immediately

Check the logs:

```bash
docker compose -f docker-compose-window.yml logs sim
```

### `rosdep` command not found

`rosdep` is part of `ros-dev-tools`, which is installed in the Dockerfile. If missing, rebuild the image:

```bash
docker compose -f docker-compose-window.yml build --no-cache
```
