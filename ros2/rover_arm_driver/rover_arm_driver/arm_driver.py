"""Bridge /arm/command to the rover_arm Arduino firmware (rover_arm/Arduino/src/main.cpp).

Topic arm/command (std_msgs/Float64MultiArray): 6 servo angles in degrees, in firmware order:
base, shoulder, elbow, gripper roll (145 = centred), wrist, gripper (0 closed, 180 open).
The firmware jumps straight to whatever it receives, so this node ramps towards the
target at max_speed deg/s. /estop true freezes the arm where it is; on exit it parks at HOME.
"""

import json
import math
import time

import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
import serial
from std_msgs.msg import Bool, Float64MultiArray

NAMES = ["servo1", "servo2", "servo3", "servo4", "servo5", "servo6"]
# firmware power-on pose; the UNO resets to it on port open
HOME = [90.0, 90.0, 90.0, 145.0, 90.0, 90.0]
# Hz; a ~75-byte line every 40 ms fits 115200 baud and the UNO's 64-byte RX buffer
RATE = 25.0


def valid(angles, lo, hi):
    """True if there are 6 finite angles, each within its joint limits."""
    return len(angles) == len(NAMES) and all(
        math.isfinite(a) and low <= a <= high for a, low, high in zip(angles, lo, hi)
    )


def step_towards(current, target, max_step):
    """Move each joint at most max_step degrees towards its target."""
    # land on t exactly (c + (t - c) can miss by an ulp and park() would never end)
    return [
        t if abs(t - c) <= max_step else c + math.copysign(max_step, t - c)
        for c, t in zip(current, target)
    ]


def command_line(angles):
    """Firmware JSON line; always all six keys, the firmware drives a missing key to 0 deg."""
    return (
        json.dumps({n: round(a) for n, a in zip(NAMES, angles)}, separators=(",", ":"))
        + "\n"
    )


class ArmDriver(Node):

    def __init__(self):
        super().__init__("arm_driver")
        port = self.declare_parameter("port", "/dev/robotarm").value
        baud = self.declare_parameter("baudrate", 115200).value
        self.max_step = self.declare_parameter("max_speed", 30.0).value / RATE
        self.lo = list(self.declare_parameter("min_angles", [0.0] * 6).value)
        self.hi = list(self.declare_parameter("max_angles", [180.0] * 6).value)
        if not (self.max_step > 0 and valid(HOME, self.lo, self.hi)):
            raise ValueError(
                f"need max_speed > 0 and 6 min/max angles containing HOME {HOME}"
            )
        self.ser = serial.Serial(port, baud, timeout=1)
        # opening the port resets the UNO; its bootloader drops bytes meanwhile
        time.sleep(2.0)
        self.current = list(HOME)
        self.target = list(HOME)
        self.last_line = command_line(HOME)
        self.estop = False
        self.create_subscription(Bool, "estop", self.on_estop, 10)
        self.create_subscription(Float64MultiArray, "arm/command", self.on_command, 10)
        self.create_timer(1.0 / RATE, self.tick)
        self.get_logger().info(
            f"arm on {port} @ {baud}, max {self.max_step * RATE} deg/s"
        )

    def on_estop(self, msg):
        self.estop = msg.data
        if self.estop:
            # stop mid-ramp; releasing estop must not resume it
            self.target = list(self.current)

    def on_command(self, msg):
        angles = list(msg.data)
        if self.estop:
            self.get_logger().warn(
                "estop active: arm command ignored", throttle_duration_sec=2.0
            )
        elif not valid(angles, self.lo, self.hi):
            self.get_logger().warn(
                f"rejected arm command {angles}: need 6 angles in {self.lo}..{self.hi}"
            )
        else:
            self.target = angles

    def tick(self):
        if not self.estop and self.current != self.target:
            self.send(step_towards(self.current, self.target, self.max_step))

    def send(self, angles):
        self.current = angles
        line = command_line(angles)
        if line != self.last_line:
            self.last_line = line
            self.ser.reset_input_buffer()  # firmware echoes every line; we don't need it
            self.ser.write(line.encode())

    def park(self):
        """Ramp back to HOME so the next start (UNO reset to HOME) does not jerk."""
        if self.estop:
            return
        while self.current != HOME:
            self.send(step_towards(self.current, HOME, self.max_step))
            time.sleep(1.0 / RATE)


def main():
    rclpy.init()
    node = ArmDriver()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.park()
        node.ser.close()
        node.destroy_node()
        rclpy.try_shutdown()
