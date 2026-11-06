#! /bin/bash
set -ev

WS=/home/dev/ws
FSS_DIR=${WS}/src/FastSwarmSim
export IGN_GAZEBO_RESOURCE_PATH=${IGN_GAZEBO_RESOURCE_PATH}:${WS}/models

if [ ! -d "${FSS_DIR}" ]; then
    echo "[setup] Cloning FastSwarmSim..."
    mkdir -p "${WS}/src"
    git clone https://github.com/shupx/FastSwarmSim.git "${FSS_DIR}"

    echo "[setup] Updating rosdep database..."
    rosdep update --rosdistro humble

    echo "[Apt-get update]"
    sudo apt-get update

    echo "[setup] Installing ROS dependencies..."
    source /opt/ros/humble/setup.bash
    cd "${WS}"
    rosdep install --from-paths src --ignore-src -r -y

    echo "[setup] Building workspace (this may take a while)..."
    colcon build --symlink-install

    echo "[setup] FastSwarmSim ready."
else
    echo "[setup] FastSwarmSim already present, skipping install."
fi

exec "$@"