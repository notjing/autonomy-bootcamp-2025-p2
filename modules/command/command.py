"""
Decision-making logic.
"""

import math

from pymavlink import mavutil

from ..common.modules.logger import logger
from ..telemetry import telemetry


class Position:
    """
    3D vector struct.
    """

    def __init__(self, x: float, y: float, z: float) -> None:
        self.x = x
        self.y = y
        self.z = z


# =================================================================================================
#                            ↓ BOOTCAMPERS MODIFY BELOW THIS COMMENT ↓
# =================================================================================================
class Command:  # pylint: disable=too-many-instance-attributes
    """
    Command class to make a decision based on recieved telemetry,
    and send out commands based upon the data.
    """

    __private_key = object()

    @classmethod
    def create(
        cls,
        connection: mavutil.mavfile,
        target: Position,
        # Put your own arguments here
        local_logger: logger.Logger,
    ) -> object | None:
        """
        Falliable create (instantiation) method to create a Command object.
        """
        try:
            return Command(cls.__private_key, connection, target, local_logger)

        except Exception as e:
            local_logger.error("Failed to create a Command object")

        return None  #  Create a Command object

    def __init__(
        self,
        key: object,
        connection: mavutil.mavfile,
        target: Position,
        # Put your own arguments here
        local_logger: logger.Logger,
    ) -> None:
        assert key is Command.__private_key, "Use create() method"

        # Do any intializiation here
        self.connection = connection
        self.target = target
        self.local_logger = local_logger
        self.velo_log = [[] for i in range(3)]
        self.altitude_error = 0.5
        self.yaw_error = 5

    def run(
        self,
        telemetry_data: telemetry.TelemetryData,
        # Put your own arguments here
    ) -> str:
        """
        Make a decision based on received telemetry data.
        """
        # Log average velocity for this trip so far

        if telemetry_data is not None:
            self.velo_log[0].append(telemetry_data.x_velocity)
            self.velo_log[1].append(telemetry_data.y_velocity)
            self.velo_log[2].append(telemetry_data.z_velocity)

        if self.velo_log[0]:
            self.local_logger.info(
                f"average velocity is {[sum(self.velo_log[0]) / len(self.velo_log[0]), sum(self.velo_log[1]) / len(self.velo_log[1]), sum(self.velo_log[2]) / len(self.velo_log[2]) ]}"
            )

        # Use COMMAND_LONG (76) message, assume the target_system=1 and target_componenet=0
        # The appropriate commands to use are instructed below

        # Adjust height using the comand MAV_CMD_CONDITION_CHANGE_ALT (113)
        # String to return to main: "CHANGE_ALTITUDE: {amount you changed it by, delta height in meters}"
        if abs(self.target.z - telemetry_data.z) > self.altitude_error:
            self.connection.mav.command_long_send(
                target_system=1,
                target_component=0,
                command=mavutil.mavlink.MAV_CMD_CONDITION_CHANGE_ALT,
                confirmation=0,
                param1=1,
                param2=0,
                param3=0,
                param4=0,
                param5=0,
                param6=0,
                param7=self.target.z,
            )

            return f"CHANGE_ALTITUDE: {self.target.z - telemetry_data.z}"

        # Adjust direction (yaw) using MAV_CMD_CONDITION_YAW (115). Must use relative angle to current state
        # String to return to main: "CHANGING_YAW: {degree you changed it by in range [-180, 180]}"
        # Positive angle is counter-clockwise as in a right handed system

        target_yaw = (
            math.atan2((self.target.y - telemetry_data.y), (self.target.x - telemetry_data.x))
            * 180
            / math.pi
        )
        current_yaw = telemetry_data.yaw * 180 / math.pi

        clockwise_turn = abs(target_yaw - current_yaw)
        counter_clockwise_turn = 360 - clockwise_turn
        optimal_dir = 1 if (clockwise_turn > counter_clockwise_turn) else -1

        if abs(target_yaw - current_yaw) > self.yaw_error:
            self.connection.mav.command_long_send(
                target_system=1,
                target_component=0,
                command=mavutil.mavlink.MAV_CMD_CONDITION_YAW,
                confirmation=0,
                param1=target_yaw,
                param2=1,
                param3=optimal_dir,
                param4=0,
                param5=0,
                param6=0,
                param7=0,
            )

            return f"CHANGE YAW: {min(clockwise_turn, counter_clockwise_turn) * -optimal_dir}"


# =================================================================================================
#                            ↑ BOOTCAMPERS MODIFY ABOVE THIS COMMENT ↑
# =================================================================================================
