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
    ) -> tuple[bool, "Command"] | tuple[bool, None]:
        """
        Falliable create (instantiation) method to create a Command object.
        """
        try:
            return True, Command(cls.__private_key, connection, target, local_logger)

        except (TypeError, ValueError) as e:
            local_logger.error(f"Failed to create a Command object: {e}")

        return False, None  #  Create a Command object

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

        target_yaw = math.atan2(self.target.y - telemetry_data.y, self.target.x - telemetry_data.x)
        current_yaw = telemetry_data.yaw;

        yaw_diff = target_yaw - current_yaw

        if yaw_diff > math.pi:
            yaw_diff = -1 * ((2 * math.pi) - yaw_diff)
        elif yaw_diff < -1 * math.pi:
            yaw_diff = -1 * ((-2 * math.pi) - yaw_diff)
        yaw_diff_deg = math.degrees(yaw_diff)

        if yaw_diff_deg > 180:
            yaw_diff_deg -= 360
        elif yaw_diff_deg < -180:
            yaw_diff_deg += 360

        optimal_dir = -1 if yaw_diff_deg > 0 else 1

        if abs(yaw_diff_deg) > self.yaw_error:
            self.connection.mav.command_long_send(
                target_system=1,
                target_component=0,
                command=mavutil.mavlink.MAV_CMD_CONDITION_YAW,
                confirmation=0,
                param1=yaw_diff_deg,
                param2=5,
                param3=optimal_dir,
                param4=1,
                param5=0,
                param6=0,
                param7=0,
            )

            return f"CHANGE YAW: {yaw_diff_deg}"

        return None
# =================================================================================================
#                            ↑ BOOTCAMPERS MODIFY ABOVE THIS COMMENT ↑
# =================================================================================================
