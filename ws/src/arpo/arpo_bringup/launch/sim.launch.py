from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('world_name',  default_value='arpo'),
        DeclareLaunchArgument('model_name',  default_value='iris_drone'),
        DeclareLaunchArgument('update_rate', default_value='20.0'),
        DeclareLaunchArgument('namespace',   default_value=''),
        DeclareLaunchArgument('z_offset',    default_value='0.1'),

        # Gazebo world + model spawning
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(PathJoinSubstitution([
                FindPackageShare('arpo_gazebo'), 'launch', 'gz.launch.py'])),
        ),

        # Pose bridge (FSS → Gazebo) + lidar bridge (Gazebo → ROS2)
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(PathJoinSubstitution([
                FindPackageShare('arpo_gz_bridge'), 'launch', 'bridge.launch.py'])),
            launch_arguments={
                'world_name':  LaunchConfiguration('world_name'),
                'model_name':  LaunchConfiguration('model_name'),
                'update_rate': LaunchConfiguration('update_rate'),
                'namespace':   LaunchConfiguration('namespace'),
                'z_offset':    LaunchConfiguration('z_offset'),
            }.items(),
        ),
    ])
