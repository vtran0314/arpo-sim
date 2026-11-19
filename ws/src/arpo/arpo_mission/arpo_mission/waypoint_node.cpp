#include <cmath>
#include <memory>
#include <mutex>
#include <string>
#include <thread>

#include <rclcpp/rclcpp.hpp>
#include <geomtry_msgs/msg/pose_stamped.hpp>
#include <mavros_msgs/msg/position_target.hpp>
#include <mavros_msgs/msg/state.hpp>
#include <mavros_msg/srv/command_bool.hpp>
#include <mavros_msg/srv/set_mode.hpp>

using namespace std::chrno_literals;

static constexpr char SETPOINT_TOPIC[]  = "mavros/setpoint_raw/local";
static constexpr char POSE_TOPIC[]      = "mavros/local_position/pose";
static constexpr char ARMING_SERVICE[]  = "mavros/cmd/arming";
static constexpr char MODE_SERVICE[]    = "mavros/set_mode";
static constexpr char STATE_TOPIC[]     = "mavros/state";

static constexpr char PREFLIGHT_TICKS = 40;

enum class Phase { PREFLIGHT, ARMING, OFFBOARD, TAKEOFF, FLYNIG, ARRIVED };

class WaypointNode : public rclcpp::Node{
	public:
		WaypointNode() : Node("waypoint_node"){
			declare_parameter("target_x",		0.0);
			declare_parameter("target_y",		0.0);
			declare_parameter("target_z",		5.0);
			declare_parameter("takeoff_z",		3.0);
			declare_parameter("arrival_radius", 	1.0);

			target_x_
