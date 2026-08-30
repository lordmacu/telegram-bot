import logging

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from . import alerts, formatting, stations, tm_client

router = Router()
log = logging.getLogger(__name__)

SESSIONS: dict[int, dict] = {}

_AVISAR_KB = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🔔 Avisar cada 5 min", callback_data="av")]
])


def _station_button_text(s: dict) -> str:
    nombre = s.get("nombre") or s.get("codigo") or "?"
    if "_distancia_m" in s:
        return f"{nombre} · {s['_distancia_m']} m"
    return nombre


def _stations_keyboard(matches: list[dict]) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text=_station_button_text(s), callback_data=f"st:{i}")]
        for i, s in enumerate(matches)
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def _rutas_keyboard(rutas: list[dict]) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text=r.get("nombre") or r.get("codigo") or "?", callback_data=f"rt:{i}")]
        for i, r in enumerate(rutas)
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer(
        "🚌 *Bot de llegadas TransMilenio/SITP*\n\n"
        "Enviame el nombre de una estación o paradero (ej. `Portal Norte`), "
        "un código exacto con `/codigo <código>`, o compartí tu ubicación 📍 "
        "para ver los paraderos más cercanos.\n\n"
        "Usa /cancelar para detener los avisos automáticos."
    )


@router.message(Command("codigo"))
async def cmd_codigo(message: Message) -> None:
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Usá: `/codigo 12345`")
        return
    all_stations = await stations.get_all_stations()
    match = stations.find_by_codigo(all_stations, parts[1])
    if not match:
        await message.answer("No encontré ninguna estación/paradero con ese código.")
        return
    await _resolve_station(message, match)


@router.message(Command("cancelar"))
async def cmd_cancelar(message: Message) -> None:
    if alerts.clear_alert(message.chat.id):
        await message.answer("✅ Avisos cancelados.")
    else:
        await message.answer("No tenías ningún aviso activo.")


@router.message(F.location)
async def on_location(message: Message) -> None:
    all_stations = await stations.get_all_stations()
    nearest = stations.nearest_stations(all_stations, message.location.latitude, message.location.longitude)
    if not nearest:
        await message.answer("No pude encontrar paraderos cercanos en este momento.")
        return
    SESSIONS[message.chat.id] = {"stations": nearest}
    await message.answer("Paraderos más cercanos:", reply_markup=_stations_keyboard(nearest))


@router.message(F.text & ~F.text.startswith("/"))
async def on_text(message: Message) -> None:
    all_stations = await stations.get_all_stations()
    matches = stations.search_by_text(all_stations, message.text)
    if not matches:
        await message.answer(
            "No encontré ninguna estación/paradero con ese nombre. "
            "Probá con otro texto o compartí tu ubicación 📍."
        )
        return
    if len(matches) == 1:
        await _resolve_station(message, matches[0])
        return
    SESSIONS[message.chat.id] = {"stations": matches}
    await message.answer(f"Encontré {len(matches)} coincidencias, elegí una:", reply_markup=_stations_keyboard(matches))


@router.callback_query(F.data.startswith("st:"))
async def on_station_selected(callback: CallbackQuery) -> None:
    session = SESSIONS.setdefault(callback.message.chat.id, {})
    idx = int(callback.data.split(":", 1)[1])
    matches = session.get("stations") or []
    if idx >= len(matches):
        await callback.answer("Esa opción ya expiró, buscá de nuevo.", show_alert=True)
        return
    await callback.answer()
    await _resolve_station(callback.message, matches[idx], session=session)


