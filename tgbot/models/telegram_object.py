from typing import Optional

from sqlalchemy import Column, Integer, Boolean, ForeignKey, String, insert, update, delete
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.future import select
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.sql import expression

from tgbot.models.base import TimedBaseModel


class User(TimedBaseModel):
    __tablename__ = "user"

    id = Column(Integer, primary_key=True)
    is_bot = Column(Boolean, server_default=expression.false())
    first_name = Column(String(length=128))
    last_name = Column(String(length=128), nullable=True)
    username = Column(String(length=128), nullable=True)
    mention = Column(String(length=128), nullable=True)
    lang_code = Column(String(length=5), default='ru_RU')
    role = Column(String(length=32), default='user')
    is_superuser = Column(Boolean, server_default=expression.false())

    user_chats = relationship(
        "ChatMember", cascade="all, delete-orphan", backref="user_chat", lazy="joined"
    )
    chats = association_proxy("user_chats", "chat")

    def __str__(self):
        return f"<id={self.id} first name={self.first_name}>"


class UserRelatedMixin:
    user_id = Column(
        Integer,
        ForeignKey(f"{User.__tablename__}.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=False,
    )


class Chat(TimedBaseModel):
    __tablename__ = "chat"

    id = Column(Integer, primary_key=True)
    type = Column(String(length=32))
    title = Column(String(length=128), nullable=True)
    username = Column(String(length=128), nullable=True)
    chat_users = relationship(
        "ChatMember", cascade="all, delete-orphan", backref="chat_user", lazy="joined"
    )
    users = association_proxy("chat_users", "user")


class ChatRelatedMixin:
    __abstract__ = True

    chat_id = Column(
        Integer,
        ForeignKey(f"{Chat.__tablename__}.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=False,
    )


class ChatMember(TimedBaseModel):
    __tablename__ = "chat_member"
    chat_id = Column(Integer, ForeignKey("chat.id", ondelete="CASCADE", onupdate="CASCADE"), primary_key=True)
    user_id = Column(Integer, ForeignKey("user.id", ondelete="CASCADE", onupdate="CASCADE"), primary_key=True)
    status = Column(String(length=32))

    chat = relationship("Chat", viewonly=True, lazy="joined")
    user = relationship("User", viewonly=True, lazy="joined")

    def __init__(self, chat, user, status='member'):
        self.chat = chat
        self.status = status


async def user_create(Session: sessionmaker, **kwargs) -> Optional[User]:
    """
    Create a new telegram User object in database. kwargs may have the following attributes:

    *id	Integer	Mandatory. Unique identifier for this user or bot.
            This number may have more than 32 significant bits and some programming languages may have
            difficulty/silent defects in interpreting it. But it has at most 52 significant bits,
            so a 64-bit integer or double-precision float type are safe for storing this identifier.

    *is_bot	Boolean	True, if this user is a bot

    *first_name	String	Mandatory. User's or bot's first name

    *last_name	String	Optional. User's or bot's last name

    *username	String	Optional. User's or bot's username

    *language_code	String	Optional. IETF language tag of the user's language .

    :param Session: DB session object
    :param kwargs: Contain dictionary of User attributes
    :return: User object on success, None on failure
    """
    if not kwargs.get('id', None) or not kwargs.get('first_name', None):
        return None

    async with Session() as session:
        statement = insert(User).values(**kwargs)
        await session.execute(statement)
        await session.commit()
    user: User = await user_read(Session, id=kwargs['id'])
    return user


async def user_read(Session: sessionmaker, **kwargs) -> Optional[User]:
    """
    Read telegram User object from database. kwargs must have the following attribute:
        *id	Integer	Unique identifier for this user or bot.
                        This number may have more than 32 significant bits and some programming languages may have
                        difficulty/silent defects in interpreting it. But it has at most 52 significant bits,
                        so a 64-bit integer or double-precision float type are safe for storing this identifier..
    :param Session: DB session object
    :param kwargs: Contain dictionary of User attributes
    :return: User object on success, None on failure
    """
    if not kwargs.get('id', None):
        return None

    async with Session() as session:
        statement = select(User).where(User.id == kwargs['id'])
        result = await session.execute(statement)
        return result.scalar()


async def user_update(Session: sessionmaker, **kwargs) -> Optional[User]:
    """
    Update telegram User object in database. kwargs may have the following attributes:

    *id	Integer	Mandatory. Unique identifier for this user or bot.
            This number may have more than 32 significant bits and some programming languages may have
            difficulty/silent defects in interpreting it. But it has at most 52 significant bits,
            so a 64-bit integer or double-precision float type are safe for storing this identifier.

    *is_bot	Boolean	True, if this user is a bot

    *first_name	String	Mandatory. User's or bot's first name

    *last_name	String	Optional. User's or bot's last name

    *username	String	Optional. User's or bot's username

    *language_code	String	Optional. IETF language tag of the user's language..
    :param Session: DB session object
    :param kwargs:  Contain dictionary of User attributes
    :return: User object on success, None on failure
    """
    if not kwargs.get('id', None):
        return None

    async with Session() as session:
        statement = update(User).where(User.id == kwargs['id']).values(**kwargs)
        await session.execute(statement)
        await session.commit()
    user: User = await user_read(Session, id=kwargs['id'])
    return user


async def user_delete(Session: sessionmaker, **kwargs) -> bool:
    """
    Delete telegram User object from database. kwargs must have the following attribute:
        *id	Integer	Unique identifier for this user or bot.
                        This number may have more than 32 significant bits and some programming languages may have
                        difficulty/silent defects in interpreting it. But it has at most 52 significant bits,
                        so a 64-bit integer or double-precision float type are safe for storing this identifier..

    :param Session: DB session object
    :param kwargs:  Contain dictionary of User attributes
    :return: True on success, False on failure
    """
    if not kwargs.get('id', None):
        return False

    async with Session() as session:
        statement = delete(User).where(User.id == kwargs['id'])
        result = await session.execute(statement)
        await session.commit()
        return True if result.rowcount else False


async def chat_create(Session: sessionmaker, **kwargs) -> Optional[Chat]:
    """
    Create a new telegram Chat object in database. kwargs may have the following attributes:
        *id	Integer	Mandatory. Unique identifier for this chat.
                        This number may have more than 32 significant bits and some programming languages
                        may have difficulty/silent defects in interpreting it. But it has at most 52 significant bits,
                        so a signed 64-bit integer or double-precision float type are safe for storing this identifier.
        *type	String	Mandatory. Type of chat, can be either “private”, “group”, “supergroup” or “channel”.

        *title	String	Optional. Title, for supergroups, channels and group chats.

        *username	String	Optional. Username, for private chats, supergroups and channels if available..

    :param Session: DB session object
    :param kwargs: Contain dictionary of Chat attributes
    :return: Chat object on success, None on failure
    """
    if not kwargs.get('id', None) or not kwargs.get('type', None):
        return None

    async with Session() as session:
        statement = insert(Chat).values(**kwargs)
        result = await session.execute(statement)
        await session.commit()
        chat: Chat = await chat_read(Session, id=kwargs['id'])
        return chat


async def chat_read(Session: sessionmaker, **kwargs) -> Optional[Chat]:
    """
    Read telegram Chat object from database. kwargs must have the following attributes:
        *id	Integer	Mandatory. Unique identifier for this chat.
                        This number may have more than 32 significant bits and some programming languages
                        may have difficulty/silent defects in interpreting it. But it has at most 52 significant bits,
                        so a signed 64-bit integer or double-precision float type are safe for storing this identifier..

    :param Session: DB session object
    :param kwargs: Contain dictionary of Chat attributes
    :return: Chat object on success, None on failure
    """
    if not kwargs.get('id', None):
        return None

    async with Session() as session:
        statement = select(Chat).where(Chat.id == kwargs['id'])
        result = await session.execute(statement)
        chat = result.scalar()
        return chat


async def chat_update(Session: sessionmaker, **kwargs) -> Optional[Chat]:
    """
    Update telegram Chat object in database. kwargs may have the following attributes:
        *id	Integer	Mandatory. Unique identifier for this chat.
                        This number may have more than 32 significant bits and some programming languages
                        may have difficulty/silent defects in interpreting it. But it has at most 52 significant bits,
                        so a signed 64-bit integer or double-precision float type are safe for storing this identifier.
        *type	String	Mandatory. Type of chat, can be either “private”, “group”, “supergroup” or “channel”.

        *title	String	Optional. Title, for supergroups, channels and group chats.

        *username	String	Optional. Username, for private chats, supergroups and channels if available..

    :param Session: DB session object
    :param kwargs: Contain dictionary of Chat attributes
    :return: Chat object on success, None on failure
    """
    if not kwargs.get('id', None):
        return None

    async with Session() as session:
        statement = update(Chat).where(Chat.id == kwargs['id']).values(**kwargs)
        result = await session.execute(statement)
        await session.commit()
        chat: Chat = await chat_read(Session, id=kwargs['id'])
        return chat


async def chat_delete(Session: sessionmaker, **kwargs) -> bool:
    """
    Delete telegram Chat object from database. kwargs must have the following attributes:
        *id	Integer	Mandatory. Unique identifier for this chat.
                        This number may have more than 32 significant bits and some programming languages
                        may have difficulty/silent defects in interpreting it. But it has at most 52 significant bits,
                        so a signed 64-bit integer or double-precision float type are safe for storing this identifier..

    :param Session: DB session object
    :param kwargs: Contain dictionary of Chat attributes
    :return: True on success, False on failure
    """
    if not kwargs.get('id', None):
        return False

    async with Session() as session:
        statement = delete(Chat).where(Chat.id == kwargs['id'])
        result = await session.execute(statement)
        await session.commit()

        return True if result.rowcount else False


async def chat_member_create(Session: sessionmaker, **kwargs) -> Optional[tuple]:
    """
    Create a new telegram ChatMember object in database. kwargs may have the following attributes:
        *user_id	Integer	Mandatory. Unique identifier for this user or bot.
                            This number may have more than 32 significant bits and some programming languages may have
                            difficulty/silent defects in interpreting it. But it has at most 52 significant bits,
                            so a 64-bit integer or double-precision float type are safe for storing this identifier.
        *chat_id	Integer	Mandatory. Unique identifier for this user or bot.
                            This number may have more than 32 significant bits and some programming languages may have
                            difficulty/silent defects in interpreting it. But it has at most 52 significant bits,
                            so a 64-bit integer or double-precision float type are safe for storing this identifier.
        *status	String	Mandatory. The member's status in the chat,
                            can be either “creator”, “administrator”, “member”, “restricted”, “left” or “kicked”
    :param Session: DB session object
    :param kwargs: Contain dictionary of ChatMember attributes
    :return: ChatMember object on success, None on failure
    """

    if not (kwargs.get('chat_id', None) and kwargs.get('user_id', None)) or not (kwargs.get('status', None)):
        return None

    async with Session() as session:
        statement = insert(ChatMember).values(**kwargs)
        result = await session.execute(statement)
        await session.commit()
        chat_member: ChatMember = await chat_member_read(Session, chat_id=kwargs['chat_id'],
                                                         user_id=kwargs['user_id'])
        return chat_member


async def chat_member_read(Session: sessionmaker, **kwargs) -> Optional[ChatMember]:
    """
    Read telegram ChatMember object from database. kwargs must have the following attributes:
        *user_id	Integer	Mandatory. Unique identifier for this user or bot.
                            This number may have more than 32 significant bits and some programming languages may have
                            difficulty/silent defects in interpreting it. But it has at most 52 significant bits,
                            so a 64-bit integer or double-precision float type are safe for storing this identifier.
        *chat_id	Integer	Mandatory. Unique identifier for this user or bot.
                            This number may have more than 32 significant bits and some programming languages may have
                            difficulty/silent defects in interpreting it. But it has at most 52 significant bits,
                            so a 64-bit integer or double-precision float type are safe for storing this identifier.
    :param Session: DB session object
    :param kwargs: Contain dictionary of ChatMember attributes
    :return: ChatMember object on success, None on failure
    """
    if not (kwargs.get('chat_id', None) and kwargs.get('user_id', None)):
        return None

    async with Session() as session:
        statement = select(ChatMember).where(ChatMember.chat_id == kwargs['chat_id'],
                                             ChatMember.user_id == kwargs['user_id'])
        result = await session.execute(statement)
        chat_member: ChatMember = result.scalar()
        return chat_member


async def chat_member_update(Session: sessionmaker, **kwargs) -> Optional[ChatMember]:
    """
    Update telegram ChatMember object in database. kwargs may have the following attributes:
        *user_id	Integer	Mandatory. Unique identifier for this user or bot.
                            This number may have more than 32 significant bits and some programming languages may have
                            difficulty/silent defects in interpreting it. But it has at most 52 significant bits,
                            so a 64-bit integer or double-precision float type are safe for storing this identifier.
        *chat_id	Integer	Mandatory. Unique identifier for this user or bot.
                            This number may have more than 32 significant bits and some programming languages may have
                            difficulty/silent defects in interpreting it. But it has at most 52 significant bits,
                            so a 64-bit integer or double-precision float type are safe for storing this identifier.
        *status	String	Mandatory. The member's status in the chat,
                            can be either “creator”, “administrator”, “member”, “restricted”, “left” or “kicked”
    :param Session: DB session object
    :param kwargs: Contain dictionary of ChatMember attributes
    :return: ChatMember object on success, None on failure
    """
    if not (kwargs.get('chat_id', None) and kwargs.get('user_id', None)):
        return None

    async with Session() as session:
        statement = update(ChatMember).where(ChatMember.chat_id == kwargs['chat_id'],
                                             ChatMember.user_id == kwargs['user_id']).values(**kwargs)
        result = await session.execute(statement)
        await session.commit()
        chat_member: ChatMember = await chat_member_read(Session, chat_id=kwargs['chat_id'],
                                                         user_id=kwargs['user_id'])
        return chat_member


async def chat_member_delete(Session: sessionmaker, **kwargs) -> bool:
    """
    Delete telegram ChatMember object from database. kwargs must have the following attributes:
        *user_id	Integer	Mandatory. Unique identifier for this user or bot.
                            This number may have more than 32 significant bits and some programming languages may have
                            difficulty/silent defects in interpreting it. But it has at most 52 significant bits,
                            so a 64-bit integer or double-precision float type are safe for storing this identifier.
        *chat_id	Integer	Mandatory. Unique identifier for this user or bot.
                            This number may have more than 32 significant bits and some programming languages may have
                            difficulty/silent defects in interpreting it. But it has at most 52 significant bits,
                            so a 64-bit integer or double-precision float type are safe for storing this identifier.
    :param Session: DB session object
    :param kwargs: Contain dictionary of ChatMember attributes
    :return: True on success, False on failure
    """
    if not (kwargs.get('chat_id', None) and kwargs.get('user_id', None)):
        return False

    async with Session() as session:
        statement = delete(ChatMember).where(ChatMember.chat_id == kwargs['chat_id'],
                                             ChatMember.user_id == kwargs['user_id'])
        result = await session.execute(statement)
        await session.commit()

        return True if result.rowcount else False
