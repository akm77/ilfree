import logging

from aiogram import types
from aiogram.dispatcher.middlewares import LifetimeControllerMiddleware
from sqlalchemy.orm import sessionmaker

from tgbot.models.telegram_object import user_read, user_create, user_update, chat_read, chat_create, chat_update, \
    chat_member_read, chat_member_create, chat_member_update, chat_member_delete

logger = logging.getLogger(__name__)


class DBMiddleware(LifetimeControllerMiddleware):
    skip_patterns = ["error", "update"]

    async def pre_process(self, obj, data, *args):

        if not isinstance(obj, types.Message):
            return

        Session: sessionmaker = obj.bot.get('db_session')

        telegram_user: types.User = obj.from_user
        telegram_chat: types.Chat = obj.chat

        db_user = await user_read(Session, id=telegram_user.id)
        if not db_user:
            db_user = await user_create(Session,
                                        id=telegram_user.id,
                                        is_bot=telegram_user.is_bot,
                                        first_name=telegram_user.first_name,
                                        last_name=telegram_user.last_name,
                                        username=telegram_user.username,
                                        mention=telegram_user.mention,
                                        lang_code=telegram_user.language_code,
                                        role='user')
        else:
            db_user = await user_update(Session,
                                        id=telegram_user.id,
                                        is_bot=telegram_user.is_bot,
                                        first_name=telegram_user.first_name,
                                        last_name=telegram_user.last_name,
                                        username=telegram_user.username,
                                        mention=telegram_user.mention,
                                        lang_code=telegram_user.language_code)

        db_chat_member = None
        db_chat = None
        if telegram_chat.type != str(types.ChatType.PRIVATE):
            telegram_chat_member = None
            bot_chat_member = None
            try:
                telegram_chat_member = await telegram_chat.get_member(telegram_user.id)
            except Exception as e:
                logger.info("Middleware: Error while issue User in Chat for %s (%i) - %r",
                            telegram_chat.title, telegram_chat.id, e)
            try:
                bot_chat_member = await telegram_chat.get_member(obj.bot.id)
            except Exception as e:
                logger.info("Middleware: Error while issue Bot in Chat for %s (%i) - %r",
                            telegram_chat.title, obj.bot.id, e)

            db_chat = await chat_read(Session, id=telegram_chat.id)
            if not db_chat:
                db_chat = await chat_create(Session,
                                            id=telegram_chat.id,
                                            title=telegram_chat.title,
                                            username=telegram_chat.username,
                                            type=telegram_chat.type)
            else:
                db_chat = await chat_update(Session,
                                            id=telegram_chat.id,
                                            title=telegram_chat.title,
                                            username=telegram_chat.username,
                                            type=telegram_chat.type)

            db_chat_member = await chat_member_read(Session,
                                                    chat_id=telegram_chat.id,
                                                    user_id=telegram_user.id)
            if not db_chat_member and telegram_chat_member:
                db_chat_member = await chat_member_create(Session,
                                                          chat_id=telegram_chat.id,
                                                          user_id=telegram_user.id,
                                                          status=telegram_chat_member.status)
            elif db_chat_member and not telegram_chat_member:
                await chat_member_delete(Session,
                                         chat_id=telegram_chat.id,
                                         user_id=telegram_user.id)
                db_chat_member = await chat_member_read(Session,
                                                        chat_id=telegram_chat.id,
                                                        user_id=telegram_user.id)
            else:
                db_chat_member = await chat_member_update(Session,
                                                          chat_id=telegram_chat.id,
                                                          user_id=telegram_user.id,
                                                          status=telegram_chat_member.status)

            db_bot_chat_member = await chat_member_read(Session,
                                                        chat_id=telegram_chat.id,
                                                        user_id=obj.bot.id)
            if not db_bot_chat_member and bot_chat_member:
                db_bot_chat_member = await chat_member_create(Session,
                                                              chat_id=telegram_chat.id,
                                                              user_id=obj.bot.id,
                                                              status=bot_chat_member.status)
            elif db_bot_chat_member and not bot_chat_member:
                await chat_member_delete(Session,
                                         chat_id=telegram_chat.id,
                                         user_id=obj.bot.id)
            else:
                db_bot_chat_member = await chat_member_update(Session,
                                                              chat_id=telegram_chat.id,
                                                              user_id=obj.bot.id,
                                                              status=bot_chat_member.status)

        data['user'] = db_user
        data['chat'] = db_chat
        data['chat_member'] = db_chat_member
