import logging

from sqlalchemy import DateTime, Column, MetaData, func, event, types
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.future import Engine
from sqlalchemy.orm import declarative_base, sessionmaker

from tgbot.config import Config

logger = logging.getLogger(__name__)

meta = MetaData(naming_convention={
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
})

Base = declarative_base(metadata=meta)

MAX_SQLITE_INT = 2 ** 63 - 1


class VeryBigInt(types.TypeDecorator):
    impl = types.Integer
    cache_ok = False

    def process_bind_param(self, value, dialect):
        return hex(value) if value > MAX_SQLITE_INT else value

    def process_result_value(self, value, dialect):
        return int(value, 16) if isinstance(value, str) else value


class TimedBaseModel(Base):
    __abstract__ = True

    __mapper_args__ = {"eager_defaults": True}

    created_at = Column(DateTime(True), server_default=func.datetime('now', 'localtime'))
    updated_at = Column(
        DateTime(True), default=func.datetime('now', 'localtime'),
        onupdate=func.datetime('now', 'localtime'),
        server_default=func.datetime('now', 'localtime'))


async def create_db_session(config: Config) -> sessionmaker:
    # dialect[+driver]: // user: password @ host / dbname[?key = value..],

    if config.db.dialect.startswith('sqlite'):
        database_uri = f"{config.db.dialect}:///{config.db.database}"
    else:
        database_uri = f"{config.db.dialect}://{config.db.user}:{config.db.password}" \
                       f"@{config.db.host}/{config.db.database}"

    engine = create_async_engine(
        database_uri,
        echo=config.db.echo,
        future=True
    )

    if config.db.dialect.startswith('sqlite'):
        @event.listens_for(Engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    async with engine.begin() as conn:
        # await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    Session: sessionmaker = sessionmaker(
        engine,
        expire_on_commit=False,
        class_=AsyncSession
    )
    logger.info(f"Database {database_uri} session successfully configured")
    return Session
