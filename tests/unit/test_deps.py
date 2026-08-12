from app.config import settings
from app.deps import get_db


def test_get_db_returns_configured_database_name():
    db = get_db()

    assert db.name == settings.MONGODB_DB_NAME
