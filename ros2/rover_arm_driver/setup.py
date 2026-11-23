from setuptools import setup

package_name = "rover_arm_driver"

setup(
    name=package_name,
    version="0.1.0",
    packages=[package_name],
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    description="ROS 2 bridge to the rover_arm Arduino servo firmware",
    license="MIT",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": ["arm_driver = rover_arm_driver.arm_driver:main"],
    },
)
