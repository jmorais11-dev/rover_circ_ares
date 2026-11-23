# ros2/

The ROS 2 Jazzy workspace sources: every colcon package that runs the rover,
in simulation or on the real hardware, plus the systemd service that starts
the real rover at boot.

The whole repository is mounted as `~/ros2_ws/src` inside the Docker image
(see the main [README](../README.md#essential-commands)), so `colcon build`
finds these packages from there. Folders outside `ros2/` (`tools/`, `docs/`)
are not built.

## Packages

| Package | Role | Used in |
|---|---|---|
| [`rover_bringup`](rover_bringup/) | Entry-point launch files: real rover, simulation + rosbridge, sensor drivers (Hokuyo, u-blox) | sim, real |
| [`rover_description`](rover_description/) | URDF/xacro of the rocker-bogie (Sawppy style), sensors (2D lidar, RGBD camera, IMU) and `ros2_control` config | sim, real (model only) |
| [`rover_gazebo`](rover_gazebo/) | Gazebo Harmonic worlds (moon, mars, forest...), ROS-Gazebo bridge, wheel odometry and the `MotorsCommand` → joint controller parser | sim |
| [`rover_localization`](rover_localization/) | rtabmap RGBD odometry + EKF (`robot_localization`) fusing it with the IMU | sim |
| [`rover_slam`](rover_slam/) | slam_toolbox mapping, AMCL on a saved map, frontier exploration params | sim |
| [`rover_navigation`](rover_navigation/) | Nav2 params (planner/controller selectable), costmaps for uneven terrain, behavior tree | sim |
| [`rover_motor_controller_cpp`](rover_motor_controller_cpp/) | `vel_parser_node` (`/cmd_vel` → rocker-bogie wheel speeds and steering) and `controller_node` (LX-16A servo driver) | sim (`vel_parser` only), real |
| [`rover_motor_controller`](rover_motor_controller/) | Python version of the same two nodes. Not used by any launch file. | — |
| [`rover_teleop`](rover_teleop/) | PS3 joystick config (`teleop_twist_joy`) and a keyboard teleop node | sim, real |
| [`rover_msgs`](rover_msgs/) | `MotorsCommand` (drive duty ×6, steering ticks ×4) | sim, real |
| [`explore_lite`](explore_lite/), [`explore_lite_msgs`](explore_lite_msgs/) | Vendored frontier exploration (ROS 2 port) | sim |
| [`rover_service`](rover_service/) | Not a colcon package: `rover.service` + `install.sh` to start the real rover with systemd | real |

## How the pieces connect

```text
/cmd_vel ──► vel_parser_node ──► /motors_command (rover_msgs/MotorsCommand)
  ▲                                   │
  │                                   ├──► motors_command_parser_node ──► Gazebo (ros2_control)   [sim]
  │                                   └──► controller_node ──► LX-16A servos on /dev/ttyUSB0      [real]
  │
  ├── teleop (joystick / keyboard)
  └── Nav2 (planner + controller + BT) ◄── /map (slam_toolbox or AMCL) ◄── EKF ◄── RGBD odometry + IMU
```

The same `vel_parser_node` feeds both the simulation and the real servos, so
the kinematics tested in Gazebo are the ones that run on the rover.

## Entry points

| Command | What it starts |
|---|---|
| `ros2 launch rover_bringup rover_mcp_sim.launch.py` | Full simulation (Gazebo, localization, SLAM/AMCL, Nav2, optional exploration) + rosbridge on port 9090. Arguments are in the main [README](../README.md#3-run-the-simulation). |
| `ros2 launch rover_gazebo gazebo.launch.py` | Same simulation stack without rosbridge. `nav2_planner` (default `SmacHybrid`) and `nav2_controller` (default `RPP`) pick the files in `rover_navigation/params/`. |
| `ros2 launch rover_gazebo moon.launch.py` (or `mars`, `forest`...) | Simulation in a given world. Navigation is tuned and tested on the moon world. |
| `ros2 launch rover_bringup rover.launch.py` | **Real rover:** Hokuyo driver, joystick teleop and the LX-16A motor controller. |
| `ros2 launch rover_bringup ublox.launch.py` | u-blox GNSS driver. Not included in `rover.launch.py`. |

## Build and test

Inside the container (`docker exec -it rover_mcp bash`):

```bash
cd ~/ros2_ws
colcon build --symlink-install                                   # everything
colcon build --symlink-install --packages-select rover_gazebo    # one package
colcon test --packages-select rover_teleop && colcon test-result --verbose
```

CI builds the whole workspace from a clean checkout on every change under
`ros2/` (`.github/workflows/docker-build.yml`). The tests here are lint checks
only (flake8, pep257, clang-format).

## Real rover: read before powering the motors

The real-rover path is **not ready for unattended use**. The
[readiness audit](https://jmorais11-dev.github.io/rover_circ_ares/auditoria-prontidao/)
lists the gaps; the most important ones live in this folder:

- `controller_node` has no command timeout and does not stop the motors on
  exit: the last command keeps running.
- `vel_parser_node` does not clamp negative speeds or the final duty (±1000).
- `rover_bringup/config/urg_node_serial.yaml` and `ublox.yaml` both use
  `/dev/ttyACM0`; there are no udev rules.
- `rover_service/rover.service` expects ROS installed on the host, not Docker.

Until those are fixed: test with the **wheels lifted** and someone on the
**physical kill switch**. Open questions about the hardware are in issue
[#32](https://github.com/jmorais11-dev/rover_circ_ares/issues/32).

## Adding a package

1. Create it here (`ros2 pkg create --build-type ament_cmake <name>` from inside `ros2/`).
2. Declare every dependency in `package.xml`: the Docker image installs them with `rosdep`, so a missing one breaks the CI build.
3. Add a row to the table above and, if it changes how the rover is launched, update the main README.
