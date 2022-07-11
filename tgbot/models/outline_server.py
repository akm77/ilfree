import logging
from ipaddress import ip_address
from typing import Optional, List, Union

from aiohttp import ClientSession
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, types, insert, select, update, delete, \
    ForeignKeyConstraint
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.sql import expression

from tgbot.models.base import Base
from tgbot.services.outline_server_api import OutlineVPN, OutlineKey

logger = logging.getLogger(__name__)


class IPAddressType(types.TypeDecorator):
    impl = types.Integer
    cache_ok = True

    def process_bind_param(self, value, dialect):
        return int(value) if value else None

    def process_result_value(self, value, dialect):
        return ip_address(value) if value else None


class OutlineServer(Base):
    __tablename__ = "outline_server"

    ip = Column(IPAddressType, primary_key=True)
    url = Column(String(length=256), )
    name = Column(String(length=128), server_default="my server")
    is_active = Column(Boolean, server_default=expression.true())
    keys = relationship(
        "ServerKey", cascade="all, delete-orphan", backref="server", lazy="joined"
    )


class ServerKey(Base):
    __tablename__ = "server_key"

    server_ip = Column(IPAddressType, ForeignKey("outline_server.ip", ondelete="RESTRICT", onupdate="CASCADE"),
                       primary_key=True)
    key_id = Column(Integer, primary_key=True)
    name = Column(String(length=256), server_default="",  index=True)
    password = Column(String(length=256), nullable=True)
    port = Column(Integer, default=0)
    method = Column(String(length=256))
    access_url = Column(String)
    used_bytes = Column(Integer, default=0)


class UserKey(Base):
    __tablename__ = "user_key"
    __table_args__ = (
        ForeignKeyConstraint(
            ('server_ip', 'key_id'),
            ['server_key.server_ip', 'server_key.key_id'],
            ondelete="RESTRICT", onupdate="CASCADE"
        ),
    )

    server_ip = Column(IPAddressType, primary_key=True)
    key_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, default=0)


async def server_create(Session: sessionmaker, **kwargs) -> Optional[OutlineServer]:
    """
    Create a new OutlineServer object in database. kwargs may have the following attributes:

        *ip  ip_address from ipaddress library IP address of the server

        *url String(length=128) Outline server manage url

        *name    String(length=256)	Human readable server name

        *is_active   Boolean	Server active and in use

    :param Session: DB session object
    :param kwargs: Contain dictionary of OutlineServer attributes
    :return: OutlineServer object on success, None on failure
    """
    if not kwargs.get('ip', None) or not kwargs.get('url', None):
        return None

    async with Session() as session:
        statement = insert(OutlineServer).values(**kwargs)
        await session.execute(statement)
        await session.commit()
    server: OutlineServer = await server_read(Session, ip=kwargs['ip'])
    return server


async def server_read(Session: sessionmaker, **kwargs) -> Optional[OutlineServer]:
    """
    Read OutlineServer object from database. kwargs must have the following attributes:

        *ip  ip_address from ipaddress library IP address of the server

    :param Session: DB session object
    :param kwargs: Contain dictionary of OutlineServer attributes
    :return: OutlineServer object on success, None on failure
    """
    if not kwargs.get('ip', None):
        return None

    async with Session() as session:
        statement = select(OutlineServer).where(OutlineServer.ip == kwargs['ip'])
        result = await session.execute(statement)
        return result.scalar()


async def server_update(Session: sessionmaker, **kwargs) -> Optional[OutlineServer]:
    """
    Update OutlineServer object in database. kwargs may have the following attributes:

        *primary_key_ip  ip_address from ipaddress library IP address of the server

        *ip  ip_address from ipaddress library IP address of the server

        *url String(length=128) Outline server manage url

        *name    String(length=256)	Human readable server name

        *is_active   Boolean	Server active and in use

    :param Session: DB session object
    :param kwargs: Contain dictionary of OutlineServer attributes
    :return: OutlineServer object on success, None on failure
    """
    if not kwargs.get('primary_key_ip', None):
        return None
    primary_key_ip = kwargs.pop('primary_key_ip')
    async with Session() as session:
        statement = update(OutlineServer).where(OutlineServer.ip == primary_key_ip).values(**kwargs)
        await session.execute(statement)
        await session.commit()
    server: OutlineServer = await server_read(Session, ip=kwargs.get('ip', primary_key_ip))
    return server


