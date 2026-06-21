# Teaching Guide: Restaurant Inventory System

This guide explains the technology and design choices used in the project.  It
is written for learners who understand basic Python and want to see how a real,
layered application is structured.

## What this project teaches

- How to structure a Python application into clear layers.
- How to use SQLAlchemy 2.0 to map Python classes to SQL tables.
- How to keep business logic independent of the user interface.
- How a CLI and a web API can share the same core code.
- Why we use `Decimal`, context managers, and eager loading.

## The big picture: layers

A well-organised application separates concerns into layers.  Each layer has
one job and talks to its neighbours through a narrow interface.

```
┌─────────────────────────────────────────────┐
│  User interface layer                        │
│  - CLI (argparse)                            │
│  - Web API (FastAPI, see web/)               │
└──────────────┬──────────────────────────────┘
               │ calls methods on
┌──────────────▼──────────────────────────────┐
│  Business logic layer                        │
│  - InventoryManager (src/inventory/inventory.py)
│  - Domain exceptions (NotFoundError, InsufficientStockError)
└──────────────┬──────────────────────────────┘
               │ uses sessions from
┌──────────────▼──────────────────────────────┐
│  Data access layer                           │
│  - Database (src/inventory/database.py)      │
│  - Models (src/inventory/models.py)          │
└──────────────┬──────────────────────────────┘
               │ talks to
┌──────────────▼──────────────────────────────┐
│  SQL database                                │
│  - SQLite for local development              │
│  - PostgreSQL for production / Docker        │
└─────────────────────────────────────────────┘
```

This layering means:

- You can swap the CLI for a web app without rewriting business rules.
- You can swap SQLite for PostgreSQL without rewriting business rules.
- You can test business rules quickly, without a browser or terminal.

## Layer 1: configuration (`src/inventory/config.py`)

Configuration is everything that changes between environments: the database
URL, log level, debug mode, etc.

We keep it in one place because:

1. It is easy to find.
2. It is easy to override with environment variables or a `.env` file.
3. The rest of the code does not need to know where the values come from.

The `Config` class is a frozen dataclass.  "Frozen" means instances are
immutable: once created, they cannot be changed.  This prevents accidental
mutation deep inside the program.

## Layer 2: database connection (`src/inventory/database.py`)

This layer creates a SQLAlchemy `Engine` and `Session` factory.

### Engine

The engine is the object that knows how to connect to the database.  You
usually create one engine per process and reuse it.

```python
engine = create_engine("sqlite:///data/inventory.db")
```

### Session

A session is a temporary workspace.  You load objects into it, change them,
and then commit or rollback.

```python
session.add(new_ingredient)
session.commit()   # save changes
session.rollback() # discard changes
session.close()    # release connection
```

### Context manager

Our `Database.session()` method is a context manager:

```python
with self.db.session() as session:
    ingredient = session.get(Ingredient, 1)
    ingredient.current_stock += 5
    # commit and close happen automatically
```

It guarantees three things:

1. If no exception is raised, the transaction is committed.
2. If an exception is raised, the transaction is rolled back.
3. The session is always closed, even if something goes wrong.

## Layer 3: models (`src/inventory/models.py`)

Models are Python classes that represent database tables.

### Mapping a class to a table

```python
class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
```

`Base` is SQLAlchemy's registry.  Every subclass of `Base` becomes a table.

`Mapped[int]` tells SQLAlchemy "this attribute maps to a database column whose
Python type is int".

`mapped_column(Integer, primary_key=True)` tells SQLAlchemy the column type and
that it is the primary key.

### Relationships

```python
class Category(Base):
    ingredients: Mapped[list["Ingredient"]] = relationship(
        "Ingredient", back_populates="category"
    )

class Ingredient(Base):
    category: Mapped["Category"] = relationship("Category", back_populates="ingredients")
```

`relationship()` links two tables.  `back_populates` makes the link two-way:

```python
produce = Category(name="Produce")
tomato = Ingredient(name="Tomato", category=produce)
assert tomato.category == produce
assert produce.ingredients == [tomato]
```

### Why `Decimal`?

Money and weights should never be stored as `float` because floats cannot
represent decimals exactly:

```python
>>> 0.1 + 0.2
0.30000000000000004
```

`Decimal` stores numbers exactly, which is critical for cost and stock
calculations.

## Layer 4: business logic (`src/inventory/inventory.py`)

`InventoryManager` is the heart of the application.  It contains methods like
`add_ingredient`, `receive_stock`, `use_stock`, and `adjust_stock`.

