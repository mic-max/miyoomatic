# Python
import argparse
import logging
import time
import uuid

# Local
import api_client
import computer_vision
import controllers
import Pokemon
import user_input


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="miyoomatic controller — drives the game via mGBA or Miyoo over Arduino."
    )
    p.add_argument(
        "--backend",
        choices=["arduino", "emulator"],
        default="arduino",
        help="arduino: real console over serial + webcam. emulator: mGBA on this desktop.",
    )
    p.add_argument(
        "--location-id", type=int, default=99, help="Default: 99 (Pokemon Tower 3F)"
    )
    p.add_argument(
        "--encounter-method", type=int, default=0, help="Default: 0 (Grass or Cave)"
    )
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logger = logging.getLogger(__name__)
    logger.info(f"Backend: {args.backend}")

    controller = controllers.build(args.backend)
    controller.start()

    exp_spawns = api_client.get_spawns(args.location_id, args.encounter_method)

    # TODO: add notification that if i haven't received a message in over X seconds, alert me.
    try:
        while True:
            while not controller.incoming.empty():
                # TODO: maybe the message includes the location_id and method_id
                msg = controller.incoming.get()
                logger.info(f"Received: {msg}")
                if msg != "s":
                    continue

                encounter_id = uuid.uuid7()
                cap_result = controller.capture()
                if cap_result is None:
                    message = "Could not prepare image from controller capture."
                    logger.error(message)
                    continue

                computer_vision.write_image(
                    f"pc/img/pics/{encounter_id}.jpg", cap_result.raw
                )

                name = computer_vision.name_roi(
                    cap_result.imgray, cap_result.dialog_rect
                )
                exp_names = [x["name"] for x in exp_spawns.values()]
                if name not in exp_names:
                    message = f"Unexpected name: {name}"
                    logger.error(message)
                    api_client.send_notification(message)
                    computer_vision.show_image("whoami", cap_result.raw)
                    name = user_input.get_pokemon_name(exp_spawns)

                pokedex_id = api_client.get_id_from_name(name)

                # Note: encounter_ROI is slow on the first execution
                # TODO: use the pokemon's sprite size and location to better select the encounter ROI
                distA, distB, delta = computer_vision.encounter_roi(
                    cap_result.raw, cap_result.main_screen_rect, pokedex_id
                )
                is_shiny = distA > distB
                if delta <= 2:
                    message = f"Weak palette delta: {delta:.1f}"
                    logger.error(message)
                    api_client.send_notification(message)
                    computer_vision.show_image("shinyami", cap_result.raw)
                    is_shiny = user_input.confirm_shiny_result()

                if is_shiny:
                    # API will fire the Pushover notification when it persists the encounter.
                    logger.critical(f"Shiny Detected: {name}")
                else:
                    controller.send("r")

                level = computer_vision.level_roi(
                    cap_result.imgray, cap_result.nametag_rect
                )
                allowed_levels = [x["level"] for x in exp_spawns[pokedex_id]["levels"]]
                if level not in allowed_levels:
                    level = None

                gender = computer_vision.gender_roi(
                    cap_result.raw, cap_result.nametag_rect
                )
                if gender not in exp_spawns[pokedex_id]["genders"]:
                    gender = None

                pokemon = Pokemon.Pokemon(pokedex_id, name, level, gender, is_shiny)
                logger.info(pokemon)
                api_client.record_encounter(
                    encounter_id, pokemon, args.location_id, args.encounter_method
                )
            time.sleep(0.01)
    except KeyboardInterrupt:
        logger.info("Stopping...")
    finally:
        controller.close()
