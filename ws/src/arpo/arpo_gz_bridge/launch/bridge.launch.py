import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory

config = os.path.join(
    get_package_share_directory('arpo_gz_bridge'), 'config', 'bridge.yml'
)

def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('world_name',  default_value='arpo'),
        DeclareLaunchArgument('model_name',  default_value='iris_drone'),
        DeclareLaunchArgument('update_rate', default_value='20.0'),
        DeclareLaunchArgument('namespace',   default_value=''),
        DeclareLaunchArgument('z_offset',    default_value='0.1'),

        # Drone pose bridge (FSS → Gazebo)
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

        # Lidar bridge (Gazebo Transport → ROS2)
        Node(
            package='ros_gz_bridge',
            executable='parameter_bridge',
            name='lidar_bridge',
            output='screen',
            parameters=[{'config_file': config}],
            #parameters=[{'config_file': '/home/dev/ws/src/arpo/arpo_gz_bridge/config/bridge.yml'}],
            #arguments=[
            #    '/lidar/scan/points@sensor_msgs/msg/PointCloud2[gz.msgs.PointCloudPacked',
            #],
        ),
    ])
