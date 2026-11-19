from setuptools import setup
import os
from glob import glob

package_name = 'arpo_mission'

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
    description='Automate controlling drone',
    entry_points={
        'console_scripts': [
            #syntax is: <executable_name> = <package>.<module>:<function>
            'waypoint_node = arpo_mission.waypoint_node:main',
        ],
    },
)

