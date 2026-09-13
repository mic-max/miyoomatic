import abc
import logging
import queue
import threading
import time
from dataclasses import dataclass
from typing import Any

import cv2
import serial as pyserial

import buttons
import computer_vision
import emulator
import serial_com

logger = logging.getLogger(__name__)


@dataclass
class Capture:
    raw: Any
    imgray: Any
    main_screen_rect: Any
    dialog_rect: Any
    nametag_rect: Any


class Controller(abc.ABC):
    incoming: queue.Queue
    outgoing: queue.Queue

    @abc.abstractmethod
    def start(self) -> None: ...

    @abc.abstractmethod
    def capture(self) -> Capture | None: ...

    @abc.abstractmethod
    def close(self) -> None: ...

    # Button API. Duration lives here rather than in the firmware, so a tap and a hold are
    # the same two events with a different gap between them. Each call enqueues the whole
    # sequence as one item, so concurrent callers can never interleave one button's press
    # with another's release.

    def tap(self, button: int, ms: int = buttons.DEFAULT_TAP_MS) -> None:
        self.outgoing.put(
            [(buttons.PRESS, button), ms / 1000, (buttons.RELEASE, button)]
        )

    def hold(self, button: int) -> None:
        self.outgoing.put([(buttons.PRESS, button)])

    def release(self, button: int) -> None:
        self.outgoing.put([(buttons.RELEASE, button)])

    def release_all(self) -> None:
        self.outgoing.put([(buttons.RELEASE, b) for b in buttons.ALL])

    def _drain(self, timeout: float = 2.0) -> None:
        """Wait for the worker thread to consume what's queued, then for it to finish the
        last item. Best-effort: bounded so shutdown can't hang on a dead worker."""
        deadline = time.time() + timeout
        while not self.outgoing.empty() and time.time() < deadline:
            time.sleep(0.01)
        time.sleep(0.05)


class ArduinoController(Controller):
    """Real Miyoo console: button presses go over serial to an Arduino;
    screen state is read by a webcam pointed at the handheld."""

    # The Nano reboots when the port is opened; bytes sent during the bootloader window are
    # swallowed. See the boot-banner note in Serial/Serial.ino's setup() -- a "READY" line
    # would turn this guess into a definite signal.
    RESET_WAIT_S = 2.0

    def __init__(self, port: str = 'COM3', baud: int = buttons.BAUD):
        self.port = port
        self.baud = baud
        self.incoming = queue.Queue()
        self.outgoing = queue.Queue()
        self._echoes = queue.Queue()
        self._write_lock = threading.Lock()
        self._ser: pyserial.Serial | None = None
        self._cap = None
        self._stop = threading.Event()

    def start(self) -> None:
        self._ser = pyserial.Serial(self.port, self.baud, timeout=1)
        time.sleep(self.RESET_WAIT_S)
        self._ser.reset_input_buffer()  # drop bootloader noise
        self._cap = computer_vision.get_cap()
        # Echoes go to their own queue: they are transport confirmation, not game events,
        # and must not reach main.py's message loop.
        threading.Thread(target=serial_com.listener, args=(self._ser, self._echoes), daemon=True).start()
        threading.Thread(target=serial_com.writer, args=(self._ser, self.outgoing, self._write_lock), daemon=True).start()
        threading.Thread(target=self._echo_loop, daemon=True).start()
        threading.Thread(target=self._encounter_loop, daemon=True).start()

    def _echo_loop(self) -> None:
        while not self._stop.is_set():
            try:
                raw = self._echoes.get(timeout=0.5)
            except queue.Empty:
                continue
            # An action with no echo means the byte was dropped or garbled in transit.
            logger.debug(f'Echo: {raw:#04x} ({buttons.describe(raw)})')

    def _encounter_loop(self) -> None:
        # TODO: flesh this out with the actual sweet-scent + post-encounter button
        # choreography, then push 's' onto self.incoming once the encounter is on screen.
        # Mirrors the same TODO on EmulatorController._script_loop.
        logger.warning(
            'Arduino backend has no encounter choreography yet: button commands work, '
            'but nothing will trigger a capture.'
        )

    def capture(self) -> Capture | None:
        im = computer_vision.read(self._cap)
        res = computer_vision.prepare_image(im)
        if res is None:
            return None
        imgray, main_screen_rect, dialog_rect, nametag_rect = res
        return Capture(im, imgray, main_screen_rect, dialog_rect, nametag_rect)

    def close(self) -> None:
        # Nothing in firmware caps how long a coil stays energized, so a solenoid held at
        # shutdown would stay hot until the board is unplugged. Release everything and let
        # the writer drain before the port goes away.
        if self._ser is not None:
            self.release_all()
            self._drain(timeout=2.0)
        self._stop.set()
        if self._cap is not None:
            self._cap.release()
        if self._ser is not None:
            self._ser.close()


