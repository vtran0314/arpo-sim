from setuptools import setup
import os
from glob import glob

package_name = 'arpo_gz_bridge'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.py')),
        (os.path.join('share', package_name, 'config'), glob('config/*.yml')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Vinh Tran',
    description='Bridges FastSwarmSim drone poses into Gazebo.',
    entry_points={
        'console_scripts': [
            'pose_bridge = arpo_gz_bridge.pose_bridge_node:main',
        ],
    },
)
