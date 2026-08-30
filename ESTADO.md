# Estado del proyecto — Bot de Telegram TransMilenio/SITP

Fecha: 2026-08-30

## Objetivo

Bot de Telegram que, usando las APIs internas de la app TransMi/TransMilenio
(mapeadas en `../TransMilenio_API.postman_collection.json` a partir del APK
decompilado), le diga al usuario qué bus está llegando a un paradero, con
tiempo de llegada y otros datos, identificando el paradero por texto, código
o ubicación GPS.

## Qué hay hecho

### Código del bot (`app/`)

- **`config.py`** — variables de entorno (`BOT_TOKEN`, `APP_VERSION`), UUID de
  "dispositivo" persistido en `data/device_uuid.txt`, headers y bases de URL.
- **`tm_client.py`** — llamadas HTTP a las 2 APIs que necesita el bot:
  - Rutas (`api.buscador-rutas.transmilenio.gov.co`): `searchStations`,
    `getRutasDeUnaEstacion` (troncal/zonal).
  - Bodega (`tmsa-transmiapp-shvpc.uc.r.appspot.com`): `getLlegadas`,
    `getBusBrtTime`, `getProgramacion`.
- **`stations.py`** — cache local del listado completo de estaciones/paraderos
  (`searchStations` con `search` vacío, igual que hace la app), búsqueda por
  texto, búsqueda por código exacto, y **cercanía por GPS** (haversine sobre
  el campo `coordenada` que trae cada estación).
- **`handlers.py`** — flujo completo en Telegram: `/start`, `/codigo`,
  mensajes de texto libre, ubicación compartida, botones inline para elegir
  estación/ruta cuando hay ambigüedad.
- **`formatting.py`** — formateo de las respuestas a mensajes legibles.
- **`Dockerfile` / `docker-compose.yml`** — listos para build (Python 3.12,
  healthcheck implícito por `restart: unless-stopped`, volumen `bot_data`
  para persistir el cache y el UUID entre reinicios).

### Validado contra las APIs reales (no supuesto, se probó)

- `searchStations` responde con **7510** estaciones/paraderos reales
  (177 troncales, 7333 zonales), incluyendo `coordenada` (lat,lng) — la
  búsqueda por texto y por GPS funcionan tal cual están escritas.
- Se encontró y corrigió un bug real: `RouteItem` (respuesta de
  `getRutasDeUnaEstacion`) serializa el ID de ruta en la key JSON `"id"`,
  no `"idRuta"` como decía el nombre del campo Java. `handlers.py` ya quedó
  corregido (`ruta.get("id")`).
- Los endpoints **estáticos** de Bodega funcionan solo con headers
  `uuid` + `version` (sin nada más): `puntos_recarga`, `puntos_personalizacion`
  devuelven 200 con datos reales.

### Bot de Telegram

- Ya existe: `@transmitest_bot` (creado con @BotFather). Token en mi poder,
  **no está commiteado** (`.env.example` queda vacío, se pasa por variable
  de entorno en Coolify).

### Repo local

- `git init` hecho en esta carpeta, identidad configurada como `lordmacu`
  (según CLAUDE.md), primer commit ya creado con todo el código.

## Qué falta / qué está bloqueado

### 1. ~~Bloqueante principal: los endpoints de "tiempo real" de Bodega dan 401~~ — RESUELTO

**Causa encontrada (2026-08-30):** Bodega requiere un header adicional
`Appid` con un valor estático que la app obtiene de **Firebase Realtime
Database** (no Remote Config) en el nodo `z/Android`, campo `Bodega`
(formato `x;NombreHeader;ValorHeader`).

Proceso de descubrimiento:
1. Se leyó `UtilsFirebase.cargaFireBase()`: usa `FirebaseDatabase` en
   `z/Android`, no `FirebaseRemoteConfig`. El intento anterior con Remote
   Config era la pista equivocada.
2. Firebase Anonymous Auth (`accounts:signUp`) requiere headers
   `X-Android-Package: com.nexura.transmilenio` y
   `X-Android-Cert: 4463555E3C2D4CF4C5F84796EF8FBF0DA0B4E26B` (del APK).
