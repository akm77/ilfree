import asyncio
import logging

import aiohttp
from aiogram import Bot, Dispatcher
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.contrib.fsm_storage.redis import RedisStorage2
from gspread_asyncio import AsyncioGspreadClientManager

from tgbot.config import load_config
from tgbot.filters.admin import AdminFilter
from tgbot.handlers.groups.service_messages import register_service_handlers
from tgbot.handlers.private.admin import register_admin
from tgbot.handlers.private.echo import register_echo
from tgbot.handlers.private.manage_outline_server import register_manage_server
from tgbot.handlers.private.user import register_user
from tgbot.middlewares.dbmiddleware import DBMiddleware
from tgbot.models.base import create_db_session
from tgbot.models.telegram_object import user_read, user_create

logger = logging.getLogger(__name__)


def register_all_middlewares(dp):
    dp.setup_middleware(DBMiddleware())


def register_all_filters(dp):
    dp.filters_factory.bind(AdminFilter)


def register_all_handlers(dp):
    register_admin(dp)
    register_user(dp)
    register_service_handlers(dp)
    register_manage_server(dp)
    register_echo(dp)


async def main():
    logging.basicConfig(
        level=logging.INFO,
        format=u'%(filename)s:%(lineno)d #%(levelname)-8s [%(asctime)s] - %(name)s - %(message)s',
    )
    logger.info("Starting bot")
    config = load_config(".env")

    storage = RedisStorage2() if config.tg_bot.use_redis else MemoryStorage()
    bot = Bot(token=config.tg_bot.token, parse_mode='HTML')
    dp = Dispatcher(bot, storage=storage)

    bot['config'] = config
    bot['http_session']: aiohttp.ClientSession = aiohttp.ClientSession()
    bot['db_session'] = await create_db_session(config)
    db_bot_user = await user_read(bot['db_session'], id=bot.id)
    if not db_bot_user:
        bot_user = await bot.me
        await user_create(bot['db_session'],
                          id=bot_user.id,
                          is_bot=bot_user.is_bot,
                          first_name=bot_user.first_name,
                          last_name=bot_user.last_name,
                          username=bot_user.username,
                          mention=bot_user.mention,
                          lang_code=bot_user.language_code,
                          role='user'
                          )

    google_client_manager: AsyncioGspreadClientManager = AsyncioGspreadClientManager(
        config.misc.scoped_credentials
    )
    bot['google_client_manager'] = google_client_manager
    register_all_middlewares(dp)
    register_all_filters(dp)
    register_all_handlers(dp)

    # start
    try:
        await dp.start_polling()
    finally:
        await dp.storage.close()
        await dp.storage.wait_closed()
        await bot.session.close()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.error("Bot stopped!")
