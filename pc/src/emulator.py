# Python
import ctypes
from pathlib import Path
import time

# PIP
import win32con
import win32gui
import networkx as nx
import cv2

SCREENSHOT_DIR = Path(r"C:\ROMs\GBA\screenshots")
SCREENSHOT_INDEX = 0

A = ord('X')
B = ord('Z')
START = win32con.VK_RETURN
UP = win32con.VK_UP
DOWN = win32con.VK_DOWN
LEFT = win32con.VK_LEFT
RIGHT = win32con.VK_RIGHT
SCREENSHOT = win32con.VK_F12

HOLD_KEY = 0.2
WAIT_FOR_FOCUS = 0.1
WAIT_FOR_SCREENSHOT = 0.2

DETECT_MENU = "menu_unknown"
OVERWORLD = "overworld"
MENU = "menu"
PARTY_CANCEL = "party_cancel"

menu_items = [
    "menu_pokedex",
    "menu_pokemon",
    "menu_bag",
    "menu_player",
    "menu_save",
    "menu_option",
    "menu_exit",
]

party_items = [
    "party_1",
    "party_2",
    "party_3",
    "party_4",
    "party_5",
    "party_6",
    "party_cancel",
]

def find_mgba_window():
    hwnds = []
    def enum_handler(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            if win32gui.GetWindowText(hwnd).startswith("mGBA"):
                hwnds.append(hwnd)
    win32gui.EnumWindows(enum_handler, None)
    return hwnds[0] if hwnds else None

def press_key(hwnd, vk):
    win32gui.PostMessage(hwnd, win32con.WM_KEYDOWN, vk, 0)
    time.sleep(HOLD_KEY)
    win32gui.PostMessage(hwnd, win32con.WM_KEYUP, vk, 0)

def press_f12_to_window(hwnd):
    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
    win32gui.SetForegroundWindow(hwnd)
    time.sleep(WAIT_FOR_FOCUS)
    ctypes.windll.user32.keybd_event(SCREENSHOT, 0, 0, 0)
    time.sleep(HOLD_KEY)
    ctypes.windll.user32.keybd_event(SCREENSHOT, 0, 0x0002, 0)

def capture(hwnd, output_dir: Path, filename: str):
    """
    Capture a screenshot via mGBA F12 and rename it to {filename}.png.

    Parameters:
        hwnd         : window handle for the emulator
        output_dir   : Path to the screenshot directory
        filename     : base filename (no extension), e.g. "menu"
        wait_seconds : time to wait for the screenshot to be written
    """
    global SCREENSHOT_INDEX
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    source = output_dir / "firered-0.png"
    target = output_dir / f"{SCREENSHOT_INDEX:02}-{filename}.png"

    # Remove any stale files
    if source.exists():
        source.unlink()
    if target.exists():
        target.unlink()

    # Trigger screenshot
    press_f12_to_window(hwnd)
    time.sleep(WAIT_FOR_SCREENSHOT)
    SCREENSHOT_INDEX += 1

    # Force-rename (overwrites if target exists)
    if not source.exists():
        raise FileNotFoundError(f"Expected screenshot not found: {source}")

    source.replace(target)

def most_recent_file(directory: Path) -> Path | None:
    directory = Path(directory)

    files = [p for p in directory.iterdir() if p.is_file()]
    if not files:
        return None

    return max(files, key=lambda p: p.stat().st_mtime)


def perform_action(hwnd, button):
    if button == DETECT_MENU:
        pass # menu_selected()
    else:
        press_key(hwnd, button)

def menu_selected(img) -> int:
    # Checks for the arrow in front of the menu item
    for i in range(7):
        if img[15 * i + 14][179][0] == 99:
            return i
    return -1

def is_menu_open(img):
    return img[153][236][0] == 198

def execute_edge(hwnd, edge):
    global SCREENSHOT_INDEX
    button = edge["button"]
    if button == DETECT_MENU:
        menu_img_path = most_recent_file(SCREENSHOT_DIR)
        img = cv2.imread(menu_img_path)
        assert is_menu_open(img)
        
        menu_index = menu_selected(img)
        assert menu_index != -1
        
        # Delete the previous screenshot of the menu
        # TODO: it would be better to rename this file
        menu_img_path.unlink()
        SCREENSHOT_INDEX -= 1
        return menu_items[menu_index]
    else:
        press_key(hwnd, button)
    return None

def replay_path(hwnd, G, path):
    for u, v in zip(path, path[1:]):
        edge = G.edges[u, v]
        execute_edge(hwnd, edge)

def traverse(hwnd, G, current_node, visited):
    if current_node not in visited:
        visited.add(current_node)
        capture(hwnd, SCREENSHOT_DIR, current_node)
        # TODO: maybe i conditionally capture. since for example when the previous node was menu
        # i dont need to capture another screenshot. i can just rename the exisiting menu.png to its actual classification
        # now i actually only want to rename that image and not take another screenshot.
        # Note: The screen capture for menu needs to be renamed to whatever current menu_item is detected

    for _, target, data in G.out_edges(current_node, data=True):
        # Execute edge
        # This will either press the button or detect the actual menu item hovered
        resolved_node = execute_edge(hwnd, data)

        if resolved_node is not None:
            next_node = resolved_node
        else:
            next_node = target

        if next_node not in visited:
            traverse(hwnd, G, next_node, visited)

            # Return to current_node after exploration
            return_path = nx.shortest_path(G, next_node, current_node)
            replay_path(hwnd, G, return_path)

# Building the graph as we explore might be the move.
# Since when I open the menu, there might not always be certain options
# For example early game before you have the pokedex or pokemon i think those items are missing
# Or when you only have 3/6 pokemon in your party, that changes the structure of the graph.

def build_graph():
    # Add nodes
    G = nx.MultiDiGraph()
    G.add_node(OVERWORLD)
    G.add_node(MENU)
    for menu_item in menu_items:
        G.add_node(menu_item)
    for party_item in party_items:
        G.add_node(party_item)
    G.add_node(f"party_cancel")

    # Add edges
    G.add_edge(OVERWORLD, MENU, button=START)
    for i, menu_item in enumerate(menu_items):
        up = menu_items[(i - 1) % len(menu_items)]
        down = menu_items[(i + 1) % len(menu_items)]

        G.add_edge(MENU, menu_item, button=DETECT_MENU)
        G.add_edge(menu_item, down, button=DOWN)
        G.add_edge(menu_item, up, button=UP)
        G.add_edge(menu_item, OVERWORLD, button=START)
        G.add_edge(menu_item, OVERWORLD, button=B)
    G.add_edge(menu_items[-1], OVERWORLD, button=A) # menu_exit
    
    # Add Menu Pokemon Edges
    menu_pokemon = menu_items[1]
    G.add_edge(menu_pokemon, party_items[0], button=A)
    
    for i, party_item in enumerate(party_items):
        up = party_items[(i - 1) % len(party_items)]
        down = party_items[(i + 1) % len(party_items)]

        G.add_edge(party_item, menu_pokemon, button=B)
        G.add_edge(party_item, down, button=DOWN)
        G.add_edge(party_item, up, button=UP)
        if i != 0 and i != len(party_items) - 1:
            G.add_edge(party_item, party_items[0], button=LEFT)
        # TODO: press right from party_1 will default to party 2
        # what happens if you have 1 pokemon will it default to cancel?
        # focus the most recently viewed party member from 2 to 6, defaults to party_2
        # it works weird, if i hover party 4, press left, press down, press up, press right
        #   it will return to party 4 even though i hovered party 2 which i assumed was part of that column..
    # Party Cancel
    G.add_edge(party_items[-1], menu_pokemon, button=A)

    return G

# -----------------------------
# Entry point
# -----------------------------

def main():
    hwnd = find_mgba_window()
    if not hwnd:
        raise RuntimeError("mGBA window not found")

    # Visit all nodes
    G = build_graph()
    visited = set()
    traverse(hwnd, G, OVERWORLD, visited)
    
    # Return to overworld
    

if __name__ == "__main__":
    main()
