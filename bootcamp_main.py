"""
Bootcamp F2025

Main process to setup and manage all the other working processes
"""

import multiprocessing as mp
import queue
import time

from pymavlink import mavutil

from modules.common.modules.logger import logger
from modules.common.modules.logger import logger_main_setup
from modules.common.modules.read_yaml import read_yaml
from modules.command import command
from modules.command import command_worker
from modules.heartbeat import heartbeat_receiver_worker
from modules.heartbeat import heartbeat_sender_worker
from modules.telemetry import telemetry_worker
from utilities.workers import queue_proxy_wrapper
from utilities.workers import worker_controller
from utilities.workers import worker_manager


# MAVLink connection
CONNECTION_STRING = "tcp:localhost:12345"

# =================================================================================================
#                            ↓ BOOTCAMPERS MODIFY BELOW THIS COMMENT ↓
# =================================================================================================
# Set queue max sizes (<= 0 for infinity)
HEARTBEAT_QUEUE_SIZE = 5
TELEMETRY_QUEUE_SIZE = 5
COMMAND_QUEUE_SIZE = 5
# Set worker counts

HEARTBEAT_RECEIVER_COUNT = 1
HEARTBEAT_SENDER_COUNT = 1
TELEMETRY_COUNT = 1
COMMAND_COUNT = 1

# Any other constants

# =================================================================================================
#                            ↑ BOOTCAMPERS MODIFY ABOVE THIS COMMENT ↑
# =================================================================================================


def main() -> int:
    """
    Main function.
    """
    # Configuration settings
    result, config = read_yaml.open_config(logger.CONFIG_FILE_PATH)
    if not result:
        print("ERROR: Failed to load configuration file")
        return -1

    # Get Pylance to stop complaining
    assert config is not None

    # Setup main logger
    result, main_logger, _ = logger_main_setup.setup_main_logger(config)
    if not result:
        print("ERROR: Failed to create main logger")
        return -1

    # Get Pylance to stop complaining
    assert main_logger is not None

    # Create a connection to the drone. Assume that this is safe to pass around to all processes
    # In reality, this will not work, but to simplify the bootcamp, pretend it is allowed
    # To test, you will run each of your workers individually to see if they work
    # (test "drones" are provided for you test your workers)
    # NOTE: If you want to have type annotations for the connection, it is of type mavutil.mavfile
    connection = mavutil.mavlink_connection(CONNECTION_STRING)
    connection.wait_heartbeat(timeout=30)  # Wait for the "drone" to connect

    # =============================================================================================
    #                          ↓ BOOTCAMPERS MODIFY BELOW THIS COMMENT ↓
    # =============================================================================================
    # Create a worker controller

    controller = worker_controller.WorkerController()

    # Create a multiprocess manager for synchronized queues

    mp_manager = mp.Manager()

    # Create queues
    heartbeat_output_queue = queue_proxy_wrapper.QueueProxyWrapper(mp_manager)
    telemetry_output_queue = queue_proxy_wrapper.QueueProxyWrapper(mp_manager)
    command_output_queue = queue_proxy_wrapper.QueueProxyWrapper(mp_manager)

    # Create worker properties for each worker type (what inputs it takes, how many workers)
    # Heartbeat sender

    heartbeat_sender_properties = worker_manager.WorkerProperties.create(
        count=HEARTBEAT_SENDER_COUNT,
        target=heartbeat_sender_worker,
        work_arguments=(connection,),
        input_queues=[],
        output_queues=[],
        controller=controller,
        local_logger=main_logger,
    )

    # Heartbeat receiver

    heartbeat_receiver_properties = worker_manager.WorkerProperties.create(
        count=HEARTBEAT_RECEIVER_COUNT,
        target=heartbeat_receiver_worker,
        work_arguments=(connection,),
        input_queues=[],
        output_queues=[heartbeat_output_queue],
        controller=controller,
        local_logger=main_logger,
    )

    # Telemetry

    telemetry_properties = worker_manager.WorkerProperties.create(
        count=TELEMETRY_COUNT,
        target=telemetry_worker,
        work_arguments=(connection,),
        input_queues=[],
        output_queues=[telemetry_output_queue],
        controller=controller,
        local_logger=main_logger,
    )

    # Command
    target_pos = command.Position(x=1, y=1, z=1)

    command_properties = worker_manager.WorkerProperties.create(
        count=COMMAND_COUNT,
        target=command_worker,
        work_arguments=(connection, target_pos),
        input_queues=[telemetry_output_queue],
        output_queues=[command_output_queue],
        controller=controller,
        local_logger=main_logger,
    )

    # Create the workers (processes) and obtain their managers

    managers = []

    heartbeat_receiver_manager = worker_manager.WorkerManager.create(
        heartbeat_receiver_properties, main_logger
    )

    heartbeat_sender_manager = worker_manager.WorkerManager.create(
        heartbeat_sender_properties, main_logger
    )

    telemetry_manager = worker_manager.WorkerManager.create(telemetry_properties, main_logger)

    command_manager = worker_manager.WorkerManager.create(command_properties, main_logger)

    managers.append(heartbeat_sender_manager)
    managers.append(heartbeat_receiver_manager)
    managers.append(telemetry_manager)
    managers.append(command_manager)

    # Start worker processes

    for manager in managers:
        manager.start_workers()

    main_logger.info("Started")

    # Main's work: read from all queues that output to main, and log any commands that we make
    # Continue running for 100 seconds or until the drone disconnects

    initial_time = time.time()

    while time.time() - initial_time <= 100:

        if not connection.target_system:
            break

        try:
            hb = heartbeat_output_queue.queue.get_nowait()
            main_logger.info(f"heartbeat received {hb}")
        except queue.Empty:
            pass

        try:
            tele_data = telemetry_output_queue.queue.get_nowait()
            main_logger.info(f"telemetry data received {tele_data}")
        except queue.Empty:
            pass

        try:
            cmd_data = command_output_queue.queue.get_nowait()
            main_logger.info(f"command data received {cmd_data}")
        except queue.Empty:
            pass

    # Stop the processes

    main_logger.info("Requested exit")

    controller.request_exit()

    # Fill and drain queues from END TO START

    main_logger.info("Queues cleared")

    heartbeat_output_queue.fill_and_drain_queue()
    telemetry_output_queue.fill_and_drain_queue()
    command_output_queue.fill_and_drain_queue()

    # Clean up worker processes

    for manager in managers:
        manager.join_workers()

    main_logger.info("Stopped")

    # We can reset controller in case we want to reuse it
    # Alternatively, create a new WorkerController instance
    controller = worker_controller.WorkerController()

    # =============================================================================================
    #                          ↑ BOOTCAMPERS MODIFY ABOVE THIS COMMENT ↑
    # =============================================================================================

    return 0


if __name__ == "__main__":
    result_main = main()
    if result_main < 0:
        print(f"Failed with return code {result_main}")
    else:
        print("Success!")
