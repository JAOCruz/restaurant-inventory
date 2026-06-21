"""Application configuration.

This module handles all configuration for the application.  The goal is to
keep environment-specific values (database URL, debug flags, log levels) in
one place so the rest of the code does not need to know whether it is running
in a test, on a developer laptop, or in production.

Why use a dataclass?
    - Immutable (frozen=True): once created, the config cannot be accidentally
      changed by some distant part of the program.
    - Typed: mypy can verify we are passing the right kinds of values around.
    - Simple: no extra dependencies, easy to understand for learners.

Why load_dotenv()?
    python-dotenv reads a `.env` file (if present) and turns its contents into
    environment variables.  This lets developers keep secrets and local settings
    out of source control while still making them available to the app.
"""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from a `.env` file in the current working directory.
# This is safe to call even when no `.env` file exists.
load_dotenv()


@dataclass(frozen=True)
class Config:
    """Immutable application configuration.

    Attributes:
        database_url: SQLAlchemy connection string, e.g.
            "sqlite:///data/inventory.db" or
            "postgresql://user:pass@host:5432/inventory".
        log_level: One of DEBUG, INFO, WARNING, ERROR.
        debug: When True, SQLAlchemy echoes every SQL statement it executes.
    """

    database_url: str
    log_level: str = "INFO"
    debug: bool = False

    @classmethod
    def from_env(cls) -> "Config":
        """Build configuration from environment variables.

        The DATABASE_URL defaults to a SQLite file next to the project root.
        We compute the path dynamically from this file's location so the app
        works no matter where the repository is cloned.
        """
        db_url = os.getenv(
            "DATABASE_URL",
            # parents[2] walks from src/inventory/config.py up to the project root.
            f"sqlite:///{Path(__file__).resolve().parents[2] / 'data' / 'inventory.db'}",
        )
        return cls(
            database_url=db_url,
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            # Accept several common truthy spellings for the DEBUG variable.
            debug=os.getenv("DEBUG", "false").lower() in ("1", "true", "yes"),
        )
