#!/usr/bin/env python3

import os
import sys
import time
import select
import tty
import termios
from threading import RLock

import rclpy
from uav_interface.srv import SetPathMode
from geometry_msgs.msg import PoseStamped
from mavros_msgs.msg import PositionTarget, State
from mavros_msgs.srv import CommandBool, SetMode
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from rclpy.signals import SignalHandlerOptions

KEY_RELEASE_TIMEOUT = 0.6
PUBLISH_PERIOD = 0.05
MOTION_KEYS = "wasdqejk"

MANUAL = 0
AUTO = 1


class KeyboardInterface(Node):
    def __init__(self):
        super().__init__("keyboard_interface")

        # Attributes for setpoint
        self.speed = 1.0        # m/s for w/a/s/d and q/e
        self.yaw_speed = 0.5    # rad/s for j/k
        self.altitude = 0.0     # target z (ENU, metres) held while in manual mode
        self.current_z = None   # last z reported by the selected UAV
        self.vx = self.vy = self.vz = self.yaw_rate = 0.0
        self.last_motion_key_time = 0.0
        self.declare_parameter("num_uavs", 1)
        self.num_uavs = max(1, int(self.get_parameter("num_uavs").value))

        # States for interface (reflect the currently selected UAV)
        self.mode = "UNKNOWN"
        self.armed = False
        self.lock = RLock()
        self.uav_number = 1
        self.uav_auto = AUTO

        # Per-UAV ROS objects, (re)created by _connect()
        self.state_sub = None
        self.pose_sub = None
        self.setpoint_pub = None
        self.arm_client = None
        self.mode_client = None
        self.auto_client = None
        self._connect(self.uav_number)

        # Created once; always publishes to whichever UAV is selected
        self.timer = self.create_timer(PUBLISH_PERIOD, self._publish)

    # ------------------------------------------------------------------ #
    # Connection management
    # ------------------------------------------------------------------ #
    def _connect(self, uav_number):
        """Tear down the previous UAV's pubs/subs/clients and attach to uav_number."""
        self._disconnect()

        # Absolute names so the node's own namespace isn't prepended
        prefix = f"/uav{uav_number}"
        self.setpoint_topic = f"{prefix}/mavros/setpoint_raw/local"
        self.state_topic = f"{prefix}/mavros/state"
        self.pose_topic = f"{prefix}/mavros/local_position/pose"
        self.arming_service = f"{prefix}/mavros/cmd/arming"  # FSS MAVROS Lite
        self.mode_service = f"{prefix}/mavros/set_mode"      # FSS MAVROS Lite
        self.path_mode_service = f"{prefix}/uav_auto/path_mode"

        self.state_sub = self.create_subscription(State, self.state_topic, self._state_cb, 10)
        self.pose_sub = self.create_subscription(
            PoseStamped, self.pose_topic, self._pose_cb, qos_profile_sensor_data)
        self.setpoint_pub = self.create_publisher(PositionTarget, self.setpoint_topic, 10)
        self.arm_client = self.create_client(CommandBool, self.arming_service)
        self.mode_client = self.create_client(SetMode, self.mode_service)
        self.auto_client = self.create_client(SetPathMode, self.path_mode_service)

        # Forget everything we knew about the previous UAV
        self.mode = "UNKNOWN"
        self.armed = False
        self.current_z = None
        self.uav_auto = AUTO

    def _disconnect(self):
        if self.state_sub: self.destroy_subscription(self.state_sub)
        if self.pose_sub: self.destroy_subscription(self.pose_sub)
        if self.setpoint_pub: self.destroy_publisher(self.setpoint_pub)
        if self.arm_client: self.destroy_client(self.arm_client)
        if self.mode_client: self.destroy_client(self.mode_client)
        if self.auto_client: self.destroy_client(self.auto_client)
        self.state_sub = self.pose_sub = self.setpoint_pub = None
        self.arm_client = self.mode_client = self.auto_client = None

    # ------------------------------------------------------------------ #
    # Callbacks
    # ------------------------------------------------------------------ #
    def _state_cb(self, msg):
        self.armed, self.mode = msg.armed, msg.mode

    def _pose_cb(self, msg):
        self.current_z = msg.pose.position.z

    # If nothing is pressed, it will stop all movements and the drone will stop moving.
    def _publish(self):
        with self.lock:
            # Only stream manual setpoints in manual mode, so we don't fight the
            # autonomous pathing node for control of the vehicle.
            if self.uav_auto != MANUAL:
                return
            if (self.last_motion_key_time and
                    time.monotonic() - self.last_motion_key_time > KEY_RELEASE_TIMEOUT):
                self._zero_velocity()
            self.altitude += self.vz * PUBLISH_PERIOD
            msg = self._build_setpoint()
        self.setpoint_pub.publish(msg)

    def _build_setpoint(self):
        """Build a MAVROS local setpoint in the ROS ENU convention.

        MAVROS converts this ROS-side representation to MAVLink LOCAL_NED.
        The mask selects x/y velocity, z position and yaw rate
        (velocity.z is left at 0).
        """
        msg = PositionTarget()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = "map"
        msg.coordinate_frame = PositionTarget.FRAME_LOCAL_NED
        msg.velocity.x, msg.velocity.y = self.vx, self.vy
        msg.position.z = self.altitude
        msg.yaw_rate = self.yaw_rate
        msg.type_mask = (PositionTarget.IGNORE_PX | PositionTarget.IGNORE_PY |
                         PositionTarget.IGNORE_AFX |
                         PositionTarget.IGNORE_AFY | PositionTarget.IGNORE_AFZ |
                         PositionTarget.IGNORE_YAW)
        return msg

    # ------------------------------------------------------------------ #
    # Keyboard actions
    # ------------------------------------------------------------------ #
    def set_key(self, key):
        if key not in MOTION_KEYS and key != " ":
            return
        if key != " ":
            if not self.armed:
                self.get_logger().warning(f"uav{self.uav_number} is not armed; arm first with z")
                return
            if self.uav_auto != MANUAL:
                self.get_logger().warning(f"uav{self.uav_number} is in auto mode; press t for manual")
                return
        with self.lock:
            if key == "w": self.vx, self.vy = self.speed, 0.0          # Move UAV forward
            elif key == "s": self.vx, self.vy = -self.speed, 0.0       # Move UAV back
            elif key == "a": self.vx, self.vy = 0.0, self.speed        # Move UAV left
            elif key == "d": self.vx, self.vy = 0.0, -self.speed       # Move UAV right
            elif key == "q": self.vz, self.yaw_rate = self.speed, 0.0  # Move UAV up
            elif key == "e": self.vz, self.yaw_rate = -self.speed, 0.0  # Move UAV down
            elif key == "j": self.vz, self.yaw_rate = 0.0, self.yaw_speed   # Yaw left
            elif key == "k": self.vz, self.yaw_rate = 0.0, -self.yaw_speed  # Yaw right
            elif key == " ":
                self.stop()                                            # Stop UAV movement
                return
            self.last_motion_key_time = time.monotonic()

    def arm(self, value=True):
        if not self.arm_client.wait_for_service(timeout_sec=0.2):
            self.get_logger().warning(f"{self.arming_service} is unavailable")
            return
        request = CommandBool.Request(); request.value = value
        self.arm_client.call_async(request)

    def offboard(self):
        if not self.armed:
            self.get_logger().warning("refusing OFFBOARD request while the vehicle is disarmed; arm first with z")
            return
        if not self.mode_client.wait_for_service(timeout_sec=0.2):
            self.get_logger().warning(f"{self.mode_service} is unavailable")
            return
        request = SetMode.Request(); request.custom_mode = "OFFBOARD"
        self.mode_client.call_async(request)

    # 1 is auto, 0 is manual
    def change_mode(self, new_mode, wait=False):
        """Ask the pathing node to switch modes. Local state only changes once it replies."""
        if new_mode == self.uav_auto:
            self.get_logger().warning("UAV is already in that mode")
            return
        if not self.auto_client.wait_for_service(timeout_sec=0.2):
            self.get_logger().warning(f"{self.path_mode_service} is unavailable")
            return

        if new_mode == MANUAL:
            # Hold the current altitude instead of commanding z = 0
            with self.lock:
                self.stop()
                if self.current_z is not None:
                    self.altitude = self.current_z

        request = SetPathMode.Request(); request.uav_auto = new_mode
        future = self.auto_client.call_async(request)
        future.add_done_callback(lambda f, m=new_mode: self._mode_done(f, m))
        if wait:
            rclpy.spin_until_future_complete(self, future, timeout_sec=1.0)

    def _mode_done(self, future, new_mode):
        if future.cancelled() or future.exception() is not None:
            self.get_logger().error(f"path mode change failed: {future.exception()}")
            return
        response = future.result()
        # Assumes SetPathMode.Response has a `success` field; treat missing as success
        if getattr(response, "success", True):
            with self.lock:
                self.uav_auto = new_mode
        else:
            self.get_logger().warning("pathing node rejected the mode change")

    def uav_selection(self, increment):
        # Hand the current UAV back to autonomous control before leaving it
        if self.uav_auto == MANUAL:
            self.change_mode(AUTO, wait=True)
        with self.lock:
            self.stop()
            if increment == 1:
                # Go to next UAV, wrap from max to 1
                self.uav_number = self.uav_number % self.num_uavs + 1
            else:
                # Go to previous UAV, wrap from 1 to max
                self.uav_number = (self.uav_number - 2) % self.num_uavs + 1
            self._connect(self.uav_number)
        self.get_logger().info(f"selected uav{self.uav_number}")

    def _zero_velocity(self):
        self.vx = self.vy = self.vz = self.yaw_rate = 0.0
        self.last_motion_key_time = 0.0

    def stop(self):
        with self.lock:
            self._zero_velocity()