class EmulatorController(Controller):
    """mGBA on the same desktop: button presses are posted as Windows key events;
    screen state is the most recent F12 screenshot mGBA writes to disk."""

    # Same button vocabulary as the solenoid rig, mapped to mGBA's default keys.
    _KEYS = {
        buttons.UP: emulator.UP,
        buttons.DOWN: emulator.DOWN,
        buttons.LEFT: emulator.LEFT,
        buttons.RIGHT: emulator.RIGHT,
        buttons.A: emulator.A,
        buttons.B: emulator.B,
        buttons.START: emulator.START,
        buttons.SELECT: emulator.SELECT,
    }

    def __init__(self):
        self.incoming = queue.Queue()
        self.outgoing = queue.Queue()
        self._hwnd: int | None = None
        self._stop = threading.Event()
        self._latest_im = None
        self._latest_lock = threading.Lock()
        self._shot_counter = 0

    def start(self) -> None:
        self._hwnd = emulator.find_mgba_window()
        if not self._hwnd:
            raise RuntimeError('mGBA window not found — is it open with FireRed loaded?')
        threading.Thread(target=self._script_loop, daemon=True).start()
        threading.Thread(target=self._command_loop, daemon=True).start()

    def _script_loop(self) -> None:
        # Stand-in for the arduino sketch. Mirrors that loop's contract:
        # do an encounter sequence, grab the frame, push 's', wait for the controller to ack.
        # TODO: flesh this out with the actual sweet-scent + post-encounter button choreography.
        while not self._stop.is_set():
            self._shot_counter += 1
            out_path = emulator.SHOT_DIR / f'shot-{self._shot_counter:06d}.png'
            if not emulator.request_screenshot(out_path):
                logger.error('Screenshot request timed out — is the Lua script loaded in mGBA and the game unpaused?')
                time.sleep(1)
                continue
            im = cv2.imread(str(out_path))
            if im is None:
                logger.error(f'Failed to read screenshot at {out_path}')
                time.sleep(1)
                continue
            with self._latest_lock:
                self._latest_im = im
            self.incoming.put('s')
            time.sleep(0.5)

    def _command_loop(self) -> None:
        while not self._stop.is_set():
            try:
                steps = self.outgoing.get(timeout=0.5)
            except queue.Empty:
                continue
            for step in steps:
                if isinstance(step, (int, float)) and not isinstance(step, bool):
                    time.sleep(step)
                    continue
                action, button = step
                vk = self._KEYS.get(button)
                if vk is None:
                    logger.warning(f'EmulatorController has no key mapping for {buttons.name(button)}')
                    continue
                if action == buttons.PRESS:
                    emulator.key_down(self._hwnd, vk)
                else:
                    emulator.key_up(self._hwnd, vk)

    def capture(self) -> Capture | None:
        with self._latest_lock:
            im = self._latest_im
        if im is None:
            return None
        # mGBA screenshots are a clean rectangle — no border detection needed.
        # TODO: tune these rects to the actual mGBA frame size you screenshot at.
        h, w = im.shape[:2]
        main_screen_rect = (0, 0, w, h)
        dialog_rect = (0, int(h * 0.70), w, h)
        nametag_rect = (0, int(h * 0.55), int(w * 0.55), int(h * 0.70))
        imgray = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
        return Capture(im, imgray, main_screen_rect, dialog_rect, nametag_rect)

    def close(self) -> None:
        self.release_all()
        self._drain()
        self._stop.set()


def build(backend: str) -> Controller:
    if backend == 'arduino':
        return ArduinoController()
    if backend == 'emulator':
        return EmulatorController()
    raise ValueError(f'Unknown backend: {backend!r} (expected "arduino" or "emulator")')