3. Con el `idToken` anónimo se leyó `z/Android.json` del database
   `https://transmilenio-transmiapp.firebaseio.com`.
4. El campo `Bodega` devolvió el valor que al parsearlo con `;` da:
   - `BODEGA_EXTRA_HEADER_NAME=Appid`
   - `BODEGA_EXTRA_HEADER_VALUE=9a2c3b48f0c24ae9bfba38e94f27c3ea`
5. Con ese header, `POST /paradero/buses` respondió **HTTP 200** desde Mac
   (IP no colombiana) — confirma que **no había geo-bloqueo**, solo faltaba
   el header.

**Estado actual:** `.env` local tiene los valores correctos. `.env.example`
actualizado con `BODEGA_EXTRA_HEADER_NAME=Appid` (valor sin commitear).
El bot está listo para arrancar y usar todos los endpoints de Bodega.

### 2. Deploy a Coolify — no arrancado todavía

- La VM `coolify` (OrbStack, Ubuntu arm64, `192.168.139.138`) tiene Coolify
  4.3.14 corriendo con ~40 apps, dashboard en `http://192.168.139.138:8000`.
  Confirmado reachable, pero **no se creó ningún proyecto/recurso nuevo ahí
  todavía** — se decidió esperar a tener el repo en GitHub primero.
- **`gh auth` sigue roto** (todas las cuentas con token inválido: `lordmacu`,
  `cristiangarcia-source`, `cristiannyxn`). Hace falta correr
  `gh auth login -h github.com -w` para poder crear el repo remoto y
  pushear. Sin esto no se puede seguir con la ruta "GitHub + auto-redeploy"
  que elegiste.
- Una vez que haya login: crear repo en GitHub bajo `lordmacu`, push, y en
  Coolify crear un proyecto nuevo → recurso "Public/Private Repository"
  apuntando a ese repo → variable de entorno `BOT_TOKEN` cargada en la UI de
  Coolify (nunca en el repo) → deploy.

### 3. Cosas menores pendientes

- `fetch_remote_config.sh` es un script de investigación (no parte del
  bot); sacarlo del commit final antes de subir a GitHub, o dejarlo en un
  commit aparte claramente marcado como "herramienta de diagnóstico".
- Falta decidir si el bot arranca solo con lo que sí funciona hoy (búsqueda
  de estaciones, rutas por estación, `puntos_recarga`/`puntos_personalizacion`,
  planeador de viaje OTP) mientras se resuelve el punto 1, o si se espera a
  tener las llegadas en vivo antes de deployar nada.

## Referencias en el código decompilado

No se copió el código decompilado a esta carpeta: son ~140MB de fuente
propietaria de Nexura/TransMilenio (más AndroidX/Firebase/Huawei HMS)
recuperada por ingeniería inversa del APK, y este repo se va a pushear a
GitHub — redistribuir eso públicamente es un problema de derechos de autor
distinto a tenerlo localmente para analizarlo. El código decompilado sigue
donde ya estaba, junto a esta carpeta:

- `../decompiled_jadx/sources/` — código Java reconstruido (jadx).
- `../decompiled_apktool/` — recursos, `AndroidManifest.xml`, smali (apktool).
- `../TransMilenio_API.postman_collection.json` — mapeo completo de las APIs
  (27 endpoints, todos los clientes), con ejemplos de cada request.

Rutas relativas a `decompiled_jadx/sources/com/nexura/transmilenio/` salvo
que se indique lo contrario.

