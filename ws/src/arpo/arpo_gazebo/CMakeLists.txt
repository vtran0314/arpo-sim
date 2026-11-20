cmake_minimum_required(VERSION 3.8)
project(arpo_gazebo)

find_package(ament_cmake REQUIRED)

install(DIRECTORY worlds launch
  DESTINATION share/${PROJECT_NAME}
)

ament_package()
