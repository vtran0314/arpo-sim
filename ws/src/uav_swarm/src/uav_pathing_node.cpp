// Node that moves a drone autonomously in a square pattern.
//
// Run one instance per drone inside that drone's namespace (e.g. /uav1), so the
// relative names below resolve to /uav1/mavros/... and /uav1/uav_auto/path_mode.
//
// Behaviour:
//   * Starts in AUTO mode and streams position setpoints for a square path.
//   * The keyboard interface calls uav_auto/path_mode (uav_interface/srv/SetPathMode):
//       uav_auto = 0 (MANUAL) -> stop publishing so the keyboard has control
//       uav_auto = 1 (AUTO)   -> resume the square from the current waypoint
//   * Arming and OFFBOARD are handled by FSS MAVROS Lite (mavros/cmd/arming,
//     mavros/set_mode); this node doesn't arm the drone itself.

#include <chrono>
#include <cmath>
#include <functional>
#include <memory>
#include <string>
#include <vector>

#include "geometry_msgs/msg/pose_stamped.hpp"
#include "mavros_msgs/msg/position_target.hpp"
#include "mavros_msgs/msg/state.hpp"
#include "rclcpp/rclcpp.hpp"
#include "uav_interface/srv/set_path_mode.hpp"

using namespace std::chrono_literals;
using std::placeholders::_1;
using std::placeholders::_2;

using PositionTarget = mavros_msgs::msg::PositionTarget;
using PoseStamped = geometry_msgs::msg::PoseStamped;
using SetPathMode = uav_interface::srv::SetPathMode;

struct Waypoint
{
    double x;
    double y;
    double z;
};

class UAVPathingNode : public rclcpp::Node
{
public:
    UAVPathingNode() : Node("uav_pathing_node")
    {
        // Square parameters (metres, relative to where the drone starts)
        square_size_ = declare_parameter("square_size", 5.0);
        altitude_ = declare_parameter("altitude", 3.0);
        tolerance_ = declare_parameter("waypoint_tolerance", 0.3);
        const double rate_hz = declare_parameter("publish_rate", 20.0);

        // MAVROS Lite uses SensorDataQoS for these topics
        const auto qos = rclcpp::SensorDataQoS();

        //For controling velocity of UAV
        setpoint_pub_ = create_publisher<PositionTarget>("mavros/setpoint_raw/local", qos);

        //Subscribe to the position of the node
        pose_sub_ = create_subscription<PoseStamped>(
            "mavros/local_position/pose", qos,
            std::bind(&UAVPathingNode::pose_callback, this, _1));

        //Subscribing to state of the node
        state_sub_ = create_subscription<mavros_msgs::msg::State>(
            "mavros/state", 10,
            [this](const mavros_msgs::msg::State::SharedPtr msg) { state_ = *msg; });

        //Creating Service for Auto or Manual pathing
        path_mode_srv_ = create_service<SetPathMode>(
            "uav_auto/path_mode",
            std::bind(&UAVPathingNode::path_mode_callback, this, _1, _2));

        timer_ = create_wall_timer(
            std::chrono::duration<double>(1.0 / rate_hz),
            std::bind(&UAVPathingNode::timer_callback, this));

        RCLCPP_INFO(get_logger(), "pathing node started in AUTO mode (square %.1f m at %.1f m)",
                    square_size_, altitude_);
    }

private:
    // Remember the start position the first time we hear from the drone,
    // then build the square around it.
    void pose_callback(const PoseStamped::SharedPtr msg)
    {
        pose_ = msg->pose;
        if (!have_pose_) {
            have_pose_ = true;
            build_square(pose_.position.x, pose_.position.y, pose_.position.z);
        }
    }

    // Takeoff point, then the four corners of the square (ENU: x East, y North, z Up)
    void build_square(double x0, double y0, double z0)
    {
        const double z = z0 + altitude_;
        waypoints_ = {
            {x0, y0, z},                              // climb above the start point
            {x0 + square_size_, y0, z},               // east
            {x0 + square_size_, y0 + square_size_, z}, // north-east
            {x0, y0 + square_size_, z},               // north
            {x0, y0, z},                              // back to start
        };
        current_wp_ = 0;
        RCLCPP_INFO(get_logger(), "square built around start (%.1f, %.1f, %.1f)", x0, y0, z0);
    }

