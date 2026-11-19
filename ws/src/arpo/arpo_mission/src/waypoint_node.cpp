#include <cmath>
#include <limits>
#include <memory>
#include <optional>
#include <string>

#include "rclcpp/rclcpp.hpp"
#include "geometry_msgs/msg/pose_stamped.hpp"
#include "mavros_msgs/msg/position_target.hpp"
#include "mavros_msgs/msg/state.hpp"
#include "mavros_msgs/srv/command_bool.hpp"
#include "mavros_msgs/srv/set_mode.hpp"

using namespace std::chrono_literals;

static constexpr char SETPOINT_TOPIC[] = "mavros/setpoint_raw/local";
static constexpr char POSE_TOPIC[]     = "mavros/local_position/pose";
static constexpr char STATE_TOPIC[]    = "mavros/state";
static constexpr char ARMING_SERVICE[] = "mavros/cmd/arming";
static constexpr char MODE_SERVICE[]   = "mavros/set_mode";

static constexpr int PREFLIGHT_TICKS = 40;  // 2 s at 20 Hz

enum class Phase { PREFLIGHT, ARMING, OFFBOARD, TAKEOFF, FLYING, ARRIVED };

class WaypointNode : public rclcpp::Node
{
public:
  WaypointNode() : Node("waypoint_node")
  {
    declare_parameter("target_x",       0.0);
    declare_parameter("target_y",       0.0);
    declare_parameter("target_z",       5.0);
    declare_parameter("takeoff_z",      3.0);
    declare_parameter("arrival_radius", 1.0);

    target_x_       = get_parameter("target_x").as_double();
    target_y_       = get_parameter("target_y").as_double();
    target_z_       = get_parameter("target_z").as_double();
    takeoff_z_      = get_parameter("takeoff_z").as_double();
    arrival_radius_ = get_parameter("arrival_radius").as_double();

    // BEST_EFFORT to match FSS publisher — same reason as pose_bridge_node.py
    auto qos = rclcpp::QoS(10).best_effort();

    setpoint_pub_ = create_publisher<mavros_msgs::msg::PositionTarget>(SETPOINT_TOPIC, 10);

    pose_sub_ = create_subscription<geometry_msgs::msg::PoseStamped>(
      POSE_TOPIC, qos,
      [this](geometry_msgs::msg::PoseStamped::SharedPtr msg) { current_pose_ = msg; });

    state_sub_ = create_subscription<mavros_msgs::msg::State>(
      STATE_TOPIC, 10,
      [this](mavros_msgs::msg::State::SharedPtr msg) { vehicle_state_ = msg; });

    arm_client_  = create_client<mavros_msgs::srv::CommandBool>(ARMING_SERVICE);
    mode_client_ = create_client<mavros_msgs::srv::SetMode>(MODE_SERVICE);

    // 20 Hz — drives the state machine, same cadence as Python version
    timer_ = create_wall_timer(50ms, [this]() { timerCb(); });

    RCLCPP_INFO(get_logger(), "WaypointNode started — PREFLIGHT");
  }

private:
  // ---------------------------------------------------------------------------
  void timerCb()
  {
    switch (phase_) {
      case Phase::PREFLIGHT:
        publishHold();
        if (++preflight_ticks_ >= PREFLIGHT_TICKS) {
          phase_ = Phase::ARMING;
          RCLCPP_INFO(get_logger(), "PREFLIGHT done → ARMING");
        }
        break;

      case Phase::ARMING:
        publishHold();
        if (!pending_arm_) {
          auto req = std::make_shared<mavros_msgs::srv::CommandBool::Request>();
          req->value = true;
          pending_arm_ = arm_client_->async_send_request(req);
        } else if (pending_arm_->wait_for(0s) == std::future_status::ready) {
          if (pending_arm_->get()->success) {
            pending_arm_.reset();
            phase_ = Phase::OFFBOARD;
            RCLCPP_INFO(get_logger(), "Armed → OFFBOARD");
          } else {
            pending_arm_.reset();  // retry next tick
          }
        }
        break;

      case Phase::OFFBOARD:
        publishHold();
        if (!pending_mode_) {
          auto req = std::make_shared<mavros_msgs::srv::SetMode::Request>();
          req->custom_mode = "OFFBOARD";
          pending_mode_ = mode_client_->async_send_request(req);
        } else if (pending_mode_->wait_for(0s) == std::future_status::ready) {
          if (vehicle_state_ && vehicle_state_->mode == "OFFBOARD") {
            pending_mode_.reset();
            phase_ = Phase::TAKEOFF;
            RCLCPP_INFO(get_logger(), "OFFBOARD mode set → TAKEOFF");
          } else {
            pending_mode_.reset();  // retry next tick
          }
        }
        break;

      case Phase::TAKEOFF:
        publishSetpoint(0.0, 0.0, takeoff_z_);
        if (current_pose_) {
          double z = current_pose_->pose.position.z;
          if (z >= takeoff_z_ - 0.3) {
            phase_ = Phase::FLYING;
            RCLCPP_INFO(get_logger(), "Reached takeoff altitude %.2f m → FLYING", z);
          }
        }
        break;

      case Phase::FLYING:
        // TODO: add your movement logic here
        publishSetpoint(target_x_, target_y_, target_z_);
        if (distanceToTarget() < arrival_radius_) {
          phase_ = Phase::ARRIVED;
          RCLCPP_INFO(get_logger(), "Arrived at target → ARRIVED");
        }
        break;

      case Phase::ARRIVED:
        publishSetpoint(target_x_, target_y_, target_z_);
        RCLCPP_INFO_ONCE(get_logger(), "Holding at target.");
        break;
    }
  }

