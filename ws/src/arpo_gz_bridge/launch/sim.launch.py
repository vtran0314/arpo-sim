"""
Launches a single FastSwarmSim drone + the Gazebo pose bridge.
Run ign gazebo separately first, then spawn the models, then run this.

Usage:
    ros2 launch arpo_gz_bridge sim.launch.py
    ros2 launch arpo_gz_bridge sim.launch.py world_name:=my_world model_name:=iris_drone_1
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
        DeclareLaunchArgument('world_name',   default_value='default'),
        DeclareLaunchArgument('model_name',   default_value='iris_drone'),
        DeclareLaunchArgument('update_rate',  default_value='20.0'),
        DeclareLaunchArgument('namespace',    default_value=''),
        DeclareLaunchArgument('z_offset',     default_value='0.1'),

        # FastSwarmSim single drone (no RViz, no time coordinator for simplicity)
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(PathJoinSubstitution([
                FindPackageShare('fss_px4_sim'), 'launch', 'px4_rotor_sim_single.launch.py'])),
            launch_arguments={
                'namespace':          LaunchConfiguration('namespace'),
                'enable_rviz':        'false',
                'enable_visualizer':  'true',
            }.items(),
        ),

        # Gazebo pose bridge
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
    ])
