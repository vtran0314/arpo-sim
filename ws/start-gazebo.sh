#! /usr/bin/bash

#
# start-gazebo.sh — launch Gazebo, wait for it to be ready, then spawn all models.
#

gz sim /home/dev/ws/models/arpo_world.sdf &

#
# Poll until the world service is available.
#
echo "Waiting for Gazebo to be ready..."
until gz service -l 2>/dev/null | grep -q "/world/arpo/create"; do
    sleep 1
done
echo "Gazebo ready."

# ── Spawn stadium ──────────────────────────────────────────────────────────────
gz service -s /world/arpo/create \
  --reqtype gz.msgs.EntityFactory \
  --reptype gz.msgs.Boolean \
  --req 'sdf_filename: "/home/dev/ws/models/gillette_stadium/model.sdf"' \
  --timeout 5000

# ── Spawn drone ────────────────────────────────────────────────────────────────
gz service -s /world/arpo/create \
  --reqtype gz.msgs.EntityFactory \
  --reptype gz.msgs.Boolean \
  --req 'sdf_filename: "/home/dev/ws/models/iris_drone/model.sdf"' \
  --timeout 5000

# ── Spawn lidar sensor station ─────────────────────────────────────────────────
#
# pose: "x y z roll pitch yaw"  (metres, radians)
#
#   x, y  — position in the world XY plane
#   z     — height above ground (set to 0 so the base sits on the ground)
#   roll/pitch/yaw — orientation (0 0 0 = upright, facing +X)
#
# Change x/y to place the sensor at a different stadium location.
# The sensor's ray origin is 0.15 m above the model origin (see model.sdf).
#
gz service -s /world/arpo/create \
  --reqtype gz.msgs.EntityFactory \
  --reptype gz.msgs.Boolean \
  --req 'sdf_filename: "/home/dev/ws/models/lidar/model.sdf", pose: {position: {x: 10, y: 0, z: 0}}' \
  --timeout 5000