  // ---------------------------------------------------------------------------
  void publishHold()
  {
    if (!current_pose_) {
      publishSetpoint(0.0, 0.0, 0.0);
      return;
    }
    auto & p = current_pose_->pose.position;
    publishSetpoint(p.x, p.y, p.z);
  }

  void publishSetpoint(double x, double y, double z)
  {
    using PT = mavros_msgs::msg::PositionTarget;
    PT msg;
    msg.header.stamp     = now();
    msg.header.frame_id  = "map";
    msg.coordinate_frame = PT::FRAME_LOCAL_NED;
    msg.position.x = x;
    msg.position.y = y;
    msg.position.z = z;
    msg.type_mask =
      PT::IGNORE_VX | PT::IGNORE_VY | PT::IGNORE_VZ |
      PT::IGNORE_AFX | PT::IGNORE_AFY | PT::IGNORE_AFZ |
      PT::IGNORE_YAW_RATE;
    setpoint_pub_->publish(msg);
  }

  double distanceToTarget()
  {
    if (!current_pose_) return std::numeric_limits<double>::infinity();
    auto & p = current_pose_->pose.position;
    return std::sqrt(
      std::pow(p.x - target_x_, 2) +
      std::pow(p.y - target_y_, 2) +
      std::pow(p.z - target_z_, 2));
  }

  // ---------------------------------------------------------------------------
  // Parameters
  double target_x_, target_y_, target_z_, takeoff_z_, arrival_radius_;

  // State
  Phase phase_           = Phase::PREFLIGHT;
  int   preflight_ticks_ = 0;
  geometry_msgs::msg::PoseStamped::SharedPtr current_pose_;
  mavros_msgs::msg::State::SharedPtr         vehicle_state_;

  // Pending service futures — nullopt means no call in flight (mirrors Python's _pending_future)
  using ArmFuture  = rclcpp::Client<mavros_msgs::srv::CommandBool>::SharedFuture;
  using ModeFuture = rclcpp::Client<mavros_msgs::srv::SetMode>::SharedFuture;
  std::optional<ArmFuture>  pending_arm_;
  std::optional<ModeFuture> pending_mode_;

  // ROS handles
  rclcpp::Publisher<mavros_msgs::msg::PositionTarget>::SharedPtr   setpoint_pub_;
  rclcpp::Subscription<geometry_msgs::msg::PoseStamped>::SharedPtr pose_sub_;
  rclcpp::Subscription<mavros_msgs::msg::State>::SharedPtr         state_sub_;
  rclcpp::Client<mavros_msgs::srv::CommandBool>::SharedPtr         arm_client_;
  rclcpp::Client<mavros_msgs::srv::SetMode>::SharedPtr             mode_client_;
  rclcpp::TimerBase::SharedPtr                                     timer_;
};

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<WaypointNode>());
  rclcpp::shutdown();
  return 0;
}
