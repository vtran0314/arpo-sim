#!/usr/bin/env python3
"""
Subscribes to FastSwarmSim drone pose and moves the matching model in Gazebo
by calling the /world/<world>/set_pose service via the gz CLI.

This is intentionally simple: subprocess calls are throttled so the overhead is low.
Replace with direct gz-transport Python bindings if sub-10ms latency is needed.
"""
import subprocess
import time
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
from geometry_msgs.msg import PoseStamped


class PoseBridgeNode(Node):
    def __init__(self):
        super().__init__('arpo_gz_pose_bridge')

        self.declare_parameter('model_name', 'iris_drone')
        self.declare_parameter('world_name', 'default')
        self.declare_parameter('update_rate_hz', 20.0)
        self.declare_parameter('ros_topic', 'mavros/local_position/pose')
        self.declare_parameter('z_offset', 0.1)

        self._model = self.get_parameter('model_name').value
        self._world = self.get_parameter('world_name').value
        self._topic = self.get_parameter('ros_topic').value
        self._z_offset = self.get_parameter('z_offset').value
        rate = self.get_parameter('update_rate_hz').value
        self._min_interval_s = 1.0 / rate  # wall-clock seconds; immune to sim-time speedup

        self._service = f'/world/{self._world}/set_pose'
        self._last_wall = 0.0
        self._recv_count = 0
        self._send_count = 0

        qos = QoSProfile(depth=10, reliability=ReliabilityPolicy.BEST_EFFORT)
        self.create_subscription(PoseStamped, self._topic, self._pose_cb, qos)

        self.get_logger().info(
            f'pose_bridge: {self._topic} → {self._service} '
            f'(model="{self._model}", {rate:.0f} Hz, z_offset={self._z_offset:.3f} m)'
        )

    def _pose_cb(self, msg: PoseStamped):
        self._recv_count += 1

        now = time.monotonic()  # wall-clock throttle — unaffected by FSS sim-time speedup
        if now - self._last_wall < self._min_interval_s:
            return
        self._last_wall = now
        self._send_count += 1

        p = msg.pose.position
        q = msg.pose.orientation

        # Log once per second so you can confirm data is flowing
        if self._send_count % max(1, int(1.0 / self._min_interval_s)) == 0:
            self.get_logger().info(
                f'[bridge] recv={self._recv_count} sent={self._send_count} '
                f'pos=({p.x:.2f}, {p.y:.2f}, {p.z + self._z_offset:.2f})'
            )

        req = (
            f'name: "{self._model}", '
            f'position: {{x: {p.x:.6f}, y: {p.y:.6f}, z: {p.z + self._z_offset:.6f}}}, '
            f'orientation: {{x: {q.x:.6f}, y: {q.y:.6f}, z: {q.z:.6f}, w: {q.w:.6f}}}'
        )

        proc = subprocess.Popen(
            ['gz', 'service',
             '-s', self._service,
             '--reqtype', 'gz.msgs.Pose',
             '--reptype', 'gz.msgs.Boolean',
             '--req', req,
             '--timeout', '500'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        # Check previous process for errors without blocking the current one
        if hasattr(self, '_last_proc') and self._last_proc is not None:
            try:
                rc = self._last_proc.poll()
                if rc is not None and rc != 0:
                    err = self._last_proc.stderr.read().decode().strip()
                    if err:
                        self.get_logger().warn(f'[bridge] gz service rc={rc}: {err}')
            except Exception:
                pass
        self._last_proc = proc


def main(args=None):
    rclpy.init(args=args)
    node = PoseBridgeNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
