from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.database import database_access, engine


def database_is_available() -> bool:
    try:
        with database_access():
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
    except SQLAlchemyError:
        return False

    return True
