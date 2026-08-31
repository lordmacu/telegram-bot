import asyncio
import logging

import uvicorn
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from . import alerts, config, stations, subscriptions
from .api import app as fastapi_app
from .handlers import router


async def main() -> None:
    logging.basicConfig(level=logging.INFO)

    bot = Bot(token=config.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
    dp = Dispatcher()
    dp.include_router(router)

    logging.info("Precargando cache de estaciones...")
    try:
        await stations.get_all_stations()
    except Exception:
        logging.exception("No se pudo precargar el cache de estaciones al inicio, se reintentará on-demand")

    api_server = uvicorn.Server(
        uvicorn.Config(fastapi_app, host="0.0.0.0", port=8080, log_level="warning")
    )

    await asyncio.gather(
        api_server.serve(),
        dp.start_polling(bot),
        alerts.alert_loop(bot),
        subscriptions.subscription_loop(bot),
    )


if __name__ == "__main__":
    asyncio.run(main())
