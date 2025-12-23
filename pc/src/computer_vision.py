# PIP
import cv2
import numpy as np
import pytesseract
import skimage.color
import sklearn.cluster

# Local
import Pokemon
import database

pytesseract.pytesseract.tesseract_cmd = r"C:/Program Files/Tesseract-OCR/tesseract.exe"
resolution_x, resolution_y = 240, 160
THRESHOLD_LOWER = 60
NUM_DOMINANT_COLORS = 16

def prepare_image(conn, im):
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

    # if len(rects < 4): return None

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

def imread(cap, filename):
    return cv2.imread(filename)

def read(cap):
    status, frame = cap.read()
    if not status:
        raise RuntimeError('Error reading webcam')
    return frame

def encounter_roi(conn, im, rect, pokedex_id):
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
    
    # TODO: does order matter? select * order by id ASC (insertion order since i insert in sorted order)
    palA, palB = database.get_palettes(conn, [pokedex_id, -pokedex_id])
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
