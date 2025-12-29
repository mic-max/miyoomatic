# PIP
import cv2
import numpy as np
import pytesseract
import skimage.color
import sklearn.cluster

# Local
import Pokemon

palettes = {
    "92": [
        (0xF8F8F8, 2438),
        (0xF8F8F8, 60),
        (0xD8D8D8, 27),
        (0xD85038, 29),
        (0xB02810, 27),
        (0xF800F8, 0),
        (0xB890B0, 0),
        (0x886080, 32),
        (0x704868, 60),
        (0x503058, 166),
        (0xD0A8C8, 581),
        (0xB890B0, 421),
        (0x886080, 209),
        (0xF800F8, 0),
        (0xF800F8, 0),
        (0x101010, 46),
    ],
    "-92": [
        (0xF8F8F8, 2438),
        (0xF8F8F8, 60),
        (0xD8D8D8, 27),
        (0xD85038, 29),
        (0xB02810, 27),
        (0xF800F8, 0),
        (0xA880E0, 0),
        (0x9070C0, 32),
        (0x583890, 60),
        (0x502860, 166),
        (0x98D8F8, 581),
        (0x70B0D0, 421),
        (0x4888A8, 209),
        (0xF800F8, 0),
        (0xF800F8, 0),
        (0x101010, 46),
    ],
    "93": [
        (0xD0D0B8, 2568),
        (0xC090D8, 192),
        (0x9068B0, 465),
        (0x605080, 327),
        (0x583870, 157),
        (0xF800F8, 0),
        (0xF800F8, 0),
        (0xF800F8, 0),
        (0xF800F8, 0),
        (0xD83030, 102),
        (0xB01818, 22),
        (0x601010, 23),
        (0xD8D8D8, 16),
        (0x707070, 1),
        (0x101010, 197),
        (0xF8F8F8, 26),
    ],
    "-93": [
        (0xD0D0B8, 2568),
        (0xD0A0D8, 192),
        (0xC080C8, 465),
        (0x8058A0, 327),
        (0x503060, 157),
        (0xF800F8, 0),
        (0xF800F8, 0),
        (0xF800F8, 0),
        (0xF800F8, 0),
        (0x4898C0, 102),
        (0x207098, 22),
        (0x004068, 23),
        (0xD0D0D0, 16),
        (0x707070, 1),
        (0x101010, 197),
        (0xF8F8F8, 26),
    ],
    "104": [
        (0x48C888, 3277),
        (0xD8B868, 28),
        (0xC09848, 64),
        (0x906830, 110),
        (0x503018, 37),
        (0xE8E8E8, 113),
        (0xC8C8B0, 105),
        (0x888868, 25),
        (0x585830, 43),
        (0xF0E0C8, 29),
        (0xF8D0A0, 53),
        (0xE0B088, 25),
        (0xF800F8, 0),
        (0xF800F8, 0),
        (0x282828, 131),
        (0xF8F8F8, 56),
    ],
    "-104": [
        (0xD0D0B8, 3277),
        (0xA8B070, 28),
        (0x808048, 64),
        (0x485018, 110),
        (0x303800, 37),
        (0xE0E0D0, 113),
        (0xC0C0A8, 105),
        (0x888868, 25),
        (0x585830, 43),
        (0xF8E8C0, 29),
        (0xE8D090, 53),
        (0xC8A058, 25),
        (0xF800F8, 0),
        (0xF800F8, 0),
        (0x282828, 131),
        (0xF8F8F8, 56),
    ],
}

pytesseract.pytesseract.tesseract_cmd = r"C:/Program Files/Tesseract-OCR/tesseract.exe"
resolution_x, resolution_y = 240, 160
THRESHOLD_LOWER = 60
NUM_DOMINANT_COLORS = 16

def prepare_image(im):
    # TODO: deskew the image
    imgray = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(imgray, THRESHOLD_LOWER, 255, cv2.THRESH_BINARY)
    contours, hierarchy = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    rects = []
    for i, cnt in enumerate(contours):
        x, y, w, h = cv2.boundingRect(cnt)
        area = w * h
        if area > 25000 and w > 50 and h > 50:
            rects.append({
                "id": i,
                "rect": (x, y, w, h),
                "next": hierarchy[0][i][0],
                "prev": hierarchy[0][i][1],
                "child": hierarchy[0][i][2],
                "parent": hierarchy[0][i][3],
                "area": area
            })

    rects.sort(key=lambda x: x["area"], reverse=True)

    if len(rects < 4): return None

    main_screen_rect = rects[0]["rect"]
    dialog_rect = rects[2]["rect"]
    nametag_rect = rects[3]["rect"]

    return imgray, main_screen_rect, dialog_rect, nametag_rect

def get_cap():
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    if not cap.isOpened():
        raise RuntimeError('Cannot open webcam')
    return cap

def read(cap):
    status, frame = cap.read()
    if not status:
        raise RuntimeError('Error reading webcam')
    return frame

