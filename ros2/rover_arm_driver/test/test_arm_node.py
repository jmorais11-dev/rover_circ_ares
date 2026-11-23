"""Safety behaviour of the node against a fake Arduino (a pty), without spinning."""

import json
import os
import pty
import select

import pytest
import rclpy
from std_msgs.msg import Bool, Float64MultiArray

from rover_arm_driver.arm_driver import ArmDriver, HOME


def cmd(base):
    return Float64MultiArray(data=[base, 90.0, 90.0, 145.0, 90.0, 90.0])


def sent_bases(master):
    out = b""
    while select.select([master], [], [], 0.1)[0]:
        out += os.read(master, 65536)
    return [json.loads(line)["servo1"] for line in out.decode().splitlines()]


@pytest.fixture
def arm():
    master, slave = pty.openpty()
    # 50 deg/s at 25 Hz = 2 deg per tick
    rclpy.init(
        args=["--ros-args", "-p", f"port:={os.ttyname(slave)}", "-p", "max_speed:=50.0"]
    )
    node = ArmDriver()
    yield node, master
    node.ser.close()
    node.destroy_node()
    rclpy.shutdown()
    os.close(master)
    os.close(slave)


def test_estop_freezes_mid_ramp_does_not_resume_and_park_returns_home(arm):
    node, master = arm
    node.on_command(cmd(150.0))
    for _ in range(5):
        node.tick()
    assert node.current[0] == 100.0

    node.on_estop(Bool(data=True))
    node.on_command(cmd(20.0))  # ignored while estop
    node.tick()
    assert node.current[0] == 100.0

    node.on_estop(Bool(data=False))
    node.tick()
    assert node.current[0] == 100.0  # releasing estop does not resume the old ramp

    node.park()
    assert node.current == HOME
    bases = sent_bases(master)
    assert bases[-1] == 90
    assert max(abs(a - b) for a, b in zip(bases, bases[1:])) <= 2


def test_park_does_not_move_while_estop(arm):
    node, master = arm
    node.on_command(cmd(100.0))
    for _ in range(5):
        node.tick()
    node.on_estop(Bool(data=True))
    sent_bases(master)
    node.park()
    assert node.current[0] == 100.0
    assert sent_bases(master) == []
