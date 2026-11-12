#! /usr/bin/bash

ign gazebo &

echo "Waiting for Gazebo to be ready..."
until ign service -l 2>/dev/null | grep -q "/world/default/create"; do
    sleep 1
done
echo "Gazebo ready."

ign service -s /world/default/create \
  --reqtype ignition.msgs.EntityFactory \
  --reptype ignition.msgs.Boolean \
  --req 'sdf_filename: "/home/dev/ws/models/gillette_stadium/model.sdf"' \
  --timeout 5000

ign service -s /world/default/create \
  --reqtype ignition.msgs.EntityFactory \
  --reptype ignition.msgs.Boolean \
  --req 'sdf_filename: "/home/dev/ws/models/iris_drone/model.sdf"' \
  --timeout 5000

