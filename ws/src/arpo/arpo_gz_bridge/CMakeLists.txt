cmake_minimum_required(VERSION 3.20)
project(arpo_gz_bridge)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# gz libraries live inside the ROS vendor prefix, not in /usr
list(PREPEND CMAKE_PREFIX_PATH
  /opt/ros/lyrical/opt/gz_transport_vendor
  /opt/ros/lyrical/opt/gz_msgs_vendor)

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(gz-transport REQUIRED)
find_package(gz-msgs REQUIRED)

add_executable(pose_bridge ${CMAKE_CURRENT_SOURCE_DIR}/src/pose_bridge_node.cpp)
target_link_libraries(pose_bridge
  rclcpp::rclcpp
  ${geometry_msgs_TARGETS}
  gz-transport::core
  gz-msgs::gz-msgs)

install(TARGETS pose_bridge
  DESTINATION lib/${PROJECT_NAME})

install(DIRECTORY launch config
  DESTINATION share/${PROJECT_NAME})

ament_package()
