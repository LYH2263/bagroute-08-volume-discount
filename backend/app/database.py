from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from app.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


# 早期库表缺少的列：create_all 不会给已存在的表补列，这里幂等补齐
_PENDING_COLUMNS = {
    "delivery_routes": [
        ("volume_discount_enabled", "BOOLEAN DEFAULT FALSE NOT NULL"),
        ("volume_discount_ratio", "FLOAT DEFAULT 1.0 NOT NULL"),
    ],
    "pack_bags": [
        ("volume_discount_applied", "BOOLEAN DEFAULT FALSE NOT NULL"),
        ("volume_limit_l", "FLOAT DEFAULT 0.0 NOT NULL"),
    ],
}


def ensure_columns() -> None:
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    with engine.begin() as conn:
        for table, columns in _PENDING_COLUMNS.items():
            if table not in existing_tables:
                continue
            present = {col["name"] for col in inspector.get_columns(table)}
            for name, ddl_type in columns:
                if name not in present:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {ddl_type}"))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
