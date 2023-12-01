from geometry_msgs.msg import Pose, Point
from control_msgs.action import GripperCommand
import control_msgs.msg as control_msg
from moveit_wrapper.moveitapi import MoveItApi, ErrorCodes
from franka_msgs.action import Grasp
from rclpy.action import ActionClient
from typing import List
import numpy as np
from rclpy.callback_groups import ReentrantCallbackGroup
from tf2_ros import TransformListener, Buffer, TransformBroadcaster
from rclpy.time import Time


class GraspPlan:
    def __init__(self,
                 approach_pose: Pose,
                 grasp_pose: Pose,
                 grasp_command: Grasp.Goal,
                 retreat_pose: Pose):
        self.approach_pose = approach_pose
        self.grasp_pose = grasp_pose
        self.grasp_command = grasp_command
        self.retreat_pose = retreat_pose


class GraspPlanner:
    """
    Plans and executes a grasp action
    """

    def __init__(self,
                 moveit_api: MoveItApi,
                 gripper_action_name: str):
        self.moveit_api = moveit_api
        self.node = self.moveit_api.node

        self.grasp_client = ActionClient(
            self.node,
            Grasp,
            gripper_action_name,
            callback_group=ReentrantCallbackGroup(),
        )

        # Create tf listener
        self.buffer = Buffer()
        self.tf_listener = TransformListener(self.buffer, self.node)
        self.tf_parent_frame = "panda_link0"


    async def execute_grasp_plan(self, grasp_plan: GraspPlan):

        self.node.get_logger().warn("going to approach point!")
        curr_poseStamped = await self.moveit_api.get_end_effector_pose()
        curr_pose = curr_poseStamped.pose

        plan_result = await self.moveit_api.plan_async(
            point=grasp_plan.approach_pose.position,
            orientation=grasp_plan.approach_pose.orientation,
            execute=True
        )

        self.node.get_logger().warn(f"succeeded in going to approach point")

        self.node.get_logger().warn("going to grasp point!")
        self.node.get_logger().warn(
            f"grasp pose: {grasp_plan.grasp_pose.orientation}")
        plan_result = await self.moveit_api.plan_async(
            point=grasp_plan.grasp_pose.position,
            orientation=grasp_plan.grasp_pose.orientation,
            execute=True
        )

        self.node.get_logger().warn("grasping...")
        goal_handle = await self.grasp_client.send_goal_async(grasp_plan.grasp_command)
        grasp_command_result = await goal_handle.get_result_async()
        self.node.get_logger().warn("finished grasp")

        actual_grasp_position = self.buffer.lookup_transform(
            "panda_link0", "panda_hand_tcp", Time())

        plan_result = await self.moveit_api.plan_async(
            point=grasp_plan.retreat_pose.position,
            orientation=grasp_plan.retreat_pose.orientation,
            execute=True
        )

        return actual_grasp_position
