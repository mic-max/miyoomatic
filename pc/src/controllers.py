import abc
import logging
import queue
import threading
import time
from dataclasses import dataclass
from typing import Any

import cv2
import serial as pyserial

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

    def send(self, command: str) -> None:
        self.outgoing.put(command)

    @abc.abstractmethod
    def close(self) -> None: ...


class ArduinoController(Controller):
    """Real Miyoo console: button presses go over serial to an Arduino;
    screen state is read by a webcam pointed at the handheld."""

    def __init__(self, port: str = 'COM3', baud: int = 9600):
        self.port = port
        self.baud = baud
        self.incoming = queue.Queue()
        self.outgoing = queue.Queue()
        self._write_lock = threading.Lock()
        self._ser: pyserial.Serial | None = None
        self._cap = None

    def start(self) -> None:
        self._ser = pyserial.Serial(self.port, self.baud, timeout=1)
        self._cap = computer_vision.get_cap()
        threading.Thread(target=serial_com.listener, args=(self._ser, self.incoming), daemon=True).start()
        threading.Thread(target=serial_com.writer, args=(self._ser, self.outgoing, self._write_lock), daemon=True).start()

    def capture(self) -> Capture | None:
        im = computer_vision.read(self._cap)
        res = computer_vision.prepare_image(im)
        if res is None:
            return None
        imgray, main_screen_rect, dialog_rect, nametag_rect = res
        return Capture(im, imgray, main_screen_rect, dialog_rect, nametag_rect)

    def close(self) -> None:
        if self._cap is not None:
            self._cap.release()
        if self._ser is not None:
            self._ser.close()


class EmulatorController(Controller):
    """mGBA on the same desktop: button presses are posted as Windows key events;
    screen state is the most recent F12 screenshot mGBA writes to disk."""

    # Mirror the arduino's tiny command vocabulary. Extend as needed.
    _COMMAND_KEYS = {
        'r': emulator.B,  # 'r' from main loop = "run away" -> press B in the emulator
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
                cmd = self.outgoing.get(timeout=0.5)
            except queue.Empty:
                continue
            key = self._COMMAND_KEYS.get(cmd)
            if key is None:
                logger.warning(f'EmulatorController has no key mapping for {cmd!r}')
                continue
            emulator.press_key(self._hwnd, key)

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
        self._stop.set()


def build(backend: str) -> Controller:
    if backend == 'arduino':
        return ArduinoController()
    if backend == 'emulator':
        return EmulatorController()
    raise ValueError(f'Unknown backend: {backend!r} (expected "arduino" or "emulator")')