def main():
    # Expected Behavior:
    # If drone is not armed or in auto mode, and user presses on any movement keys
    #   the interface will alert the user.
    # Additionally, if the user tries to select the same mode while the UAV
    #   is already in that mode, the interface will alert the user that the UAV
    #   is already in that mode.
    # Pressing 9 or 0 switches between UAV numbers.

    rclpy.init(signal_handler_options=SignalHandlerOptions.NO)
    node = None
    old = None
    try:
        node = KeyboardInterface()
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd) if sys.stdin.isatty() else None
        if old:
            tty.setcbreak(fd)
            print("keyboard control | w/a/s/d move, q/e altitude, j/k yaw | +/- speed, [/] yaw speed | "
                  "z arm, c disarm, x OFFBOARD | t manual, r auto | 9/0 switch uav | space stop | Ctrl-C exit",
                  flush=True)
            while rclpy.ok():
                rclpy.spin_once(node, timeout_sec=0.02)
                ready, _, _ = select.select([sys.stdin], [], [], 0.02)
                if not ready: continue
                # os.read bypasses Python's stdin buffer so select() never misses keys
                key = os.read(fd, 1).decode(errors="ignore").lower()
                if key == "\x03": break

                if key == "x": node.offboard()                                   # OFFBOARD mode
                elif key == "z": node.arm(True)                                  # Arm UAV
                elif key == "c": node.arm(False)                                 # Disarm UAV
                elif key == "t": node.change_mode(MANUAL)                        # Manual Mode
                elif key == "r": node.change_mode(AUTO)                          # Auto Mode
                elif key == "+": node.speed = min(10.0, round(node.speed + 0.1, 1))   # Increase speed
                elif key == "-": node.speed = max(0.0, round(node.speed - 0.1, 1))    # Decrease speed
                elif key == "]": node.yaw_speed = min(3.0, round(node.yaw_speed + 0.1, 1))
                elif key == "[": node.yaw_speed = max(0.0, round(node.yaw_speed - 0.1, 1))
                elif key == "0": node.uav_selection(1)                           # Next UAV
                elif key == "9": node.uav_selection(0)                           # Previous UAV
                else: node.set_key(key)
                print("\ruav{} {:<6} mode={:<10} armed={} speed={:.1f} yaw_speed={:.1f} "
                      "vx={:+.1f} vy={:+.1f} vz={:+.1f} yaw={:+.2f}   ".format(
                          node.uav_number, "MANUAL" if node.uav_auto == MANUAL else "AUTO",
                          node.mode, node.armed, node.speed, node.yaw_speed,
                          node.vx, node.vy, node.vz, node.yaw_rate), end="", flush=True)
        else:
            node.get_logger().warning("stdin is not a tty; keyboard control disabled (run with `ros2 run` in a terminal)")
            rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        # Drones are meant to act as adversary
        if old: termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old)
        if node:
            node.destroy_node()
        if rclpy.ok(): rclpy.shutdown()


if __name__ == "__main__":
    main()
