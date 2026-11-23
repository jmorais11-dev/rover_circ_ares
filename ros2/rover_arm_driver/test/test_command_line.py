import json

from rover_arm_driver.arm_driver import command_line, HOME, step_towards, valid

LO, HI = [0.0] * 6, [180.0] * 6


def test_command_line_sends_all_six_rounded():
    line = command_line([90, 90.4, 90, 145, 0, 180])
    assert line.endswith("\n")
    assert json.loads(line) == {"servo1": 90, "servo2": 90, "servo3": 90,
                                "servo4": 145, "servo5": 0, "servo6": 180}


def test_valid_rejects_bad_input():
    assert valid(HOME, LO, HI)
    assert not valid([90] * 5, LO, HI)
    assert not valid([90] * 7, LO, HI)
    assert not valid([90] * 5 + [181], LO, HI)
    assert not valid([90] * 5 + [-1], LO, HI)
    assert not valid([90] * 5 + [float("nan")], LO, HI)
    assert not valid([90, 10, 90, 145, 90, 90], LO, [180, 9] + HI[2:])  # per-joint limit


def test_step_towards_limits_each_joint_and_lands_exactly():
    cur = [0.1, 90.0]
    assert step_towards(cur, [0.3, 90.0], 0.5) == [0.3, 90.0]  # exact landing, no float drift
    cur = [90.0, 90.0]
    cur = step_towards(cur, [100.0, 89.0], 2.0)
    assert cur == [92.0, 89.0]
    for _ in range(10):
        cur = step_towards(cur, [100.0, 89.0], 2.0)
    assert cur == [100.0, 89.0]
