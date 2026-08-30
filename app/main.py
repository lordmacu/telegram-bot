import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from . import alerts, config, stations, subscriptions
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

    asyncio.create_task(alerts.alert_loop(bot))
    asyncio.create_task(subscriptions.subscription_loop(bot))
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