def get_palette(pokedex_id: int):
    res = [colour for colour, count in palettes[str(pokedex_id)][1:] if count >= 0]
    # no duplicates
    # no background colour
    # no palette colours that are not used in the sprite (0 pixels reference it)
    return list(set(res))

def encounter_roi(im, rect, pokedex_id):
    x, y, w, h = rect
    # print('encounter', w, h)
    # scale_x, scale_y = w / 240, h / 112
    # x, y, w, h = 144, 8, 64, 64
    # roi = im[y:y + h, x:x + w]
    xx = int(0.5950 * w) + x
    yy = int(0.1014 * h) + y # increase this depending on the pokedex_id, cubone is lower than ghastly
    ww = int(0.2666 * w)
    hh = int(0.5714 * h)

    roi = im[yy:yy + hh, xx:xx + ww]
    roi = cv2.resize(roi, (64, 64), interpolation=cv2.INTER_NEAREST)
    roi = normalize_brightness(roi, 207)

    # TODO exclude background colour
    # exclude any colours with 0 count
    palA = get_palette(pokedex_id)
    palB = get_palette(-pokedex_id)
    print(palA)
    print(palB)
    palP = dominant_colors(roi, NUM_DOMINANT_COLORS)
    palPx = [[r.item(), g.item(), b.item()] for b, g, r in palP]

    distA = palette_distance(palPx, palA)
    distB = palette_distance(palPx, palB)
    return distA, distB, abs(distA - distB)

def show_image(title, im):
    cv2.imshow(title, im)
    cv2.waitKey(0)

def write_image(filename, im) -> bool:
    return cv2.imwrite(filename, im)

def name_roi(imgray, rect):
    x, y, w, h = rect
    # TODO use the scale: scale_x, scale_y = w / 224, h / 34
    xx = int(0.115 * w) + x # x offset in native res is 25.76 pixels
    yy = int(0.093 * h) + y # y offset in native res is xxx pixels
    ww = int(0.292 * w) # ten letters plus padding, native res width is 65.389 pixels, which means ~2.5 pixels of hpad on the word and each letter is 6 pixels wide including trailing padding
    hh = int(0.378 * h) # native res height is 12.85 pixels
    roi = imgray[yy:yy + hh, xx:xx + ww]
    config = "--psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    name = pytesseract.image_to_string(roi, config=config).strip()
    name = name.capitalize()
    return name

def level_roi(imgray, rect):
    x, y, w, h = rect
    # TODO use the scale: scale_x, scale_y = w / 92, h / 29
    xx = int(0.820 * w) + x
    yy = int(0.110 * h) + y
    ww = int(0.180 * w)
    hh = int(0.400 * h)
    roi = imgray[yy:yy + hh, xx:xx + ww]

    config = "--psm 7 -c tessedit_char_whitelist=0123456789 -c classify_bln_numeric_mode=1"
    level = pytesseract.image_to_string(roi, config=config).strip()
    try:
        i = int(level)
    except ValueError:
        i = 0
    return i

def gender_roi(im, rect) -> Pokemon.Gender:
    return Pokemon.Gender.MALE
    # x, y, w, h = 100, 100, 30, 60
    # x += len(name) * 6 # each letter is 5px wide and has a 1px space after
    # gender_roi = warped[y:y + h, x:x + w]
    # hsv = cv2.cvtColor(gender_roi, cv2.COLOR_BGR2HSV)

    # pink_pixels = cv2.countNonZero(cv2.inRange(hsv, np.array([0, 2, 177]), np.array([24, 60, 228])))
    # blue_pixels = cv2.countNonZero(cv2.inRange(hsv, np.array([71, 19, 153]), np.array([103, 87, 197])))

    # is_male = None
    # if pink_pixels > blue_pixels:
    #     is_male = False
    # elif blue_pixels > pink_pixels:
    #     is_male = True
    # return is_male

def dominant_colors(im, n: int):
    data = im.reshape((-1, 3))
    kmeans = sklearn.cluster.KMeans(n_clusters=n, n_init=3, random_state=0)
    kmeans.fit(data)
    return np.uint8(kmeans.cluster_centers_)

def palette_distance(pal1, pal2):
    pal1 = np.array(pal1, dtype=np.uint8)
    pal2 = np.array(pal2, dtype=np.uint8)
    lab1 = skimage.color.rgb2lab(pal1[None, :, :] / 255.0)
    lab2 = skimage.color.rgb2lab(pal2[None, :, :] / 255.0)
    dist_matrix = skimage.color.deltaE_cie76(lab1[:, None, :, :], lab2[:, :, None, :])
    return float(np.mean(np.min(dist_matrix, axis=2)))

def normalize_brightness(im, mean_ref_v: int):
    imhsv = cv2.cvtColor(im, cv2.COLOR_BGR2HSV)
    mean_photo_v = np.mean(imhsv[..., 2])
    imhsv[..., 2] = np.clip(imhsv[..., 2] * (mean_ref_v / mean_photo_v), 0, 255)
    return cv2.cvtColor(imhsv, cv2.COLOR_HSV2BGR)