Each method:

1. Validates input.
2. Opens a session.
3. Loads or creates the needed model(s).
4. Applies business rules.
5. Commits automatically.
6. Returns the result.

### Example: receiving stock

```python
def receive_stock(self, ingredient_id, quantity, reference=None, notes=None):
    qty = Decimal(str(quantity))          # 1. validate/normalise
    with self.db.session() as session:    # 2. open session
        ingredient = session.get(Ingredient, ingredient_id)  # 3. load
        if ingredient is None:
            raise NotFoundError(...)      # 4. business rule: must exist
        ingredient.current_stock += qty   # 4. apply change
        self._record_transaction(...)     # 4. audit trail
        session.flush()
        session.refresh(ingredient)
        return ingredient                 # 6. return result
```

### Why return ORM objects?

Returning the object lets the caller print its attributes.  Because we set
`expire_on_commit=False` and eager-load relationships, the object is still
usable after the session closes.

### Domain exceptions

We raise custom exceptions instead of printing error messages directly:

- `NotFoundError` — the requested entity does not exist.
- `InsufficientStockError` — the operation would make stock negative.

Custom exceptions let callers decide how to report the error.  The CLI prints
to stderr; a web API returns an HTTP 404 or 422.

## Layer 5: user interface (`src/inventory/cli.py`)

The CLI is an adapter.  It parses terminal arguments and calls manager
methods.  It contains no business logic.

### Adding a command

1. Write a handler function:

   ```python
   def cmd_receive(args, manager):
       ingredient = manager.receive_stock(args.ingredient, args.quantity)
       print(f"New stock: {ingredient.current_stock}")
       return 0
   ```

2. Register it in `handlers`.
3. Add a subparser in `build_parser()`.

This pattern is the same in many frameworks: parse input, call the service
layer, render output.

## From CLI to web app

The same `InventoryManager` can back a web API.  The web layer does three
things:

1. **Parse HTTP requests** — read JSON from the client.
2. **Call the manager** — exactly like the CLI does.
3. **Return HTTP responses** — serialise the result as JSON.

Example mapping:

| Action | CLI command | HTTP endpoint |
| ------ | ----------- | ------------- |
| List ingredients | `inventory list-ingredients` | `GET /api/ingredients` |
| Add ingredient | `inventory add-ingredient ...` | `POST /api/ingredients` |
| Receive stock | `inventory receive 1 10` | `POST /api/ingredients/1/receive` |
| Use stock | `inventory use 1 2.5` | `POST /api/ingredients/1/use` |

See the `web/` directory for a working FastAPI implementation.

## Request/response flow in a web app

```
Browser
   │  POST /api/ingredients/1/receive
   │  { "quantity": 10 }
   ▼
FastAPI route (web/api.py)
   │  parses JSON into a Pydantic model
   ▼
InventoryManager.receive_stock(1, 10)
   ▼
Database.session() context manager
   │  loads Ingredient from DB
   │  updates current_stock
   │  creates StockTransaction
   │  commits
   ▼
Returns Ingredient object
   ▼
FastAPI serialises it to JSON
   │  { "id": 1, "current_stock": "20.000", ... }
   ▼
Browser updates the page
```

## Common pitfalls and how we avoid them

### DetachedInstanceError

By default, SQLAlchemy expires objects after commit.  If you access an
attribute after the session closes, SQLAlchemy tries to reload it and fails.

We fix this by setting `expire_on_commit=False` in the session maker.

### Lazy loading outside a session

If you access `ingredient.category.name` after the session closes and the
category was never loaded, SQLAlchemy tries to query the database and fails.

We fix this with eager loading (`selectinload`) in the manager's query methods.

### Floating-point money

We use `Decimal` for all quantities and costs to avoid rounding errors.

### Hard-coded configuration

All environment-specific values come from `Config`, not from inline strings.

## Try it yourself

1. Run the CLI to add an ingredient and receive stock.
2. Look at `src/inventory/inventory.py` and trace which model fields change.
3. Open the web app (`web/README.md`) and compare the API routes to the CLI
   commands.
4. Add a new field to `Ingredient` in `models.py`, run `python -m inventory init`,
   and see how SQLAlchemy updates the schema.

## Further reading

- [SQLAlchemy 2.0 tutorial](https://docs.sqlalchemy.org/en/20/tutorial/)
- [FastAPI documentation](https://fastapi.tiangolo.com/)
- [argparse documentation](https://docs.python.org/3/library/argparse.html)
- [Docker Compose overview](https://docs.docker.com/compose/)
