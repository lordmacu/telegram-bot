def _tiempo_label(tiempo: str) -> str:
    t = tiempo.strip().lower()
    if t in ("ahora", "llegando", "en estación"):
        return f"🟢 ¡Llegando ahora!"
    return f"🕐 Llega en {tiempo}"


def format_llegadas(estacion_nombre: str, llegadas: list[dict]) -> str:
    if not llegadas:
        return f"No hay buses reportados en este momento para *{estacion_nombre}*."
    lines = [f"📍 *{estacion_nombre}*", ""]
    for item in llegadas:
        ruta = str(item.get("ruta_extraida") or "?")
        destino = item.get("destino_limpio") or ""
        tiempo = item.get("labeltiempo") or "?"
        distancia = item.get("distancia") or ""
        extras = f"  ·  📏 {distancia}" if distancia else ""
        lines.append(f"🚌 *{ruta}*  {destino}")
        lines.append(f"{_tiempo_label(tiempo)}{extras}")
        lines.append("")
    if lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines)


def format_bus_brt_times(estacion_nombre: str, ruta_nombre: str, buses: list[dict]) -> str:
    if not buses:
        return f"No hay buses en vivo para *{ruta_nombre}* en *{estacion_nombre}* en este momento."
    lines = [f"📍 *{estacion_nombre}*", f"🚌 *{ruta_nombre}*", ""]
    for b in buses:
        tiempo = b.get("labeltiempo") or b.get("time") or "?"
        distancia = b.get("distancia")
        placa = b.get("vehicleid") or ""
        accesible = str(b.get("acessiblidad") or "").strip().lower() in ("si", "true", "1", "s")
        extras = []
        if isinstance(distancia, (int, float)):
            extras.append(f"📏 {distancia:.0f} m")
        if placa:
            extras.append(f"🚍 {placa}")
        if accesible:
            extras.append("♿")
        suffix = "  ·  " + "  ·  ".join(extras) if extras else ""
        lines.append(f"{_tiempo_label(tiempo)}{suffix}")
    return "\n".join(lines)


def format_programacion(estacion_nombre: str, ruta_nombre: str, programacion: list[dict]) -> str:
    if not programacion:
        return f"No hay programación disponible para *{ruta_nombre}* en *{estacion_nombre}* en este momento."
    lines = [f"🚏 *{estacion_nombre}* — 🚌 *{ruta_nombre}* (horario programado)", ""]
    for p in programacion:
        tiempo = p.get("tiempo_estimado") or "?"
        lines.append(f"⏱ {tiempo}")
    return "\n".join(lines)
