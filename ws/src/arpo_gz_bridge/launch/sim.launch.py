"""
Launches a single FastSwarmSim drone + the Gazebo pose bridge + lidar bridge.
Run start-gazebo.sh first to start Gazebo and spawn models, then run this.

Usage:
    ros2 launch arpo_gz_bridge sim.launch.py
    ros2 launch arpo_gz_bridge sim.launch.py world_name:=arpo model_name:=iris_drone_1

ROS2 topics published:
    /lidar/scan/points  (sensor_msgs/msg/PointCloud2)  — lidar point cloud
"""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.actions import IncludeLaunchDescription
from launch_ros.substitutions import FindPackageShare
from launch.substitutions import PathJoinSubstitution


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('world_name',   default_value='arpo'),
        DeclareLaunchArgument('model_name',   default_value='iris_drone'),
        DeclareLaunchArgument('update_rate',  default_value='20.0'),
        DeclareLaunchArgument('namespace',    default_value=''),
        DeclareLaunchArgument('z_offset',     default_value='0.1'),

        # ── FastSwarmSim single drone ──────────────────────────────────────
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(PathJoinSubstitution([
                FindPackageShare('fss_px4_sim'), 'launch', 'px4_rotor_sim_single.launch.py'])),
            launch_arguments={
                'namespace':          LaunchConfiguration('namespace'),
                'enable_rviz':        'false',
                'enable_visualizer':  'true',
            }.items(),
        ),

        # ── Drone pose bridge (FSS → Gazebo) ──────────────────────────────
        Node(
            package='arpo_gz_bridge',
            executable='pose_bridge',
            name='arpo_gz_pose_bridge',
            output='screen',
            parameters=[{
                'model_name':     LaunchConfiguration('model_name'),
                'world_name':     LaunchConfiguration('world_name'),
                'update_rate_hz': LaunchConfiguration('update_rate'),
                'z_offset':       LaunchConfiguration('z_offset'),
            }],
        ),

        # ── Lidar bridge (Gazebo → ROS2) ──────────────────────────────────
        #
        # ros_gz_bridge translates Gazebo transport messages into ROS2 messages.
        #
        # Argument format:
        #   <gz_topic> @ <ros2_type> [ <gz_type>
        #
        #   @  separates the topic name from the type specification
        #   [  means one-way: Gazebo → ROS2  (use ] for ROS2 → Gazebo)
        #
        # The lidar sensor publishes on /lidar/scan/points (Gazebo transport).
        # We bridge it to the same topic name in ROS2 as PointCloud2.
        #
        Node(
            package='ros_gz_bridge',
            executable='parameter_bridge',
            name='lidar_bridge',
            output='screen',
            arguments=[
                '/lidar/scan/points@sensor_msgs/msg/PointCloud2[gz.msgs.PointCloudPacked',
            ],
        ),
    ])