@router.callback_query(F.data.startswith("rt:"))
async def on_route_selected(callback: CallbackQuery) -> None:
    session = SESSIONS.setdefault(callback.message.chat.id, {})
    idx = int(callback.data.split(":", 1)[1])
    rutas = session.get("rutas") or []
    estacion = session.get("estacion")
    es_troncal = session.get("es_troncal", True)

    if idx >= len(rutas) or not estacion:
        await callback.answer("Esa opción ya expiró, buscá de nuevo.", show_alert=True)
        return
    await callback.answer()

    ruta = rutas[idx]
    alerta_ctx = {
        "paradero": estacion.get("codigo"),
        "estacion_nombre": estacion.get("nombre") or "",
        "ruta_codigo": ruta.get("codigo"),
        "id_ruta": ruta.get("id"),
        "nombre_ruta": ruta.get("nombre") or "",
        "es_troncal": es_troncal,
    }
    session["alerta"] = alerta_ctx

    if es_troncal:
        try:
            buses = await tm_client.get_bus_brt_time(
                estacion.get("codigo"), ruta.get("codigo"), ruta.get("id"), ruta.get("nombre")
            )
        except Exception:
            log.exception("Fallo consultando getServicios")
            buses = []

        if buses:
            await callback.message.answer(
                formatting.format_bus_brt_times(estacion.get("nombre") or "", ruta.get("nombre") or "", buses),
                reply_markup=_AVISAR_KB,
            )
            return

        try:
            programacion = await tm_client.get_programacion(
                estacion.get("codigo"), ruta.get("codigo"), ruta.get("id"), ruta.get("nombre")
            )
        except Exception:
            log.exception("Fallo consultando consultar_programacion")
            programacion = []

        await callback.message.answer(
            formatting.format_programacion(estacion.get("nombre") or "", ruta.get("nombre") or "", programacion),
            reply_markup=_AVISAR_KB,
        )

    else:
        # Zonal: getLlegadas y filtrar por ruta
        try:
            llegadas = await tm_client.get_llegadas(estacion.get("codigo"))
        except Exception:
            log.exception("Fallo consultando llegadas zonales")
            await callback.message.answer("No pude consultar las llegadas, intentá de nuevo en un momento.")
            return

        ruta_nombre = ruta.get("nombre") or ruta.get("codigo") or ""
        filtradas = [
            l for l in llegadas
            if ruta_nombre and (
                ruta_nombre in (l.get("ruta_extraida") or "")
                or ruta_nombre in (l.get("ruta_sae") or "")
                or (l.get("ruta_extraida") or "") in ruta_nombre
            )
        ] or llegadas  # si no filtra nada, mostrar todas

        await callback.message.answer(
            formatting.format_llegadas(estacion.get("nombre") or "", filtradas),
            reply_markup=_AVISAR_KB,
        )


@router.callback_query(F.data == "av")
async def on_avisar(callback: CallbackQuery) -> None:
    session = SESSIONS.get(callback.message.chat.id, {})
    ctx = session.get("alerta")
    if not ctx:
        await callback.answer("Ya no tengo el contexto, buscá de nuevo.", show_alert=True)
        return
    alerts.set_alert(callback.message.chat.id, ctx)
    await callback.answer()
    await callback.message.answer(
        f"🔔 Te voy a avisar cada 5 min sobre *{ctx['nombre_ruta'] or 'este paradero'}* "
        f"en *{ctx['estacion_nombre']}*.\n"
        "Usá /cancelar para detener los avisos."
    )


async def _resolve_station(message: Message, station: dict, session: dict | None = None) -> None:
    chat_id = message.chat.id
    session = session if session is not None else SESSIONS.setdefault(chat_id, {})
    es_troncal = stations.es_troncal(station)

    if es_troncal:
        try:
            rutas = await tm_client.get_rutas_de_estacion(station.get("codigo"), es_troncal=True)
        except Exception:
            log.exception("Fallo consultando rutas de estación troncal")
            await message.answer("No pude consultar las rutas de esta estación, intentá de nuevo en un momento.")
            return
        if not rutas:
            await message.answer(f"No hay rutas registradas para *{station.get('nombre')}* en este momento.")
            return
        session["rutas"] = rutas
        session["estacion"] = station
        session["es_troncal"] = True
        session["llegadas_cache"] = None
        await message.answer(
            f"🚏 *{station.get('nombre')}* — elegí una ruta:",
            reply_markup=_rutas_keyboard(rutas),
        )
    else:
        # Zonal: obtener llegadas en tiempo real y extraer rutas de ahí
        try:
            llegadas = await tm_client.get_llegadas(station.get("codigo"))
        except Exception:
            log.exception("Fallo consultando llegadas zonales")
            await message.answer("No pude consultar las llegadas de este paradero, intentá de nuevo en un momento.")
            return

        if not llegadas:
            await message.answer(f"No hay buses llegando a *{station.get('nombre')}* en este momento.")
            return

        # Extraer rutas únicas de las llegadas
        seen: set = set()
        rutas = []
        for l in llegadas:
            nombre = l.get("ruta_extraida") or l.get("ruta_sae") or ""
            if nombre and nombre not in seen:
                seen.add(nombre)
                rutas.append({"nombre": nombre, "codigo": nombre, "id": nombre})

        session["rutas"] = rutas
        session["estacion"] = station
        session["es_troncal"] = False
        session["llegadas_cache"] = llegadas  # reusar sin otra llamada a la API

        if len(rutas) == 1:
            # Una sola ruta — ir directo a mostrar llegadas
            session["alerta"] = {
                "paradero": station.get("codigo"),
                "estacion_nombre": station.get("nombre") or "",
                "ruta_codigo": rutas[0]["codigo"],
                "id_ruta": rutas[0]["id"],
                "nombre_ruta": rutas[0]["nombre"],
                "es_troncal": False,
            }
            await message.answer(
                formatting.format_llegadas(station.get("nombre") or "", llegadas),
                reply_markup=_AVISAR_KB,
            )
        else:
            await message.answer(
                f"🚏 *{station.get('nombre')}* — elegí una ruta:",
                reply_markup=_rutas_keyboard(rutas),
            )
