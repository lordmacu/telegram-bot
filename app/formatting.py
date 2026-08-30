def format_llegadas(estacion_nombre: str, llegadas: list[dict]) -> str:
    if not llegadas:
        return f"No hay buses reportados en este momento para *{estacion_nombre}*."
    lines = [f"🚏 *{estacion_nombre}*", ""]
    for item in llegadas:
        ruta = item.get("ruta_extraida") or "?"
        destino = item.get("destino_limpio") or ""
        tiempo = item.get("labeltiempo") or "?"
        distancia = item.get("distancia") or ""
        line = f"🚌 *{ruta}* → {destino}\n   ⏱ {tiempo}"
        if distancia:
            line += f" · 📍 {distancia}"
        lines.append(line)
    return "\n".join(lines)


def format_bus_brt_times(estacion_nombre: str, ruta_nombre: str, buses: list[dict]) -> str:
    if not buses:
        return f"No hay buses en vivo para *{ruta_nombre}* en *{estacion_nombre}* en este momento."
    lines = [f"🚏 *{estacion_nombre}* — 🚌 *{ruta_nombre}*", ""]
    for b in buses:
        tiempo = b.get("labeltiempo") or b.get("time") or "?"
        distancia = b.get("distancia")
        placa = b.get("vehicleid") or ""
        accesible = str(b.get("acessiblidad") or "").strip().lower() in ("si", "true", "1", "s")
        line = f"⏱ {tiempo}"
        if isinstance(distancia, (int, float)):
            line += f" · 📍 {distancia:.0f} m"
        if placa:
            line += f" · 🚍 {placa}"
        if accesible:
            line += " · ♿"
        lines.append(line)
    return "\n".join(lines)


def format_programacion(estacion_nombre: str, ruta_nombre: str, programacion: list[dict]) -> str:
    if not programacion:
        return f"No hay programación disponible para *{ruta_nombre}* en *{estacion_nombre}* en este momento."
    lines = [f"🚏 *{estacion_nombre}* — 🚌 *{ruta_nombre}* (horario programado)", ""]
    for p in programacion:
        tiempo = p.get("tiempo_estimado") or "?"
        lines.append(f"⏱ {tiempo}")
    return "\n".join(lines)
