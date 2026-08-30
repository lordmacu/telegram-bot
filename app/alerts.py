import asyncio
import json
import logging

from . import config, formatting, tm_client

log = logging.getLogger(__name__)

ALERTS_PATH = config.DATA_DIR / "alerts.json"


def _load() -> dict:
    if ALERTS_PATH.exists():
        try:
            return json.loads(ALERTS_PATH.read_text())
        except Exception:
            return {}
    return {}


def _save(alerts: dict) -> None:
    ALERTS_PATH.write_text(json.dumps(alerts, ensure_ascii=False))


def set_alert(chat_id: int, context: dict) -> None:
    alerts = _load()
    alerts[str(chat_id)] = context
    _save(alerts)


def clear_alert(chat_id: int) -> bool:
    alerts = _load()
    if str(chat_id) in alerts:
        del alerts[str(chat_id)]
        _save(alerts)
        return True
    return False


def get_alert(chat_id: int) -> dict | None:
    return _load().get(str(chat_id))


async def alert_loop(bot) -> None:
    await asyncio.sleep(10)  # dar tiempo al bot a arrancar
    while True:
        await asyncio.sleep(300)  # 5 minutos
        alerts = _load()
        for chat_id_str, ctx in list(alerts.items()):
            chat_id = int(chat_id_str)
            try:
                if ctx.get("es_troncal"):
                    buses = await tm_client.get_bus_brt_time(
                        ctx["paradero"], ctx["ruta_codigo"], ctx["id_ruta"], ctx["nombre_ruta"]
                    )
                    text = "🔔 *Actualización cada 5 min:*\n\n" + formatting.format_bus_brt_times(
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
                    text = "🔔 *Actualización cada 5 min:*\n\n" + formatting.format_llegadas(
                        ctx["estacion_nombre"], filtradas
                    )
                await bot.send_message(chat_id, text)
            except Exception:
                log.exception("Error enviando alerta a %s", chat_id)
