import logging

from aiogram import types, Dispatcher
from aiogram.types import ChatMember
from sqlalchemy.orm import sessionmaker

from tgbot.models.telegram_object import chat_member_read, chat_member_create, chat_member_delete

logger = logging.getLogger(__name__)


async def new_chat_member(message: types.Message):
    Session: sessionmaker = message.bot.get('db_session')

    logger.info("New chat member(s) in chat %s", message.chat.title)
    for telegram_user in message.new_chat_members:
        db_chat_member = await chat_member_read(Session, chat_id=message.chat.id, user_id=telegram_user.id)
        telegram_chat_member: ChatMember = await message.chat.get_member(telegram_user.id)

        if not db_chat_member:
            db_chat_member = await chat_member_create(Session,
                                                      chat_id=message.chat.id,
                                                      user_id=telegram_user.id,
                                                      status=telegram_chat_member.status)
            if db_chat_member:
                logger.info("New chat member %s in chat %s added to database chat_members table",
                            telegram_user.mention, message.chat.title)
        else:
            logger.info("New chat member %s in chat %s already exist in database chat_members table",
                        telegram_user.mention, message.chat.title)


async def left_chat_member(message: types.Message):
    Session: sessionmaker = message.bot.get('db_session')

    logger.info("Chat member %s left chat %s", message.left_chat_member.mention, message.chat.title)
    result = await chat_member_delete(Session,
                                      chat_id=message.chat.id,
                                      user_id=message.left_chat_member.id)
    if result:
        logger.info("Chat member %s from chat %s deleted from database chat_members table",
                    message.left_chat_member.mention, message.chat.title)


def register_service_handlers(dp: Dispatcher):
    dp.register_message_handler(new_chat_member,
                                content_types=types.ContentTypes.NEW_CHAT_MEMBERS)
    dp.register_message_handler(left_chat_member,
                                content_types=types.ContentTypes.LEFT_CHAT_MEMBER)