async def server_delete(Session: sessionmaker, **kwargs) -> bool:
    """
    Delete OutlineServer object from database. kwargs must have the following attributes:

        *ip  ip_address from ipaddress library IP address of the server

    :param Session: DB session object
    :param kwargs: Contain dictionary of OutlineServer attributes
    :return: True on success, False on failure
    """
    if not kwargs.get('ip', None):
        return False

    async with Session() as session:
        statement = delete(OutlineServer).where(OutlineServer.ip == kwargs['ip'])
        result = await session.execute(statement)
        await session.commit()
        return True if result.rowcount else False


async def servers_list(Session: sessionmaker, **kwargs) -> List[OutlineServer]:
    """
    Return list of OutlineServer object from database. kwargs may have the following attributes:

        *mode may have one of three value 'all', 'active', 'inactive'. When pass 'all' is_active attribute ignored.
                When pass 'active' method will return rows with is_active==True.
                When pass 'nonactive' method will return rows with is_active==False.

    :param Session: DB session object
    :param kwargs: Contain dictionary of OutlineServer attributes
    :return: List of vpn servers
    """
    mode = 'all' if not kwargs.get('mode', None) else kwargs['mode']
    statement = select(OutlineServer)
    if mode == 'active':
        statement = statement.where(OutlineServer.is_active is True)
    elif mode == 'inactive':
        statement = statement.where(OutlineServer.is_active is False)
    async with Session() as session:
        result = await session.execute(statement)
        return result.unique().scalars().all()


async def server_key_create(Session: sessionmaker,
                            aiohttp_session: Optional[ClientSession],
                            **kwargs) -> Optional[ServerKey]:
    """
    Create Outline server key on outline server and then in database. kwargs must have the following attributes:

        *server_ip  ip_address from ipaddress library IP address of the server.
        *key_name name of the key

    :param Session: DB session object
    :param aiohttp_session: aiohttp session
    :param kwargs: Contain dictionary of ServerKey attributes
    :return: ServerKey object on success, None on failure
    """
    if not kwargs.get('server_ip', None):
        return None
    vpn = OutlineVPN(session=aiohttp_session, logger=logger)
    async with Session() as session:
        server = await server_read(Session, ip=kwargs['server_ip'])
        if not server:
            return
        vpn.api_url = server.url
        key: OutlineKey = await vpn.create_key()
        if key and kwargs.get('key_name', None):
            if await vpn.rename_key(key.key_id, kwargs['key_name']):
                key = OutlineKey(key_id=key.key_id,
                                 name=kwargs['key_name'],
                                 password=key.password,
                                 port=key.port,
                                 method=key.method,
                                 access_url=key.access_url,
                                 used_bytes=key.used_bytes)
        statement = insert(ServerKey).values(server_ip=kwargs['server_ip'], key_id=key.key_id,
                                             name=key.name, password=key.password,
                                             port=key.port, method=key.method,
                                             access_url=key.access_url, used_bytes=key.used_bytes)
        await session.execute(statement)
        await session.commit()
    server_key: ServerKey = await server_key_read(Session, server_ip=kwargs['server_ip'], key_id=key.key_id)
    return server_key


async def server_key_read(Session: sessionmaker, **kwargs) -> Optional[ServerKey]:
    """
    Read Outline server key from database. kwargs must have the following attributes:

        *server_ip  ip_address from ipaddress library IP address of the server.
        *key_id key id

    :param Session: DB session object
    :param kwargs: Contain dictionary of ServerKey attributes
    :return: ServerKey object on success, None on failure
    """
    if not kwargs.get('server_ip', None) or kwargs.get('key_id', None) is None:
        return None
    async with Session() as session:
        statement = select(ServerKey).where(ServerKey.server_ip == kwargs['server_ip'],
                                            ServerKey.key_id == kwargs['key_id'])
        result = await session.execute(statement)
        return result.scalar()


async def server_key_update(Session: sessionmaker, **kwargs) -> Optional[ServerKey]:
    """
    Update Outline server key from database. kwargs must have the following attributes:

        *server_ip  ip_address from ipaddress library IP address of the server.
        *key_id key id

    :param Session: DB session object
    :param kwargs: Contain dictionary of ServerKey attributes
    :return: ServerKey object on success, None on failure
    """
    if not kwargs.get('server_ip', None) or kwargs.get('key_id', None) is None:
        return None
    server_ip = kwargs.pop('server_ip')
    key_id = kwargs.pop('key_id')
    async with Session() as session:
        statement = update(ServerKey).where(ServerKey.server_ip == server_ip,
                                            ServerKey.key_id == key_id).values(**kwargs)
        await session.execute(statement)
        await session.commit()
    server_key: ServerKey = await server_key_read(Session, server_ip=server_ip, key_id=key_id)
    return server_key


