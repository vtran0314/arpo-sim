#!/usr/bin/env python3
# Launch file for running a multi-drone scenario with autonomous mode

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction, SetEnvironmentVariable
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def make_uav_controllers(context):
    """One autonomous pathing node per drone, inside that drone's namespace."""
    count = int(LaunchConfiguration("num_uavs").perform(context))
    return [
        Node(
            package="uav_swarm",
            executable="uav_pathing_node",
            namespace=f"uav{index}",
            name="uav_pathing_node",
            output="screen",
        )
        for index in range(1, count + 1)
    ]


def generate_launch_description():
    num_uavs = LaunchConfiguration("num_uavs")

    return LaunchDescription([
        SetEnvironmentVariable("RCUTILS_COLORIZED_OUTPUT", "1"),
        DeclareLaunchArgument("num_uavs", default_value="1",
                              description="Number of vehicles to launch."),
        DeclareLaunchArgument("enable_pathing", default_value="true",
                              choices=["true", "false"],
                              description="Start uav_pathing_node (square path) for each drone."),
        DeclareLaunchArgument("keyboard_in_xterm", default_value="true",
                              choices=["true", "false"],
                              description="Open the keyboard interface in its own xterm window."),

        DeclareLaunchArgument('world_name',  default_value='arpo'),
        DeclareLaunchArgument('update_rate', default_value='20.0'),
        DeclareLaunchArgument('z_offset',    default_value='0.1',
                              description="Drone Z offset above ground"),

        # Spawn all drones (uav1..uavN) once. The default direct_ros transport runs
        # MAVROS Lite inside PX4, so /uavN/mavros/... exists without extra arguments.
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(PathJoinSubstitution([
                FindPackageShare("fss_px4_sim"), "launch", "px4_rotor_sim_multi.launch.py"])),
            launch_arguments={
                "num_drones": num_uavs,
            }.items(),
        ),

        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(PathJoinSubstitution([
               FindPackageShare('arpo_bringup'), 'launch', 'sim.launch.py'])),
            launch_arguments={
                'num_uavs':    num_uavs,
                'world_name':  LaunchConfiguration('world_name'),
                'update_rate': LaunchConfiguration('update_rate'),
                'z_offset':    LaunchConfiguration('z_offset'),
            }.items(),
        ),

        # Keyboard interface (only if asked to open in xterm; otherwise use `ros2 run`)
        Node(
            package="uav_swarm",
            executable="swarm_keyboard_interface",
            name="keyboard_interface",
            namespace="uav_swarm",
            prefix="xterm -e",
            output="screen",
            parameters=[{"num_uavs": num_uavs}],
            condition=IfCondition(LaunchConfiguration("keyboard_in_xterm")),
        ),

        # Autonomous controllers, one per drone
        OpaqueFunction(
            function=make_uav_controllers,
            condition=IfCondition(LaunchConfiguration("enable_pathing")),
        ),
    ])
