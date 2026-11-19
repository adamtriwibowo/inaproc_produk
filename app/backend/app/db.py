from contextlib import contextmanager
from sqlmodel import Session, SQLModel, create_engine
from . import config

_args = {"check_same_thread": False} if config.DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(config.DATABASE_URL, connect_args=_args)


def _migrate():
    """create_all tidak menambah kolom pada tabel yang sudah ada: tambahkan kolom baru secara aman."""
    from sqlalchemy import inspect, text
    insp = inspect(engine)
    with engine.begin() as conn:
        for table in SQLModel.metadata.sorted_tables:
            if not insp.has_table(table.name):
                continue
            have = {c["name"] for c in insp.get_columns(table.name)}
            for col in table.columns:
                if col.name in have:
                    continue
                typ = col.type.compile(engine.dialect)
                default = ""
                d = col.default.arg if col.default is not None and getattr(col.default, "is_scalar", False) else None
                if isinstance(d, str):
                    default = " DEFAULT '" + d.replace("'", "''") + "'"
                elif isinstance(d, (int, float)) and not isinstance(d, bool):
                    default = f" DEFAULT {d}"
                elif isinstance(d, bool):
                    default = f" DEFAULT {int(d)}"
                conn.execute(text(f'ALTER TABLE "{table.name}" ADD COLUMN "{col.name}" {typ}{default}'))


def init_db():
    from . import models  # noqa: F401
    SQLModel.metadata.create_all(engine)
    _migrate()


def get_session():
    with Session(engine, expire_on_commit=False) as s:
        yield s


@contextmanager
def session_scope():
    with Session(engine, expire_on_commit=False) as s:
        yield s
