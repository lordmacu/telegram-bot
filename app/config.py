import os
import pathlib
import uuid

DATA_DIR = pathlib.Path(os.getenv("DATA_DIR", "/app/data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

BOT_TOKEN = os.environ["BOT_TOKEN"]

APP_VERSION = os.getenv("APP_VERSION", "2.9.7")

_UUID_FILE = DATA_DIR / "device_uuid.txt"


def _load_or_create_uuid() -> str:
    if _UUID_FILE.exists():
        value = _UUID_FILE.read_text().strip()
        if value:
            return value
    value = str(uuid.uuid4())
    _UUID_FILE.write_text(value)
    return value


APP_UUID = os.getenv("APP_UUID") or _load_or_create_uuid()

# Header extra opcional para ApiClientBodega (ver Client/ApiClientBodega.java).
# En el APK llega vía Firebase/Huawei Remote Config; en la práctica el propio
# código lo trata como opcional, así que arranca vacío y se puede setear si
# se confirma que hace falta.
BODEGA_EXTRA_HEADER_NAME = os.getenv("BODEGA_EXTRA_HEADER_NAME", "")
BODEGA_EXTRA_HEADER_VALUE = os.getenv("BODEGA_EXTRA_HEADER_VALUE", "")

RUTAS_BASE = "https://api.buscador-rutas.transmilenio.gov.co"
BODEGA_BASE = "https://tmsa-transmiapp-shvpc.uc.r.appspot.com"

STATIONS_CACHE_PATH = DATA_DIR / "stations_cache.json"
STATIONS_CACHE_TTL_SECONDS = int(os.getenv("STATIONS_CACHE_TTL_SECONDS", str(6 * 3600)))

HTTP_TIMEOUT_SECONDS = 30.0
