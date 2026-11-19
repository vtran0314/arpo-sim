from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('target_x',   default_value='0'),
        DeclareLaunchArgument('target_y',   default_value='0'),
        DeclareLaunchArgument('target_z',   default_value='0'),
        DeclareLaunchArgument('takeoff_z',  default_value='0'),
        DeclareLaunchArgument('arrival_radius',    default_value='5'),

        Node(
            package='arpo_mission',
            executable='waypoint_node',
            name='waypoint_node',
            parameters=[{'target_x': LaunchConfiguration('target_x'),
                         'target_y': LaunchConfiguration('target_y'),
                         'target_z': LaunchConfiguration('target_z'),
                         'takeoff_z': LaunchConfiguration('takeoff_z'),
                         'arrival_radius': LaunchConfiguration('arrival_radius'),
                }],
            output='screen',
            ) 
])
