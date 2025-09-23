"""
Heartbeat receiving logic.
"""

from pymavlink import mavutil

from ..common.modules.logger import logger


# =================================================================================================
#                            ↓ BOOTCAMPERS MODIFY BELOW THIS COMMENT ↓
# =================================================================================================
class HeartbeatReceiver:
    """
    HeartbeatReceiver class to send a heartbeat
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
        Falliable create (instantiation) method to create a HeartbeatReceiver object.
        """

        try:
            return cls(cls.__private_key, connection, local_logger)
        except (TypeError, ValueError) as e:
            local_logger.error(f"Failed to create heartbeat reciever: {e}")
            return None

        # Create a HeartbeatReceiver object

    def __init__(
        self,
        key: object,
        connection: mavutil.mavfile,
        # Put your own arguments here
        local_logger: logger.Logger,
    ) -> None:
        assert key is HeartbeatReceiver.__private_key, "Use create() method"

        # Do any intializiation here
        self.connection = connection
        self.status = "Disconnected"
        self.missed = 0
        self.local_logger = local_logger

    def run(
        self,
        # Put your own arguments here
    ) -> str:
        """
        Attempt to recieve a heartbeat message.
        If disconnected for over a threshold number of periods,
        the connection is considered disconnected.
        """

        msg = self.connection.recv_match(type="HEARTBEAT", blocking=False)

        try:
            if msg is None:
                self.missed += 1
                if self.missed >= 5:
                    self.status = "Disconnected"
                    self.local_logger.warning("The drone has been disconnected.")
                else:
                    self.local_logger.warning(f"{self.missed} heartbeats missed.")

            else:
                self.missed = 0
                if self.status == "Disconnected":
                    self.status = "Connected"
                    self.local_logger.info("The drone is connected.")

        except ConnectionError as e:
            self.local_logger.error(f"There was a problem recieving the hearbeat: {e}")

        return self.status


# =================================================================================================
#                            ↑ BOOTCAMPERS MODIFY ABOVE THIS COMMENT ↑
# =================================================================================================