    // Square movement: publish the current waypoint and advance when we reach it
    void timer_callback()
    {
        if (!auto_mode_ || !have_pose_) {
            return; // manual mode: the keyboard interface is publishing setpoints
        }

        const Waypoint &wp = waypoints_[current_wp_];

        // Only advance once we are actually flying the path
        if (state_.armed && state_.mode == "OFFBOARD" && reached(wp)) {
            // Waypoint 0 is takeoff; afterwards loop around corners 1..4
            current_wp_ = (current_wp_ + 1 < waypoints_.size()) ? current_wp_ + 1 : 1;
            RCLCPP_INFO(get_logger(), "reached waypoint, heading to %zu", current_wp_);
        }

        publish_setpoint(waypoints_[current_wp_]);
    }

    bool reached(const Waypoint &wp) const
    {
        const double dx = wp.x - pose_.position.x;
        const double dy = wp.y - pose_.position.y;
        const double dz = wp.z - pose_.position.z;
        return std::sqrt(dx * dx + dy * dy + dz * dz) < tolerance_;
    }

    void publish_setpoint(const Waypoint &wp)
    {
        PositionTarget msg;
        msg.header.stamp = now();
        msg.header.frame_id = "map";
        // ROS-side ENU; MAVROS Lite converts to MAVLink LOCAL_NED
        msg.coordinate_frame = PositionTarget::FRAME_LOCAL_NED;
        msg.position.x = wp.x;
        msg.position.y = wp.y;
        msg.position.z = wp.z;
        msg.yaw_rate = 0.0; // hold current heading
        // Position-only setpoint
        msg.type_mask = PositionTarget::IGNORE_VX | PositionTarget::IGNORE_VY |
                        PositionTarget::IGNORE_VZ | PositionTarget::IGNORE_AFX |
                        PositionTarget::IGNORE_AFY | PositionTarget::IGNORE_AFZ |
                        PositionTarget::IGNORE_YAW;
        setpoint_pub_->publish(msg);
    }

    // Called by the keyboard interface (t = manual, r = auto)
    void path_mode_callback(const std::shared_ptr<SetPathMode::Request> request,
                            std::shared_ptr<SetPathMode::Response> response)
    {
        if (request->uav_auto == SetPathMode::Request::MANUAL) {
            auto_mode_ = false;
            response->success = true;
            response->message = "manual mode: autonomous path paused";
        } else if (request->uav_auto == SetPathMode::Request::AUTO) {
            auto_mode_ = true;
            response->success = true;
            response->message = "auto mode: resuming square path";
        } else {
            response->success = false;
            response->message = "uav_auto must be 0 (MANUAL) or 1 (AUTO)";
        }
        RCLCPP_INFO(get_logger(), "%s", response->message.c_str());
    }

    // Parameters
    double square_size_;
    double altitude_;
    double tolerance_;

    // State
    bool auto_mode_ = true;
    bool have_pose_ = false;
    geometry_msgs::msg::Pose pose_;
    mavros_msgs::msg::State state_;
    std::vector<Waypoint> waypoints_;
    size_t current_wp_ = 0;

    // ROS interfaces
    rclcpp::Publisher<PositionTarget>::SharedPtr setpoint_pub_;
    rclcpp::Subscription<PoseStamped>::SharedPtr pose_sub_;
    rclcpp::Subscription<mavros_msgs::msg::State>::SharedPtr state_sub_;
    rclcpp::Service<SetPathMode>::SharedPtr path_mode_srv_;
    rclcpp::TimerBase::SharedPtr timer_;
};

int main(int argc, char *argv[])
{
    rclcpp::init(argc, argv);
    rclcpp::spin(std::make_shared<UAVPathingNode>());
    rclcpp::shutdown();
    return 0;
}
