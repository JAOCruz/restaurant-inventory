# Restaurant Inventory System Bobopz

A professional, production-ready inventory management system for restaurants.
It tracks ingredients, suppliers, categories, stock levels, and every stock
movement (receipts, usage, waste, and adjustments) in a SQL database.

## Features

- **Ingredient catalog** with SKU, category, supplier, unit, reorder levels, and cost.
- **Stock control** with receipts, usage, adjustments, and audit trail.
- **Low-stock alerts** based on configurable reorder levels.
- **Supplier management** to link ingredients to vendors.
- **CLI application** for day-to-day operations.
- **Docker & Docker Compose** setup for PostgreSQL.
- **Automated tests** with pytest and code quality with Ruff / MyPy.

## Project Structure

```
restaurant-inventory/
├── src/
│   └── inventory/              # Main Python package
│       ├── __init__.py         # Public API exports
│       ├── __main__.py         # `python -m inventory` entry point
│       ├── cli.py              # Command-line interface
│       ├── config.py           # Configuration from environment / .env
│       ├── database.py         # SQLAlchemy engine & session manager
│       ├── inventory.py        # Core business logic
│       └── models.py           # SQLAlchemy ORM models
├── sql/
│   ├── schema.sql              # SQLite DDL (used by init_db.sh)
│   ├── schema.postgres.sql     # PostgreSQL DDL (used by Docker Compose)
│   └── seed.sql                # Sample development data
├── tests/
│   └── test_inventory.py       # pytest suite
├── scripts/
│   └── init_db.sh              # Bootstrap a local SQLite database
├── web/                        # FastAPI web example
│   ├── api.py                  # REST API routes
│   ├── schemas.py              # Pydantic request/response models
│   ├── requirements.txt        # Web-specific dependencies
│   ├── README.md               # How to run the web app
│   └── static/
│       ├── index.html          # Frontend page
│       └── app.js              # Frontend JavaScript
├── docs/
│   └── architecture.md         # Mermaid architecture diagrams
├── TEACHING.md                 # Beginner-friendly learning guide
├── Dockerfile                  # Container image for the app
├── docker-compose.yml          # PostgreSQL + app stack
├── pyproject.toml              # Build metadata, tool config, dependencies
├── requirements.txt            # Runtime dependencies
├── .env.example                # Example environment variables
└── README.md                   # This file
```

## Quick Start (SQLite)

1. **Create a virtual environment and install dependencies:**

   ```bash
   cd restaurant-inventory
   python -m venv .venv   
   source .venv/bin/activate # .venv\Scripts\Activate.ps1 windows
   pip install -r requirements.txt
   pip install -e ".[dev]"
   ```

2. **Initialize the database:**  #Nice69

   ```bash
   ./scripts/init_db.sh #./scripts/init_db.ps1 Windows
   ```

   Or use the Python CLI:

   ```bash
   python -m inventory init
   ```

3. **Run a command:**

   ```bash
   python -m inventory list-ingredients
   ```

## Quick Start (Docker + PostgreSQL)

```bash
docker compose up --build
```

This starts a PostgreSQL container pre-loaded with the schema and seed data,
then runs the application container which lists the seeded ingredients.

The PostgreSQL host port defaults to `15432` to avoid conflicts with a local
PostgreSQL installation. Override it with the `POSTGRES_PORT` environment
variable or in your `.env` file.

## Web App Example

A complete FastAPI + HTML/JS example is in the `web/` directory.  It reuses the
same `InventoryManager` as the CLI, showing how the core business logic is
independent of the user interface.

R.

```bash
cd web
pip install -r requirements.txt
export PYTHONPATH=../src
uvicorn api:app --reload
```

- Frontend: http://localhost:8000
- Interactive API docs: http://localhost:8000/docs

See `web/README.md` for details.

## Learning Resources

- **[TEACHING.md](TEACHING.md)** — a beginner-friendly guide to the codebase,
  layers, and design patterns.
- **[docs/architecture.md](docs/architecture.md)** — Mermaid diagrams showing
  system architecture, database relationships, and request/response flows.

## CLI Usage

```bash
# Initialize schema
python -m inventory init

# Add a category
python -m inventory add-category Produce --description "Fresh vegetables"

# Add a supplier
python -m inventory add-supplier "Green Valley Produce" \
    --contact "Maria" --phone "555-0101" --email "maria@example.com"

# Add an ingredient
python -m inventory add-ingredient TOM-001 "Roma Tomatoes" kg \
    --category 1 --supplier 1 --reorder-level 5 --reorder-quantity 10 \
    --current-stock 12.5 --cost 2.50

# List all ingredients
python -m inventory list-ingredients

# Receive stock
python -m inventory receive 1 10.0 --reference "PO-123"

# Use stock
python -m inventory use 1 2.5 --notes "Daily prep"

# Adjust stock
python -m inventory adjust 1 8.0 --notes "Spoilage count"

# View low-stock items
python -m inventory low-stock

# View transaction history
python -m inventory transactions --ingredient 1 --limit 20
```

## Configuration

Configuration is read from environment variables (and an optional `.env` file):

| Variable       | Default                          | Description                        |
| -------------- | -------------------------------- | ---------------------------------- |
| `DATABASE_URL` | `sqlite:///data/inventory.db`    | SQLAlchemy connection string       |
| `LOG_LEVEL`    | `INFO`                           | Logging level                      |
| `DEBUG`        | `false`                          | Enable SQL echoing when `true`     |
| `POSTGRES_PORT`| `15432`                          | Host port for Docker Compose PostgreSQL |

Copy `.env.example` to `.env` and edit as needed.

## Running Tests

```bash
pytest
```

With coverage:

```bash
pytest --cov=inventory --cov-report=html
```

## Code Quality

```bash
# Linting and auto-formatting
ruff check .
ruff format .

# Static type checking
mypy src/inventory
```

## Technology Choices

- **Python 3.10+** with type hints for maintainability.
- **SQLAlchemy 2.0** ORM for database portability.
- **SQLite** for local development and **PostgreSQL** for production / Docker.
- **Docker Compose** to spin up a reproducible PostgreSQL environment.
- **pytest** for unit testing.
- **Ruff** and **MyPy** for linting, formatting, and type checking.
- **FastAPI + Pydantic** example for a modern web API.

## License

MIT