import asyncio
import json
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from . import config, formatting, tm_client

log = logging.getLogger(__name__)
SUBS_PATH = config.DATA_DIR / "subscriptions.json"
BOGOTA = ZoneInfo("America/Bogota")

# Horarios disponibles para elegir (HH:MM)
HORAS_DISPONIBLES = [
    ["05:00", "05:30", "06:00", "06:30"],
    ["07:00", "07:30", "08:00", "08:30"],
    ["09:00", "12:00", "17:00", "18:00"],
]


def _load() -> dict:
    if SUBS_PATH.exists():
        try:
            return json.loads(SUBS_PATH.read_text())
        except Exception:
            return {}
    return {}


def _save(subs: dict) -> None:
    SUBS_PATH.write_text(json.dumps(subs, ensure_ascii=False))


def set_subscription(chat_id: int, context: dict) -> None:
    subs = _load()
    subs[str(chat_id)] = context
    _save(subs)


def clear_subscription(chat_id: int) -> bool:
    subs = _load()
    if str(chat_id) in subs:
        del subs[str(chat_id)]
        _save(subs)
        return True
    return False


def get_subscription(chat_id: int) -> dict | None:
    return _load().get(str(chat_id))


async def subscription_loop(bot) -> None:
    await asyncio.sleep(15)
    sent_today: set[str] = set()
    while True:
        await asyncio.sleep(60)
        now = datetime.now(BOGOTA)
        current_slot = now.strftime("%H:%M")
        today = now.strftime("%Y-%m-%d")

        # Limpiar registro del día anterior al cambiar de día
        if current_slot == "00:01":
            sent_today.clear()

        subs = _load()
        for chat_id_str, ctx in list(subs.items()):
            if ctx.get("hora") != current_slot:
                continue
            key = f"{chat_id_str}:{today}:{current_slot}"
            if key in sent_today:
                continue
            sent_today.add(key)
            chat_id = int(chat_id_str)
            hora = ctx.get("hora", "")
            try:
                if ctx.get("es_troncal"):
                    buses = await tm_client.get_bus_brt_time(
                        ctx["paradero"], ctx["ruta_codigo"], ctx["id_ruta"], ctx["nombre_ruta"]
                    )
                    text = f"📅 *Recordatorio diario {hora}*\n\n" + formatting.format_bus_brt_times(
                        ctx["estacion_nombre"], ctx["nombre_ruta"], buses
                    )
                else:
                    llegadas = await tm_client.get_llegadas(ctx["paradero"])
                    ruta_nombre = ctx.get("nombre_ruta") or ""
                    if ruta_nombre:
                        filtradas = [
                            l for l in llegadas
                            if ruta_nombre in str(l.get("ruta_extraida") or "")
                            or ruta_nombre in str(l.get("ruta_sae") or "")
                            or str(l.get("ruta_extraida") or "") in ruta_nombre
                        ] or llegadas
                    else:
                        filtradas = llegadas
                    text = f"📅 *Recordatorio diario {hora}*\n\n" + formatting.format_llegadas(
                        ctx["estacion_nombre"], filtradas
                    )
                await bot.send_message(chat_id, text)
                log.info("Suscripción diaria enviada a %s a las %s", chat_id, hora)
            except Exception:
                log.exception("Error enviando suscripción diaria a %s", chat_id)
