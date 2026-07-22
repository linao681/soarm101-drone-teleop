#!/usr/bin/env python3
"""Arm the XIAO controller without commanding a position jump."""

import time

import rclpy
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy
from sensor_msgs.msg import JointState


class ArmAtCurrentPose(Node):
    def __init__(self):
        super().__init__("soarm_arm_at_current_pose")
        qos = QoSProfile(
            history=HistoryPolicy.KEEP_LAST,
            depth=1,
            reliability=ReliabilityPolicy.BEST_EFFORT,
            durability=DurabilityPolicy.VOLATILE,
        )
        self.latest = None
        self.create_subscription(JointState, "/joint_states", self._on_state, qos)
        self.publisher = self.create_publisher(JointState, "/joint_command", qos)

    def _on_state(self, message):
        if len(message.name) == 6 and len(message.position) == 6:
            self.latest = message


def main():
    rclpy.init()
    node = ArmAtCurrentPose()
    deadline = time.monotonic() + 10.0
    while node.latest is None and time.monotonic() < deadline:
        rclpy.spin_once(node, timeout_sec=0.1)

    if node.latest is None:
        node.destroy_node()
        rclpy.shutdown()
        raise RuntimeError("No /joint_states received within 10 seconds")

    command = JointState()
    command.name = list(node.latest.name)
    command.position = list(node.latest.position)
    print(f"Arming at measured pose: {command.position}")

    # Allow DDS discovery for the newly created publisher, then repeat the
    # identical pose to tolerate best-effort packet loss.
    time.sleep(1.0)
    for _ in range(5):
        command.header.stamp = node.get_clock().now().to_msg()
        node.publisher.publish(command)
        rclpy.spin_once(node, timeout_sec=0.1)
        time.sleep(0.1)

    print("Arm handshake sent. Verify the serial log contains 'ARMED'.")
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
