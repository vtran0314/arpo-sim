import os
from launch import LaunchDescription
from launch.actions import ExecuteProcess, RegisterEventHandler
from launch.event_handlers import OnProcessStart, OnProcessExit
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    pkg_arpo_gazebo = get_package_share_directory('arpo_gazebo')
    pkg_arpo_description = get_package_share_directory('arpo_description')

    world_sdf = os.path.join(pkg_arpo_gazebo, 'worlds', 'arpo_world.sdf')
    models_dir = os.path.join(pkg_arpo_description, 'models')

    gz_sim = ExecuteProcess(
        cmd=['gz', 'sim', world_sdf],
        output='screen',
    )

    # Poll until the world service is available before spawning models.
    # Mirrors the until-loop in the old start-gazebo.sh.
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

    spawn_drone = ExecuteProcess(
        cmd=['gz', 'service', '-s', '/world/arpo/create',
             '--reqtype', 'gz.msgs.EntityFactory',
             '--reptype', 'gz.msgs.Boolean',
             '--req', f'sdf_filename: "{models_dir}/iris_drone/model.sdf"',
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

    return LaunchDescription([
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
                on_exit=[spawn_stadium, spawn_drone, spawn_lidar],
            )
        ),
    ])