| Pieza del bot | Se basa en | Qué mirar ahí |
|---|---|---|
| `tm_client.search_stations()` | `Client/APIServiceInterface.java:123-124` | firma `searchStations()`, endpoint `loader.php` |
| `tm_client.get_rutas_de_estacion()` | `Client/APIServiceInterface.java:87-88,90-91` | `getRutasDeUnaEstacion()` / `getRutasDeUnaEstacionZonal()` |
| `tm_client.get_llegadas()` | `Client/APIServiceInterface.java:48-49` | `getLlegadas()`, endpoint `paradero/buses` |
| `tm_client.get_bus_brt_time()` | `Client/APIServiceInterface.java:39-40` | `getBusBrtTime()`, endpoint `getServicios` |
| `tm_client.get_programacion()` | `Client/APIServiceInterface.java:72-73` | `getProgramacion()`, endpoint `consultar_programacion` |
| Headers `uuid`/`version` (Rutas) | `Client/ApiClient.java:25,28-38` | `BASE_URL` + interceptor OkHttp |
| Headers `uuid`/`version` + header extra opcional (Bodega) | `Client/ApiClientBodega.java:15,18-38` | `BASE_URL` + interceptor condicional |
| Body de `getLlegadas` (`paradero`) | `Activity/RoutesActivity.java:73-77` | construcción real del `JsonObject` antes de llamar |
| Body de `getProgramacion` (`paradero,ruta,idRuta,nombre`) | `Activity/MapLocationBusBRTTimeActivity.java:166-173` y `Activity/MapBusesActivity.java:128-139` | dos call-sites, mismos campos |
| Body de `getBusBrtTime` (`estacion,ruta,idRuta,Nombre,Distancia="100"`) | `Activity/MapLocationBusBRTTimeActivity.java:418-426` y `Activity/MapBusesActivity.java:380-392` | `Distancia` siempre fija en `"100"` |
| `EstacionesAppListModel.listParadas` | `Models/EstacionesAppListModel.java:9-21` | key JSON que envuelve el array |
| Campos de estación (`codigo,nombre,direccion,tipo_parada,troncal,coordenada,color`) | `Models/EstacionesAppModel.java:9-16` | modelo Realm, sin `@SerializedName` (nombres literales) |
| `RutasListModel.lista_rutas` | `Models/RutasListModel.java:8-27` | key JSON del array de rutas |
| **Bug encontrado y corregido**: ID de ruta es `"id"`, no `"idRuta"` | `Models/RouteItem.java:28-30` | `@c("id") private String idRuta;` — el nombre del campo Java engaña, la key JSON real es `id` |
| Campos de `getLlegadas` (`ruta_extraida,color_ruta,distancia,ruta_sae,destino_limpio,labelparadero,labeltiempo`) | `Models/LlegadasItem.java:8-36` | usado en `formatting.format_llegadas()` |
| Campos de `getBusBrtTime` (`acessiblidad,distancia,etiqueta,labeltiempo,lasttime,latitud,longitud,plan,time,vehicleid`) | `Models/Bodega/BusBrtTime.java:8-48` | usado en `formatting.format_bus_brt_times()` |
| Campos de `getProgramacion` (`estacion_parada,hora_teor_segundos,nodo,nombre_parada,ruta,ruta_extraida,tiempo_estimado`) | `Models/Bodega/Programacion.java:7-35` | usado en `formatting.format_programacion()` |
| Versión de la app enviada en header `version` | `BuildConfig.java:9` | `VERSION_NAME = "2.9.7"` |
| Por qué existe el header extra de Bodega (investigación del 401) | `Activity/SplashActivity.java:24-26`, `Utils/UtilsFirebase.java:24-28`, `Utils/Utils.java:231-233` | `getSavedConfigInPreferences()`, key `"Bodega"` de Remote Config, `getSplit(";")` |
| Credenciales Firebase usadas solo para la investigación del Remote Config (no viven en el bot) | `../decompiled_apktool/res/values/strings.xml` | `google_api_key`, `google_app_id`, `project_id`, `gcm_defaultSenderId` |

## Resumen ejecutivo

El bot está **funcionalmente completo y probado** para todo lo que no
depende del backend "Bodega" en tiempo real. Lo que falta para que cumpla
la promesa original ("qué bus está llegando y con qué tiempo") es un solo
bloqueante técnico —por qué Bodega devuelve 401— que necesita una prueba
desde una red/dispositivo colombiano para poder seguir. El deploy a Coolify
está listo para ejecutarse en cuanto se resuelva el login de GitHub.
