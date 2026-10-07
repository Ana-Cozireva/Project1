import logging
import time

from sqlalchemy import create_engine, event, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

_is_sqlite = settings.database_url.startswith("sqlite")
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    connect_args={"check_same_thread": False} if _is_sqlite else {},
)


if _is_sqlite:  # в SQLite внешние ключи по умолчанию выключены (используется в тестах)

    @event.listens_for(engine, "connect")
    def _enable_sqlite_fk(dbapi_connection, _):
        dbapi_connection.execute("PRAGMA foreign_keys=ON")


SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def wait_for_db() -> None:
    """Повторные попытки подключения при старте (ToR, п. 10.1): БД может подняться позже backend."""
    for attempt in range(1, settings.db_connect_retries + 1):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("Database is ready")
            return
        except OperationalError:
            logger.warning(
                "Database not ready (attempt %s/%s)", attempt, settings.db_connect_retries
            )
            time.sleep(settings.db_connect_delay_sec)
    raise RuntimeError("Could not connect to the database")