async def server_key_delete(Session: sessionmaker,
                            aiohttp_session: Optional[ClientSession],
                            **kwargs) -> bool:
    """
    Create Outline server key on outline server and then in database. kwargs must have the following attributes:

        *server_ip  ip_address from ipaddress library IP address of the server.
        *key_name name of the key

    :param Session: DB session object
    :param aiohttp_session: aiohttp session
    :param kwargs: Contain dictionary of ServerKey attributes
    :return: True on success, False on failure
    """
    if not kwargs.get('server_ip', None) and not kwargs.get('key_id', None):
        return False
    vpn = OutlineVPN(session=aiohttp_session, logger=logger)
    async with Session() as session:
        server = await server_read(Session, ip=kwargs['server_ip'])
        if not server:
            return False
        vpn.api_url = server.url
        if not await vpn.delete_key(key_id=kwargs['key_id']):
            return False
        statement = delete(ServerKey).where(ServerKey.server_ip == kwargs['server_ip'],
                                            ServerKey.key_id == kwargs['key_id'])
        result = await session.execute(statement)
        await session.commit()
        return True if result.rowcount else False


async def server_key_list(Session: sessionmaker, **kwargs) -> List[ServerKey]:
    """
    Return list of ServerKey object from database. kwargs may have the following attributes:

        *server_ip  ip_address from ipaddress library IP address of the server.

    :param Session: DB session object
    :param kwargs: Contain dictionary of OutlineServer attributes
    :return: List of vpn servers
    """
    if not kwargs.get('server_ip', None):
        return []
    statement = select(ServerKey).where(ServerKey.server_ip == kwargs['server_ip']).order_by(ServerKey.name)
    async with Session() as session:
        result = await session.execute(statement)
        return result.unique().scalars().all()


async def server_key_sync(Session: sessionmaker,
                          aiohttp_session: Optional[ClientSession],
                          **kwargs) -> Union[bool, Optional[List[ServerKey]]]:
    """
    Sync ServerKey objects from database with Outline VPN Server. kwargs may have the following attributes:

        *server_ip  ip_address from ipaddress library IP address of the server.

    :param Session: DB session object
    :param aiohttp_session: aiohttp session
    :param kwargs: Contain dictionary of OutlineServer attributes
    :return: True on success, False on failure
    """
    if not kwargs.get('server_ip', None):
        return False
    server_ip = kwargs['server_ip']
    server = await server_read(Session, ip=server_ip)
    if not server:
        return False
    try:
        vpn = OutlineVPN(api_url=server.url, session=aiohttp_session, logger=logger)
        vpn_keys = await vpn.get_keys()
        key_list = await server_key_list(Session, server_ip=server_ip)
        db_keys = [OutlineKey(key_id=key.key_id,
                              name=key.name,
                              password=key.password,
                              port=key.port,
                              method=key.method,
                              access_url=key.access_url,
                              used_bytes=key.used_bytes) for key in key_list]
        db_key_id_list = [key.key_id for key in db_keys]
        vpn_key_id_list = [key.key_id for key in vpn_keys]
        # In case if we add key in OutlineManager
        insert_values = [{'server_ip': server_ip,
                          'key_id': key.key_id,
                          'name': key.name,
                          'password': key.password,
                          'port': key.port,
                          'method': key.method,
                          'access_url': key.access_url,
                          'used_bytes': key.used_bytes} for key in
                         set(filter(lambda k: k.key_id not in db_key_id_list, vpn_keys))]

        # In case if we delete key in OutlineManager
        keys_to_delete = set(filter(lambda k: k.key_id not in vpn_key_id_list, db_keys))
        # In case if we add need update key from OutlineVPN
        keys_to_update = set(vpn_keys) - set(keys_to_delete) - set(db_keys)
        # keys_not_in_db = set(vpn_keys) - set(db_keys)
        # In case if we remove key in OutlineManager
        async with Session() as session:
            if len(insert_values):
                statement = insert(ServerKey).values(insert_values)
                await session.execute(statement)

            for key in keys_to_delete:
                statement = delete(ServerKey).where(ServerKey.server_ip == server_ip,
                                                    ServerKey.key_id == key.key_id)
                result = await session.execute(statement)
            for key in keys_to_update:
                statement = update(ServerKey).where(ServerKey.server_ip == server_ip,
                                                    ServerKey.key_id == key.key_id
                                                    ).values({'name': key.name,
                                                              'password': key.password,
                                                              'port': key.port,
                                                              'method': key.method,
                                                              'access_url': key.access_url,
                                                              'used_bytes': key.used_bytes})
                await session.execute(statement)

            await session.commit()
            logger.info("Sync successful!")
    except Exception as e:
        logger.error("Error occurred during syncing. Error: %r", e)
    finally:
        return await server_key_list(Session, **kwargs)
