import os

import httpx

BASE_URL = os.getenv("MIYOOMATIC_API", "http://localhost:8001")

_client = httpx.Client(base_url=BASE_URL, timeout=5.0)


def get_spawns(location_id: int, method_id: int) -> dict:
    r = _client.get(f"/spawns/{location_id}/{method_id}")
    r.raise_for_status()
    # JSON keys come back as strings — restore int keys to match the old database.get_spawns contract.
    return {int(k): v for k, v in r.json().items()}


def get_id_from_name(name: str) -> int | None:
    r = _client.get("/pokemon", params={"name": name})
    if r.status_code == 404:
        return None
    r.raise_for_status()
    return r.json()["pokedex_id"]


def send_notification(message: str) -> None:
    r = _client.post("/notifications", json={"message": message})
    r.raise_for_status()


def record_encounter(encounter_id, pokemon, location_id: int, method_id: int) -> None:
    payload = {
        "encounter_id": str(encounter_id),
        "pokedex_id": pokemon.pokedex_id,
        "name": pokemon.name,
        "level": pokemon.level,
        "gender": pokemon.gender.value if pokemon.gender is not None else None,
        "is_shiny": pokemon.is_shiny,
        "location_id": location_id,
        "method_id": method_id,
    }
    r = _client.post("/encounters", json=payload)
    r.raise_for_status()
