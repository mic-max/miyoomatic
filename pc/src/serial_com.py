import logging
import time

import serial

import buttons

logger = logging.getLogger(__name__)


def listener(ser, q):
    logger.info(f"Listener on {ser.port}...")
    while True:
        try:
            # The Arduino echoes a single raw byte with no terminator, so readline() would
            # block for the full port timeout on every action.
            data = ser.read(1)
            if not data:
                continue  # read timeout, not EOF
            q.put(data[0])
        except serial.SerialException as e:
            logger.error(f"Serial read error: {e}")
            break


def writer(ser, q, lock):
    logger.info(f"Writer on {ser.port}...")
    while True:
        try:
            steps = q.get()  # blocking until item available
            for step in steps:
                if isinstance(step, (int, float)) and not isinstance(step, bool):
                    time.sleep(step)  # outside the lock; nothing to serialise here
                    continue
                action, button = step
                data = (
                    buttons.press_byte(button)
                    if action == buttons.PRESS
                    else buttons.release_byte(button)
                )
                with lock:
                    ser.write(data)
                    ser.flush()
                logger.debug(f"Sent {data.hex()} ({buttons.describe(data[0])})")
        except serial.SerialException as e:
            logger.error(f"Serial write error: {e}")
            break
        except Exception as e:
            logger.error(f"Unexpected writer error: {e}")
            break
