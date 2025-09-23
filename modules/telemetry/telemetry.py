"""
Telemetry gathering logic.
"""

import time

from pymavlink import mavutil

from ..common.modules.logger import logger


class TelemetryData:  # pylint: disable=too-many-instance-attributes
    """
    Python struct to represent Telemtry Data. Contains the most recent attitude and position reading.
    """

    def __init__(
        self,
        time_since_boot: int | None = None,  # ms
        x: float | None = None,  # m
        y: float | None = None,  # m
        z: float | None = None,  # m
        x_velocity: float | None = None,  # m/s
        y_velocity: float | None = None,  # m/s
        z_velocity: float | None = None,  # m/s
        roll: float | None = None,  # rad
        pitch: float | None = None,  # rad
        yaw: float | None = None,  # rad
        roll_speed: float | None = None,  # rad/s
        pitch_speed: float | None = None,  # rad/s
        yaw_speed: float | None = None,  # rad/s
    ) -> None:
        self.time_since_boot = time_since_boot
        self.x = x
        self.y = y
        self.z = z
        self.x_velocity = x_velocity
        self.y_velocity = y_velocity
        self.z_velocity = z_velocity
        self.roll = roll
        self.pitch = pitch
        self.yaw = yaw
        self.roll_speed = roll_speed
        self.pitch_speed = pitch_speed
        self.yaw_speed = yaw_speed

    def __str__(self) -> str:
        return f"""{{
            time_since_boot: {self.time_since_boot},
            x: {self.x},
            y: {self.y},
            z: {self.z},
            x_velocity: {self.x_velocity},
            y_velocity: {self.y_velocity},
            z_velocity: {self.z_velocity},
            roll: {self.roll},
            pitch: {self.pitch},
            yaw: {self.yaw},
            roll_speed: {self.roll_speed},
            pitch_speed: {self.pitch_speed},
            yaw_speed: {self.yaw_speed}
        }}"""


# =================================================================================================
#                            ↓ BOOTCAMPERS MODIFY BELOW THIS COMMENT ↓
# =================================================================================================
class Telemetry:
    """
    Telemetry class to read position and attitude (orientation).
    """

    __private_key = object()

    @classmethod
    def create(
        cls,
        connection: mavutil.mavfile,
        # Put your own arguments here
        local_logger: logger.Logger,
    ) -> object | None:
        """
        Falliable create (instantiation) method to create a Telemetry object.
        """

        try:
            Telemetry(cls.__private_key, connection, local_logger)
            local_logger.info("Telemetry object created")

        except ValueError as e:
            local_logger.error(f"Failed to create Telemetry object: {e}")

        # Create a Telemetry object

    def __init__(
        self,
        key: object,
        connection: mavutil.mavfile,
        # Put your own arguments here
        local_logger: logger.Logger,
    ) -> None:
        assert key is Telemetry.__private_key, "Use create() method"

        # Do any intializiation here

        self.connection = connection
        self.local_logger = local_logger

    def run(
        self,
        # Put your own arguments here
    ) -> TelemetryData | None:
        """
        Receive LOCAL_POSITION_NED and ATTITUDE messages from the drone,
        combining them together to form a single TelemetryData object.
        """
        # Read MAVLink message LOCAL_POSITION_NED (32)
        # Read MAVLink message ATTITUDE (30)
        # Return the most recent of both, and use the most recent message's timestamp

        initial_time = time.time()
        pos_ned = None
        attitude = None

        while time.time() - initial_time < 1:
            if pos_ned is None:
                pos_ned = self.connection.recv_match(
                    type="LOCAL_POSITION_NED", blocking=False, timeout=0.05
                )
                if pos_ned is not None:
                    self.local_logger.info("LOCAL_POSITION_NED info received")

            if attitude is None:
                attitude = self.connection.recv_match(type="ATTITUDE", blocking=False, timeout=0.05)
                if pos_ned is not None:
                    self.local_logger.info("ATTITUDE info received")

        if pos_ned is not None and attitude is not None:
            telemetry_data = TelemetryData(
                time_since_boot=max(pos_ned.time_boot_ms, attitude.time_boot_ms),
                x=pos_ned.x,
                y=pos_ned.y,
                z=pos_ned.z,
                x_velocity=pos_ned.vx,
                y_velocity=pos_ned.vy,
                z_velocity=pos_ned.vz,
                roll=attitude.roll,
                pitch=attitude.pitch,
                yaw=attitude.yaw,
                roll_speed=attitude.rollspeed,
                pitch_speed=attitude.pitchspeed,
                yaw_speed=attitude.yawspeed,
            )
            self.local_logger.info("telemetry data created")
            return telemetry_data

        self.local_logger.warning("no telemetry data received")
        return None


# =================================================================================================
#                            ↑ BOOTCAMPERS MODIFY ABOVE THIS COMMENT ↑
# =================================================================================================
