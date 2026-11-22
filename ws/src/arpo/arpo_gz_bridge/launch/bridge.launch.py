import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory

config = os.path.join(
    get_package_share_directory('arpo_gz_bridge'), 'config', 'bridge.yml'
)


def make_pose_bridges(context):
    """One pose bridge node per drone, in that drone's namespace."""
    count = int(LaunchConfiguration('num_uavs').perform(context))
    world = LaunchConfiguration('world_name').perform(context)
    rate  = float(LaunchConfiguration('update_rate').perform(context))
    z_off = float(LaunchConfiguration('z_offset').perform(context))
    return [
        Node(
            package='arpo_gz_bridge',
            executable='pose_bridge',
            namespace=f'uav{i}',
            name='arpo_gz_pose_bridge',
            output='screen',
            parameters=[{
                'model_name':     f'iris_drone_{i}',
                'world_name':     world,
                'update_rate_hz': rate,
                'z_offset':       z_off,
            }],
        )
        for i in range(1, count + 1)
    ]


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('num_uavs',    default_value='1',
                              description='Number of drones to bridge.'),
        DeclareLaunchArgument('world_name',  default_value='arpo'),
        DeclareLaunchArgument('update_rate', default_value='20.0'),
        DeclareLaunchArgument('z_offset',    default_value='0.1'),

        OpaqueFunction(function=make_pose_bridges),

        # Lidar bridge (Gazebo Transport → ROS2) — shared, not per-drone
        Node(
            package='ros_gz_bridge',
            executable='parameter_bridge',
            name='lidar_bridge',
            output='screen',
            parameters=[{'config_file': config}],
        ),

        # Static TF: world → lidar_3d_v2/link/lidar
        # The lidar is spawned at (x=10, y=0, z=0) in gz.launch.py; the sensor
        # sits 0.15 m above the model origin (see lidar/model.sdf sensor pose).
        # Without this transform RViz cannot locate the point cloud in world space.
        Node(
            package='tf2_ros',
            executable='static_transform_publisher',
            name='lidar_tf_publisher',
            output='screen',
            arguments=[
                '--x',          '10.0',
                '--y',          '0.0',
                '--z',          '0.15',
                '--roll',       '0.0',
                '--pitch',      '0.0',
                '--yaw',        '0.0',
                '--frame-id',   'world',
                '--child-frame-id', 'lidar_3d_v2/link/lidar',
            ],
        ),
    ])
