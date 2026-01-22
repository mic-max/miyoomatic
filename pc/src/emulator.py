import time
import win32gui
import win32con
from wgcapture import capture_screen
import cv2

def find_mgba_window():
    hwnds = []
    def enum_handler(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            if win32gui.GetWindowText(hwnd).startswith("mGBA"):
                hwnds.append(hwnd)
    win32gui.EnumWindows(enum_handler, None)
    return hwnds[0] if hwnds else None


A = ord('X')
START = win32con.VK_RETURN
DOWN = win32con.VK_DOWN
RIGHT = win32con.VK_RIGHT
def press_key(hwnd, vk, hold=0.1):
    win32gui.PostMessage(hwnd, win32con.WM_KEYDOWN, vk, 0)
    time.sleep(hold)
    win32gui.PostMessage(hwnd, win32con.WM_KEYUP, vk, 0)

def screengrab():
    img = capture_screen(screen="mGBA")
    img_bgr = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
    h, w = img_bgr.shape[:2]
    return img_bgr[64:h-1, 1:w-1]

if __name__ == "__main__":
    hwnd = find_mgba_window()
    if not hwnd:
        raise RuntimeError("mGBA window not found")

    # set emulation speed
    # create non deterministic FSM
    # define start state?
    # define goal state

    while True:
        screen = screengrab()
        cv2.imwrite("tmp/a.png", screen)
        exit()
        # determine state, use previous state? use fsm nodes, since you're more likely to be fewer actions away than more
        # determine best route to goal state
        # execute command on the goal_route's first edge (will fail sometimes)
        # wait for minimum amount of time before checking the new state

    script = [
        (START,  .4), # open menu, can maybe press twice, but no spamming.
        (    A, 1.1), # select pokemon menu item, can spam
        (    A,  .3), # select first slot pokemon
        ( DOWN,  .3), # navigate to sweet scent
        (    A, 9.7), # use sweet scent, can spam
        (    A, 2.9), # skip dialog, can spam
        ( DOWN,  .3), # hover pokemon, can spam
        (RIGHT,  .3), # hover run, can spam
        (    A,  .7), # run, can spam
        (    A, 2.9), # skip dialog, can spam
    ]
