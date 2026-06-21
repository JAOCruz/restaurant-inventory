"""Database engine and session management.

This module is the bridge between Python code and the actual SQL database.
It uses SQLAlchemy, a toolkit that lets us work with databases through Python
objects (the ORM) while still allowing raw SQL when needed.

Key concepts for learners:

1. Engine
   The Engine is SQLAlchemy's connection pool and dialect manager.  It knows
   *how* to talk to SQLite, PostgreSQL, MySQL, etc.  We create one engine per
   application process and reuse it.

2. Session
   A Session is a temporary workspace.  You load objects into it, modify them,
   and then commit (save) or rollback (discard) the changes.  Sessions should
   be short-lived: open one, do a unit of work, close it.

3. Context manager (`with self.db.session()`)
   The `session()` method below is a context manager.  It guarantees that:
   - the session is committed if no exception is raised
   - the session is rolled back if an exception is raised
   - the session is always closed, even if something goes wrong
   This pattern prevents connection leaks and partial writes.

4. expire_on_commit=False
   By default, SQLAlchemy expires object attributes after a commit.  When you
   later access an attribute, SQLAlchemy tries to refresh it from the database.
   If the session is already closed, that fails with DetachedInstanceError.
   Setting expire_on_commit=False keeps the loaded data usable after the
   session ends, which is convenient for returning objects from manager methods.
"""

from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from .config import Config


class Database:
    """Manages the SQLAlchemy engine and sessions for the application."""

    def __init__(self, config: Config | None = None) -> None:
        # Use the provided config, or build one from environment variables.
        self.config = config or Config.from_env()

        # Build keyword arguments for create_engine.  We add SQLite-specific
        # options when needed because SQLite has stricter thread-safety checks
        # than client/server databases.
        engine_kwargs: dict[str, Any] = {
            "echo": self.config.debug,  # print SQL when debugging
            "future": True,  # use SQLAlchemy 2.0 behaviour
        }

        if self.config.database_url.startswith("sqlite"):
            # SQLite's default mode refuses to share a connection across threads.
            # SQLAlchemy handles pooling safely for us, but we need to tell the
            # underlying sqlite3 driver to relax that check.
            engine_kwargs["connect_args"] = {"check_same_thread": False}
            # Make sure the directory for the SQLite file exists before the
            # engine tries to create the file.
            self._ensure_sqlite_directory()

        self.engine = create_engine(self.config.database_url, **engine_kwargs)

        # sessionmaker is a factory that produces Session objects bound to our
        # engine.  autocommit=False means we control transactions manually.
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine,
            future=True,
            expire_on_commit=False,
        )

    def _ensure_sqlite_directory(self) -> None:
        """Create the parent directory for a SQLite database file if needed."""
        url = self.config.database_url
        prefix = "sqlite:///"
        if url.startswith(prefix):
            db_path = Path(url[len(prefix) :])
            db_path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def session(self) -> Generator[Session, None, None]:
        """Provide a transactional scope around a series of operations.

        Typical usage inside a manager method:

            with self.db.session() as session:
                ingredient = session.get(Ingredient, ingredient_id)
                ingredient.current_stock += quantity
                # commit happens automatically here if no exception occurs

        Yields:
            A SQLAlchemy Session ready to use.
        """
        db = self.SessionLocal()
        try:
            yield db
            db.commit()
        except Exception:
            # If anything fails, roll back so the database stays consistent.
            db.rollback()
            raise
        finally:
            # Always close the session to release the database connection.
            db.close()

    def create_tables(self) -> None:
        """Create all tables defined in the models module.

        We import models inside the method to avoid circular imports at module
        load time.  SQLAlchemy reads the model metadata and emits the correct
        CREATE TABLE statements for the current database dialect.
        """
        from . import models  # noqa: PLC0415

        models.Base.metadata.create_all(bind=self.engine)

    def drop_tables(self) -> None:
        """Drop all tables defined in the models module.

        Useful for tests or for completely resetting a database.  Use with
        caution in production.
        """
        from . import models  # noqa: PLC0415

        models.Base.metadata.drop_all(bind=self.engine)
