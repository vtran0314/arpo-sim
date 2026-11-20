cmake_minimum_required(VERSION 3.20)
project(uav_interface)

find_package(ament_cmake REQUIRED)
find_package(rosidl_default_generators REQUIRED)

# Generates C++ and Python code for the service.
# Python: from uav_interface.srv import SetPathMode
# C++:    #include "uav_interface/srv/set_path_mode.hpp"
rosidl_generate_interfaces(${PROJECT_NAME}
  "srv/SetPathMode.srv"
)

ament_export_dependencies(rosidl_default_runtime)

if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  set(ament_cmake_copyright_FOUND TRUE)
  set(ament_cmake_cpplint_FOUND TRUE)
  ament_lint_auto_find_test_dependencies()
endif()

ament_package()
