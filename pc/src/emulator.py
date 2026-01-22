import time
import win32gui
import win32con


def find_mgba_window():
    result = []

    def enum_handler(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if title.startswith("mGBA"):
                result.append(hwnd)

    win32gui.EnumWindows(enum_handler, None)
    return result[0] if result else None

def press_key(hwnd, vk, hold_seconds=0.1):
    win32gui.PostMessage(hwnd, win32con.WM_KEYDOWN, vk, 0)
    time.sleep(hold_seconds)
    win32gui.PostMessage(hwnd, win32con.WM_KEYUP, vk, 0)


if __name__ == "__main__":
    hwnd = find_mgba_window()

    if hwnd is None:
        raise RuntimeError("mGBA window not found")

    A = ord('X')
    START = win32con.VK_RETURN
    DOWN = win32con.VK_DOWN
    RIGHT = win32con.VK_RIGHT

    script = [
        (      START,  0.4), # open menu, can maybe press twice, but no spamming.
        (          A, 1.1), # select pokemon menu item, can spam
        (          A,  .3), # select first slot pokemon
        (       DOWN,  .3), # navigate to sweet scent
        (          A, 9.7), # use sweet scent, can spam
        (          A, 2.9), # skip dialog, can spam
        (       DOWN,  .3), # hover pokemon, can spam
        (      RIGHT,  .3), # hover run, can spam
        (          A,  .7), # run, can spam
        (          A, 2.9), # skip dialog, can spam
    ]
    
    while True:
        for key, wait in script:
            press_key(hwnd, key, 0.1)
            time.sleep(wait)
