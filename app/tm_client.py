import logging

import httpx

from . import config

_client: httpx.AsyncClient | None = None
log = logging.getLogger(__name__)


async def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(timeout=config.HTTP_TIMEOUT_SECONDS)
    return _client


def _rutas_headers() -> dict:
    return {"uuid": config.APP_UUID, "version": config.APP_VERSION}


def _bodega_headers() -> dict:
    headers = {"uuid": config.APP_UUID, "version": config.APP_VERSION}
    if config.BODEGA_EXTRA_HEADER_NAME:
        headers[config.BODEGA_EXTRA_HEADER_NAME] = config.BODEGA_EXTRA_HEADER_VALUE
    return headers


async def search_stations(search: str | None) -> list[dict]:
    """APIServiceInterface.searchStations() -> EstacionesAppListModel.listParadas"""
    params = {"lServicio": "Rutas", "lTipo": "api", "lFuncion": "getParaderosList"}
    if search:
        params["search"] = search
    client = await _get_client()
    r = await client.get(f"{config.RUTAS_BASE}/loader.php", params=params, headers=_rutas_headers())
    r.raise_for_status()
    return r.json().get("listParadas") or []


async def get_rutas_de_estacion(estacion_codigo: str, es_troncal: bool) -> list[dict]:
    """getRutasDeUnaEstacion() (troncal) / getRutasDeUnaEstacionZonal() (zonal) -> RutasListModel.lista_rutas"""
    l_funcion = "searchRutasByEstacionTroncales" if es_troncal else "findRutasByParada"
    param_name = "estacion" if es_troncal else "parada"
    params = {"lServicio": "Rutas", "lTipo": "api", "lFuncion": l_funcion, param_name: estacion_codigo}
    client = await _get_client()
    r = await client.get(f"{config.RUTAS_BASE}/loader.php", params=params, headers=_rutas_headers())
    r.raise_for_status()
    data = r.json()
    rutas = data.get("lista_rutas") or []
    log.info("get_rutas_de_estacion(%s, troncal=%s) → %d rutas | raw keys: %s", estacion_codigo, es_troncal, len(rutas), list(data.keys()))
    return rutas


async def get_llegadas(paradero_codigo: str) -> list[dict]:
    """getLlegadas() (zonal/SITP) -> List<LlegadasItem>"""
    client = await _get_client()
    r = await client.post(
        f"{config.BODEGA_BASE}/paradero/buses",
        json={"paradero": paradero_codigo},
        headers=_bodega_headers(),
    )
    r.raise_for_status()
    data = r.json() or []
    log.info("get_llegadas(%s) → %d items", paradero_codigo, len(data))
    return data


async def get_bus_brt_time(
    estacion_codigo: str, ruta_codigo: str, id_ruta: str, nombre_ruta: str, distancia: str = "100"
) -> list[dict]:
    """getBusBrtTime() (troncal, posición en vivo) -> List<BusBrtTime>"""
    client = await _get_client()
    r = await client.post(
        f"{config.BODEGA_BASE}/getServicios",
        json={
            "estacion": estacion_codigo,
            "ruta": ruta_codigo,
            "idRuta": id_ruta,
            "Nombre": nombre_ruta,
            "Distancia": distancia,
        },
        headers=_bodega_headers(),
    )
    r.raise_for_status()
    return r.json() or []


async def get_programacion(paradero_codigo: str, ruta_codigo: str, id_ruta: str, nombre_ruta: str) -> list[dict]:
    """getProgramacion() (troncal, horario teórico de respaldo) -> List<Programacion>"""
    client = await _get_client()
    r = await client.post(
        f"{config.BODEGA_BASE}/consultar_programacion",
        json={"paradero": paradero_codigo, "ruta": ruta_codigo, "idRuta": id_ruta, "nombre": nombre_ruta},
        headers=_bodega_headers(),
    )
    r.raise_for_status()
    return r.json() or []
