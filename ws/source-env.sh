#! /usr/bin/bash

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    echo "ERROR: This script must be sourced: source ${0}"
    exit 1
fi

echo 'Exporting gazebo resource path'
export IGN_GAZEBO_RESOURCE_PATH=/home/dev/ws/models
echo $IGN_GAZEBO_RESOURCE_PATH
echo 'source ros path'
source /opt/ros/humble/setup.bash
echo 'source FSS path'
source /home/dev/ws/src/FastSwarmSim/install/setup.bash
echo 'source model path'
source /home/dev/ws/install/setup.bash
