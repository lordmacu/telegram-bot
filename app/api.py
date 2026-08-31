from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from . import stations as stations_mod, tm_client

app = FastAPI(title="TransMilenio API Proxy", docs_url="/api/docs")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/stations")
async def get_stations(search: str = Query(default="")):
    all_st = await stations_mod.get_all_stations()
    if search.strip():
        result = stations_mod.search_by_text(all_st, search, limit=20)
    else:
        result = all_st
    return result


@app.get("/api/stations/nearest")
async def get_nearest(lat: float, lon: float, limit: int = 8, radius_m: float = 0):
    all_st = await stations_mod.get_all_stations()
    if radius_m > 0:
        return stations_mod.nearest_within_radius(all_st, lat, lon, radius_m)
    return stations_mod.nearest_stations(all_st, lat, lon, top_n=limit)


@app.get("/api/llegadas/{codigo}")
async def get_llegadas(codigo: str):
    try:
        return await tm_client.get_llegadas(codigo)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@app.get("/api/rutas/{codigo}")
async def get_rutas(codigo: str, troncal: bool = False):
    try:
        return await tm_client.get_rutas_de_estacion(codigo, es_troncal=troncal)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@app.get("/api/rutas")
async def search_rutas(q: str = Query(..., min_length=1)):
    try:
        return await tm_client.search_rutas(q)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@app.get("/api/brt/{estacion}/{ruta_codigo}")
async def get_brt(estacion: str, ruta_codigo: str, id_ruta: str = "", nombre: str = ""):
    try:
        return await tm_client.get_bus_brt_time(estacion, ruta_codigo, id_ruta, nombre)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@app.get("/health")
async def health():
    return {"status": "ok"}
