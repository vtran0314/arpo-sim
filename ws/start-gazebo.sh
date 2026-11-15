#! /usr/bin/bash

gz sim &

echo "Waiting for Gazebo to be ready..."
until gz service -l 2>/dev/null | grep -q "/world/default/create"; do
    sleep 1
done
echo "Gazebo ready."

gz service -s /world/default/create \
  --reqtype gz.msgs.EntityFactory \
  --reptype gz.msgs.Boolean \
  --req 'sdf_filename: "/home/dev/ws/models/gillette_stadium/model.sdf"' \
  --timeout 5000

gz service -s /world/default/create \
  --reqtype gz.msgs.EntityFactory \
  --reptype gz.msgs.Boolean \
  --req 'sdf_filename: "/home/dev/ws/models/iris_drone/model.sdf"' \
  --timeout 5000

