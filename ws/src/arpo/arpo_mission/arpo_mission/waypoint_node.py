import math

import rclpy
from geometry_msgs.msg import PoseStamped
from mavros_msgs.msg import PositionTarget, State
from mavros_msgs.srv import CommandBool, SetMode
from rclpy.qos import QoSProfile, ReliabilityPolicy
from rclpy.node import Node


SETPOINT_TOPIC  = 'mavros/setpoint_raw/local'
POSE_TOPIC      = 'mavros/local_position/pose'
ARMING_SERVICE  = 'mavros/cmd/arming'
MODE_SERVICE    = 'mavros/set_mode'
STATE_TOPIC     = 'mavros/state'

PREFLIGHT  = 'PREFLIGHT'
ARMING     = 'ARMING'
OFFBOARD   = 'OFFBOARD'
TAKEOFF    = 'TAKEOFF'
FLYING     = 'FLYING'
ARRIVED    = 'ARRIVED'

PREFLIGHT_TICKS = 40  # 2 seconds at 20 Hz before attempting arm


class WaypointNode(Node):
    def __init__(self):
        super().__init__('waypoint_node')

        # Parameters
        self.declare_parameter('target_x',       0.0)
        self.declare_parameter('target_y',       0.0)
        self.declare_parameter('target_z',       5.0)
        self.declare_parameter('takeoff_z',      3.0)
        self.declare_parameter('arrival_radius', 1.0)

        self.target_x       = self.get_parameter('target_x').value
        self.target_y       = self.get_parameter('target_y').value
        self.target_z       = self.get_parameter('target_z').value
        self.takeoff_z      = self.get_parameter('takeoff_z').value
        self.arrival_radius = self.get_parameter('arrival_radius').value

        # State
        self.phase           = PREFLIGHT
        self.current_pose    = None   # updated by _pose_cb
        self._preflight_ticks = 0
        self._pending_future  = None  # tracks in-flight service calls
        self.vehicle_state   = None

        # Publisher / subscriber
        qos = QoSProfile(depth=10, reliability=ReliabilityPolicy.BEST_EFFORT)
        self.setpoint_pub = self.create_publisher(PositionTarget, SETPOINT_TOPIC, 10)
        self.pose_sub = self.create_subscription(PoseStamped, POSE_TOPIC, self._pose_cb, qos)

        self.state_sub = self.create_subscription(State, STATE_TOPIC, self._state_cb, 10)


        # Service clients
        self.arm_client  = self.create_client(CommandBool, ARMING_SERVICE)
        self.mode_client = self.create_client(SetMode,     MODE_SERVICE)

        # 20 Hz timer — drives the state machine
        self.timer = self.create_timer(0.05, self._timer_cb)

        self.get_logger().info('WaypointNode started — PREFLIGHT')

    # ------------------------------------------------------------------
    def _pose_cb(self, msg):
        self.current_pose = msg

    def _state_cb(self, msg):
        self.vehicle_state= msg


    # ------------------------------------------------------------------
    def _timer_cb(self):
        if self.phase == PREFLIGHT:
            self._publish_hold()
            self._preflight_ticks += 1
            if self._preflight_ticks >= PREFLIGHT_TICKS:
                self.phase = ARMING
                self.get_logger().info('PREFLIGHT done → ARMING')

        elif self.phase == ARMING:
            self._publish_hold()
            if self._pending_future is None:
                req = CommandBool.Request()
                req.value = True
                self._pending_future = self.arm_client.call_async(req)
            elif self._pending_future.done():
                if self._pending_future.result().success:
                    self._pending_future = None
                    self.phase = OFFBOARD
                    self.get_logger().info('Armed → OFFBOARD')
                else:
                    self._pending_future = None  # retry next tick

        elif self.phase == OFFBOARD:
            self._publish_hold()
            if self._pending_future is None:
                req = SetMode.Request()
                req.custom_mode = 'OFFBOARD'
                self._pending_future = self.mode_client.call_async(req)
            elif self._pending_future.done():
                if self.vehicle_state is not None and self.vehicle_state.mode == 'OFFBOARD':
                    self._pending_future = None
                    self.phase = TAKEOFF
                    self.get_logger().info('OFFBOARD mode set → TAKEOFF')
                else:
                    self._pending_future = None  # retry next tick

        elif self.phase == TAKEOFF:
            self._publish_setpoint(0.0, 0.0, self.takeoff_z)
            if self.current_pose is not None:
                z = self.current_pose.pose.position.z
                if z >= self.takeoff_z - 0.3:
                    self.phase = FLYING
                    self.get_logger().info(f'Reached takeoff altitude {z:.2f} m → FLYING')

        elif self.phase == FLYING:
            self._publish_setpoint(self.target_x, self.target_y, self.target_z)
            if self._distance_to_target() < self.arrival_radius:
                self.phase = ARRIVED
                self.get_logger().info('Arrived at target → ARRIVED')

        elif self.phase == ARRIVED:
            self._publish_setpoint(self.target_x, self.target_y, self.target_z)
            self.get_logger().info('Holding at target.', once=True)

    # ------------------------------------------------------------------
    def _publish_hold(self):
        if self.current_pose is None:
            self._publish_setpoint(0.0, 0.0, 0.0)
            return
        self._publish_setpoint(
            self.current_pose.pose.position.x,
            self.current_pose.pose.position.y,
            self.current_pose.pose.position.z,
        )

    def _publish_setpoint(self, x, y, z):
        msg = PositionTarget()
        msg.header.stamp      = self.get_clock().now().to_msg()
        msg.header.frame_id   = 'map'
        msg.coordinate_frame  = PositionTarget.FRAME_LOCAL_NED
        msg.position.x        = x
        msg.position.y        = y
        msg.position.z        = z
        msg.type_mask = (
            PositionTarget.IGNORE_VX | PositionTarget.IGNORE_VY | PositionTarget.IGNORE_VZ |
            PositionTarget.IGNORE_AFX | PositionTarget.IGNORE_AFY | PositionTarget.IGNORE_AFZ |
            PositionTarget.IGNORE_YAW_RATE
        )
        self.setpoint_pub.publish(msg)

    def _distance_to_target(self):
        if self.current_pose is None:
            return float('inf')
        p = self.current_pose.pose.position
        return math.sqrt(
            (p.x - self.target_x) ** 2 +
            (p.y - self.target_y) ** 2 +
            (p.z - self.target_z) ** 2
        )


def main():
    rclpy.init()
    node = WaypointNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
