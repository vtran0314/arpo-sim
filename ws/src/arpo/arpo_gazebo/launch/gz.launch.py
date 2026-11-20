import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, OpaqueFunction, RegisterEventHandler
from launch.event_handlers import OnProcessStart, OnProcessExit
from launch.substitutions import LaunchConfiguration
from ament_index_python.packages import get_package_share_directory


def spawn_drones(context, models_dir, wait_for_gazebo):
    """Spawn iris_drone_1..iris_drone_N, each offset 3 m apart on the X axis."""
    count = int(LaunchConfiguration('num_uavs').perform(context))
    drones = []
    for i in range(1, count + 1):
        x_offset = (i - 1) * 3.0
        drones.append(ExecuteProcess(
            cmd=['gz', 'service', '-s', '/world/arpo/create',
                 '--reqtype', 'gz.msgs.EntityFactory',
                 '--reptype', 'gz.msgs.Boolean',
                 '--req', f'sdf_filename: "{models_dir}/iris_drone/model.sdf", '
                          f'name: "iris_drone_{i}", '
                          f'pose: {{position: {{x: {x_offset}, y: 0, z: 0}}}}',
                 '--timeout', '5000'],
            output='screen',
        ))
    return drones


def make_spawn_actions(context):
    pkg_arpo_description = get_package_share_directory('arpo_description')
    models_dir = os.path.join(pkg_arpo_description, 'models')

    wait_for_gazebo = ExecuteProcess(
        cmd=['bash', '-c',
             'until gz service -l 2>/dev/null | grep -q "/world/arpo/create"; '
             'do sleep 1; done && echo "Gazebo ready."'],
        output='screen',
    )

    spawn_stadium = ExecuteProcess(
        cmd=['gz', 'service', '-s', '/world/arpo/create',
             '--reqtype', 'gz.msgs.EntityFactory',
             '--reptype', 'gz.msgs.Boolean',
             '--req', f'sdf_filename: "{models_dir}/gillette_stadium/model.sdf"',
             '--timeout', '5000'],
        output='screen',
    )

    spawn_lidar = ExecuteProcess(
        cmd=['gz', 'service', '-s', '/world/arpo/create',
             '--reqtype', 'gz.msgs.EntityFactory',
             '--reptype', 'gz.msgs.Boolean',
             '--req', f'sdf_filename: "{models_dir}/lidar/model.sdf", '
                      'pose: {position: {x: 10, y: 0, z: 0}}',
             '--timeout', '5000'],
        output='screen',
    )

    drones = spawn_drones(context, models_dir, wait_for_gazebo)

    pkg_arpo_gazebo = get_package_share_directory('arpo_gazebo')
    world_sdf = os.path.join(pkg_arpo_gazebo, 'worlds', 'arpo_world.sdf')
    models_dir_full = os.path.join(get_package_share_directory('arpo_description'), 'models')

    gz_sim = ExecuteProcess(
        cmd=['gz', 'sim', world_sdf],
        additional_env={'GZ_SIM_RESOURCE_PATH': models_dir_full},
        output='screen',
    )

    return [
        gz_sim,
        RegisterEventHandler(
            OnProcessStart(
                target_action=gz_sim,
                on_start=[wait_for_gazebo],
            )
        ),
        RegisterEventHandler(
            OnProcessExit(
                target_action=wait_for_gazebo,
                on_exit=[spawn_stadium, spawn_lidar] + drones,
            )
        ),
    ]


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('num_uavs', default_value='1',
                              description='Number of drones to spawn in Gazebo.'),
        OpaqueFunction(function=make_spawn_actions),
    ])
