# PIP
import sqlite3
import typing

# Local
import Pokemon

def connect():
    return sqlite3.connect('miyoomatic.db')

def record_encounter(pokemon: Pokemon.Pokemon, encounter_id: int):
    # insert to database
    # broadcast over websocket
    pass

def get_all_messages(conn: sqlite3.Connection) -> any:
    cur = conn.execute('SELECT id, content FROM messages ORDER BY id ASC')
    return cur.fetchall()

def get_id_from_name(conn: sqlite3.Connection, name: str) -> int | None:
    cur = conn.execute('SELECT id FROM pokemon WHERE name = ?', (name,))
    row = cur.fetchone()
    return row[0] if row else None

def get_spawns(conn: sqlite3.Connection, location_id: int, method_id: int) -> dict:
    cur = conn.execute("""
        SELECT spawns.pokemon_id, pokemon.name, spawns.level
        FROM spawns
        INNER JOIN pokemon
        ON spawns.pokemon_id=pokemon.pokemon_id
        WHERE spawns.location_id = ?
        ORDER BY spawns.pokemon_id ASC
    """, (location_id,))

    result = {}
    for pokemon_id, name, level in cur.fetchall():
        if pokemon_id not in result:
            result[pokemon_id] = {
                'name': name,
                'levels': [],
                'genders': [Pokemon.Gender.MALE, Pokemon.Gender.FEMALE]
            }
        result[pokemon_id]['levels'].append(level)
    return result
