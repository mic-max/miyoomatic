# Python
import logging
import os
import queue
import serial
import threading
import time

# PIP
import dotenv

# Local
import database
import serial_com
import webserver
import computer_vision
import Pokemon
import user_input
import notify

if __name__ == '__main__':
    clients = set()
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    logger = logging.getLogger(__name__)
    dotenv.load_dotenv()
    pushover_token = os.getenv('PUSHOVER_USER_TOKEN')

    incoming = queue.Queue()
    outgoing = queue.Queue()
    write_lock = threading.Lock()
    conn = database.connect()

    threading.Thread(target=webserver.start_http_server, daemon=True).start()
    threading.Thread(target=webserver.run_ws_server, daemon=True).start()
    # ser = serial.Serial('COM3', 9600, timeout=1)
    # threading.Thread(target=serial_com.listener, args=(ser, incoming), daemon=True).start()
    # threading.Thread(target=serial_com.writer, args=(ser, outgoing, write_lock), daemon=True).start()

    cap = computer_vision.get_cap()

    location_id = 99 # Pokemon Tower 3F
    encounter_method = 0 # Grass or Cave
    exp_spawns = database.get_spawns(conn, location_id, encounter_method)

    # TODO: add notification that if i haven't received a message in over X seconds, alert me.
    try:
        while True:
            while not incoming.empty():
                # TODO: maybe the message includes the location_id and method_id
                msg = incoming.get()
                logger.info(f"Received: {msg}")
                if msg == 's':
                    encounter_id = int(time.time())
                    # TODO: update to python 3.14 and use uuid.uuid7()
                    im = computer_vision.read(cap)
                    write_status = computer_vision.write_image(f"pc/img/pics/{encounter_id}.jpg", im)
                    if not write_status:
                        logger.warning("Photo not saved")

                    imgray, main_screen_rect, dialog_rect, nametag_rect = computer_vision.prepare_image(conn, im)
                    name = computer_vision.name_roi(imgray, dialog_rect)
                    exp_names = {x["name"] for x in exp_spawns.values()}
                    if name not in exp_names:
                        message = f"Unexpected name: {name}"
                        logger.error(message)
                        notify.send_push(pushover_token, message)
                        computer_vision.show_image("whoami", im)
                        name = user_input.get_pokemon_name(exp_spawns)

                    pokedex_id = database.get_id_from_name(conn, name)

                    # Note: encounter_ROI is slow on the first execution
                    # TODO: use the pokemon's sprite size and location to better select the encounter ROI
                    distA, distB, delta = computer_vision.encounter_roi(conn, im, main_screen_rect, pokedex_id)
                    is_shiny = distA > distB
                    if delta <= 2:
                        message = f"Weak palette delta: {delta:.1f}"
                        logger.error(message)
                        notify.send_push(pushover_token, message)
                        computer_vision.show_image("shinyami", im)
                        is_shiny = user_input.confirm_shiny_result()

                    if is_shiny:
                        message = f"Shiny Detected: {name}"
                        logger.critical(message)
                        notify.send_push(pushover_token, message)
                    else:
                        outgoing.put('r')

                    level = computer_vision.level_roi(imgray, nametag_rect)
                    if level not in exp_spawns[pokedex_id]["levels"]:
                        level = None

                    gender = computer_vision.gender_roi(im, nametag_rect)
                    if gender not in exp_spawns[pokedex_id]["genders"]:
                        gender = None

                    pokemon = Pokemon.Pokemon(pokedex_id, name, level, gender, is_shiny)
                    logger.info(pokemon)
                    database.record_encounter(pokemon, encounter_id)
            time.sleep(0.01)
    except KeyboardInterrupt:
        logger.info("Stopping...")
    finally:
        cap.release()
