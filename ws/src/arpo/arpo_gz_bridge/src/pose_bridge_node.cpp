#include <chrono>
#include <memory>
#include <string>

#include <rclcpp/rclcpp.hpp>
#include <geometry_msgs/msg/pose_stamped.hpp>
#include <gz/transport/Node.hh>
#include <gz/msgs/pose.pb.h>
#include <gz/msgs/boolean.pb.h>

class PoseBridgeNode : public rclcpp::Node
{
public:
  PoseBridgeNode()
  : Node("arpo_gz_pose_bridge")
  {
    declare_parameter("model_name",     "iris_drone");
    declare_parameter("world_name",     "default");
    declare_parameter("update_rate_hz", 20.0);
    declare_parameter("ros_topic",      "mavros/local_position/pose");
    declare_parameter("z_offset",       0.1);

    model_    = get_parameter("model_name").as_string();
    world_    = get_parameter("world_name").as_string();
    topic_    = get_parameter("ros_topic").as_string();
    z_offset_ = get_parameter("z_offset").as_double();

    double rate      = get_parameter("update_rate_hz").as_double();
    min_interval_ns_ = static_cast<int64_t>(1e9 / rate);
    log_every_n_     = std::max(1, static_cast<int>(rate));

    service_ = "/world/" + world_ + "/set_pose";

    auto qos = rclcpp::QoS(10).best_effort();
    sub_ = create_subscription<geometry_msgs::msg::PoseStamped>(
      topic_, qos,
      [this](geometry_msgs::msg::PoseStamped::SharedPtr msg) { pose_cb(msg); });

    RCLCPP_INFO(get_logger(),
      "pose_bridge: %s → %s (model=\"%s\", %.0f Hz, z_offset=%.3f m)",
      topic_.c_str(), service_.c_str(), model_.c_str(), rate, z_offset_);
  }

private:
  void pose_cb(const geometry_msgs::msg::PoseStamped::SharedPtr msg)
  {
    ++recv_count_;

    auto now_ns = std::chrono::steady_clock::now().time_since_epoch().count();
    if (now_ns - last_time_ns_ < min_interval_ns_) return;
    last_time_ns_ = now_ns;
    ++send_count_;

    const auto & p = msg->pose.position;
    const auto & q = msg->pose.orientation;

    if (send_count_ % log_every_n_ == 0) {
      RCLCPP_INFO(get_logger(),
        "[bridge] recv=%zu sent=%zu pos=(%.2f, %.2f, %.2f)",
        recv_count_, send_count_, p.x, p.y, p.z + z_offset_);
    }

    gz::msgs::Pose req;
    req.set_name(model_);
    req.mutable_position()->set_x(p.x);
    req.mutable_position()->set_y(p.y);
    req.mutable_position()->set_z(p.z + z_offset_);
    req.mutable_orientation()->set_x(q.x);
    req.mutable_orientation()->set_y(q.y);
    req.mutable_orientation()->set_z(q.z);
    req.mutable_orientation()->set_w(q.w);

    // Async — does not block the subscription callback while waiting for Gazebo.
    auto weak = weak_from_this();
    std::function<void(const gz::msgs::Boolean &, bool)> cb =
      [weak](const gz::msgs::Boolean & rep, const bool result) {
        if (!result || !rep.data()) {
          if (auto node = weak.lock()) {
            RCLCPP_WARN(node->get_logger(),
              "[bridge] set_pose failed (transport_ok=%d gz_ok=%d)", result, rep.data());
          }
        }
      };
    gz_node_.Request<gz::msgs::Pose, gz::msgs::Boolean>(service_, req, cb);
  }

  rclcpp::Subscription<geometry_msgs::msg::PoseStamped>::SharedPtr sub_;
  gz::transport::Node gz_node_;

  std::string model_, world_, topic_, service_;
  double      z_offset_{0.1};
  int64_t     min_interval_ns_{50'000'000LL};
  int64_t     last_time_ns_{0};
  int         log_every_n_{20};
  size_t      recv_count_{0};
  size_t      send_count_{0};
};

int main(int argc, char * argv[])
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<PoseBridgeNode>());
  rclcpp::shutdown();
  return 0;
}
