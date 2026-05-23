# Post a random encounter (or several) to the miyoomatic API. Useful for:
# - manually testing the websocket / queue animation without booting the controller
# - smoke-testing changes to the API contract
# Run after `python pc/src/api.py` is up.

import argparse
import random
import time
import uuid

import api_client
import Pokemon


def weighted_pick(spawns: dict) -> dict:
    flat = []
    for pid, p in spawns.items():
        for row in p['levels']:
            flat.append({
                'pokedex_id': pid,
                'name': p['name'],
                'level': row['level'],
                'odds': row['odds'],
            })
    total = sum(x['odds'] for x in flat)
    r = random.random() * total
    for row in flat:
        r -= row['odds']
        if r <= 0:
            return row
    return flat[-1]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Post simulated encounters to the miyoomatic API.')
    p.add_argument('--location-id', type=int, default=99)
    p.add_argument('--method-id', type=int, default=0)
    p.add_argument('--count', type=int, default=1, help='Number of encounters to post.')
    p.add_argument('--interval', type=float, default=0.5, help='Seconds between encounters.')
    p.add_argument('--shiny-odds', type=int, default=8192, help='1-in-N shiny chance.')
    return p.parse_args()


if __name__ == '__main__':
    args = parse_args()
    spawns = api_client.get_spawns(args.location_id, args.method_id)
    for i in range(args.count):
        pick = weighted_pick(spawns)
        gender = random.choice([Pokemon.Gender.MALE, Pokemon.Gender.FEMALE])
        is_shiny = random.randint(1, args.shiny_odds) == 1
        pokemon = Pokemon.Pokemon(pick['pokedex_id'], pick['name'], pick['level'], gender, is_shiny)
        encounter_id = uuid.uuid7()
        api_client.record_encounter(encounter_id, pokemon, args.location_id, args.method_id)
        print(f'#{i + 1} {pokemon}')
        if i + 1 < args.count:
            time.sleep(args.interval)
