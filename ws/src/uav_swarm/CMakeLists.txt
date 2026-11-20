cmake_minimum_required(VERSION 3.20)
project(uav_swarm)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(mavros_msgs REQUIRED)
find_package(uav_interface REQUIRED)

# --- C++ pathing node ---
add_executable(uav_pathing_node src/uav_pathing_node.cpp)
target_link_libraries(uav_pathing_node PUBLIC
  rclcpp::rclcpp
  ${geometry_msgs_TARGETS}
  ${mavros_msgs_TARGETS}
  ${uav_interface_TARGETS})
install(TARGETS uav_pathing_node
  DESTINATION lib/${PROJECT_NAME})

# --- Python keyboard interface ---
# Installed without the .py extension so `executable='swarm_keyboard_interface'` works
install(PROGRAMS scripts/swarm_keyboard_interface.py
  DESTINATION lib/${PROJECT_NAME}
  RENAME swarm_keyboard_interface)

# --- Launch files ---
install(DIRECTORY launch
  DESTINATION share/${PROJECT_NAME})

if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  set(ament_cmake_copyright_FOUND TRUE)
  set(ament_cmake_cpplint_FOUND TRUE)
  ament_lint_auto_find_test_dependencies()
endif()

ament_package()
