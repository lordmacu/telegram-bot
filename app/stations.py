import json
import math
import time

from . import config, tm_client


async def get_all_stations(force_refresh: bool = False) -> list[dict]:
    if not force_refresh and config.STATIONS_CACHE_PATH.exists():
        age = time.time() - config.STATIONS_CACHE_PATH.stat().st_mtime
        if age < config.STATIONS_CACHE_TTL_SECONDS:
            try:
                return json.loads(config.STATIONS_CACHE_PATH.read_text())
            except (json.JSONDecodeError, OSError):
                pass
    stations = await tm_client.search_stations(None)
    try:
        config.STATIONS_CACHE_PATH.write_text(json.dumps(stations))
    except OSError:
        pass
    return stations


def es_troncal(station: dict) -> bool:
    return (station.get("codigo") or "").upper().startswith("TM")


def search_by_text(stations_list: list[dict], text: str, limit: int = 8) -> list[dict]:
    text_norm = text.strip().lower()
    if not text_norm:
        return []
    matches = [
        s
        for s in stations_list
        if text_norm in (s.get("nombre") or "").lower()
        or text_norm in (s.get("direccion") or "").lower()
        or text_norm == (s.get("codigo") or "").lower()
    ]
    return matches[:limit]


def find_by_codigo(stations_list: list[dict], codigo: str) -> dict | None:
    codigo_norm = codigo.strip().lower()
    for s in stations_list:
        if (s.get("codigo") or "").lower() == codigo_norm:
            return s
    return None


def _parse_coordenada(coordenada: str) -> tuple[float, float] | None:
    if not coordenada:
        return None
    parts = coordenada.replace("(", "").replace(")", "").split(",")
    if len(parts) != 2:
        return None
    try:
        return float(parts[0].strip()), float(parts[1].strip())
    except ValueError:
        return None


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    earth_radius_m = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * earth_radius_m * math.asin(math.sqrt(a))


def nearest_stations(stations_list: list[dict], lat: float, lon: float, top_n: int = 6) -> list[dict]:
    scored = []
    for s in stations_list:
        coords = _parse_coordenada(s.get("coordenada") or "")
        if not coords:
            continue
        dist = _haversine_m(lat, lon, coords[0], coords[1])
        scored.append((dist, s))
    scored.sort(key=lambda t: t[0])
    result = []
    for dist, s in scored[:top_n]:
        s2 = dict(s)
        s2["_distancia_m"] = round(dist)
        result.append(s2)
    return result
