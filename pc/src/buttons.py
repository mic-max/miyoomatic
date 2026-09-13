"""Button vocabulary and wire protocol shared by every controller backend.

This file and Serial/Serial.ino are the only two places the encoding exists -- keep them
in sync.

Protocol: one byte per action, no framing, no terminator.
    bit 7     1 = press (drive HIGH), 0 = release (drive LOW)
    bits 0-3  solenoid index, 0..7
    bits 4-6  unused, must be 0

    0x80 -> solenoid 0 down      0x00 -> solenoid 0 up
    0x87 -> solenoid 7 down      0x07 -> solenoid 7 up

The Arduino owns no timing: a tap is a press byte and a release byte with whatever gap the
PC chooses, a hold is the same two bytes further apart, a chord is several presses before
any release.
"""

# Button id == solenoid index == Arduino pin - 2. All three have to move together; the pin
# side of that is the solenoids[] array in Serial/Serial.ino.
UP, DOWN, LEFT, RIGHT, A, B, START, SELECT = range(8)

NAMES = {
    UP: "Up",
    DOWN: "Down",
    LEFT: "Left",
    RIGHT: "Right",
    A: "A",
    B: "B",
    START: "Start",
    SELECT: "Select",
}

ALL = tuple(NAMES)

PRESS_BIT = 0x80

# Must match Serial.begin() in Serial/Serial.ino.
BAUD = 115200

# Was SolenoidActiveMs in the old sketch, where it was the only possible press length.
# Now it is just the default; every tap can ask for its own duration.
DEFAULT_TAP_MS = 40

# Step kinds for the queue format the backend worker threads consume. A queue item is a
# list of steps executed in order; a step is either (PRESS, button), (RELEASE, button), or
# a float meaning "sleep this many seconds".
PRESS = "press"
RELEASE = "release"


def press_byte(button: int) -> bytes:
    return bytes([PRESS_BIT | button])


def release_byte(button: int) -> bytes:
    return bytes([button])


def name(button: int) -> str:
    return NAMES.get(button, f"<unknown button {button}>")


def describe(raw: int) -> str:
    """Render a byte seen on the wire, for logging echoes."""
    action = "press" if raw & PRESS_BIT else "release"
    return f"{action} {name(raw & 0x0F)}"
