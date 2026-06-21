"""FastAPI web API example for the restaurant inventory system.

This file demonstrates how the same InventoryManager used by the CLI can back
a modern web API.  The API layer has three responsibilities:

    1. Parse and validate HTTP requests using Pydantic schemas.
    2. Call InventoryManager methods.
    3. Return HTTP responses (JSON) and appropriate status codes.

Why FastAPI?
    - Type hints are reused for request/response validation.
    - Automatic OpenAPI/Swagger documentation at /docs.
    - Async-capable, but we use sync mode here to match the manager.

How to run:
    cd web
    pip install -r requirements.txt
    export PYTHONPATH=../src
    uvicorn api:app --reload

Then open http://localhost:8000 for the frontend or
http://localhost:8000/docs for the interactive API explorer.
"""

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# Import Pydantic schemas from the same directory.  We use a plain import
# (not relative) so the file can be run directly with uvicorn from the web/
# directory without treating web/ as a Python package.
from schemas import (
    CategoryCreate,
    CategoryOut,
    IngredientCreate,
    IngredientOut,
    StockAdjustment,
    StockMovement,
    StockTransactionOut,
    SupplierCreate,
    SupplierOut,
)

# Import the same manager and models the CLI uses.
from inventory import InventoryManager
from inventory.config import Config
from inventory.database import Database
from inventory.inventory import InsufficientStockError, NotFoundError
from inventory.models import Category, Ingredient, StockTransaction, Supplier


# ---------------------------------------------------------------------------
# Application lifespan
# ---------------------------------------------------------------------------
# The lifespan context manager runs setup code when the server starts and
# teardown code when it stops.  Here we create the database tables and a shared
# InventoryManager instance.
@asynccontextmanager
async def lifespan(app: FastAPI) -> Any:
    """Create tables on startup; nothing special on shutdown."""
    # Compute the database path relative to this file.
    db_path = Path(__file__).resolve().parents[1] / "data" / "inventory_web.db"
    config = Config(database_url=f"sqlite:///{db_path}")
    database = Database(config)
    database.create_tables()

    # Store the manager on the app so every route can access it.
    app.state.manager = InventoryManager(database)
    yield


app = FastAPI(
    title="Restaurant Inventory API",
    description="Web API example for the restaurant inventory system.",
    version="0.1.0",
    lifespan=lifespan,
)

# Serve static files (HTML, CSS, JS) from the static directory.
app.mount(
    "/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static"
)

# Jinja2 is used only to render the single index.html page.
templates = Jinja2Templates(directory=Path(__file__).parent / "static")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def get_manager(request: Request) -> InventoryManager:
    """Return the InventoryManager stored in app.state."""
    # app.state is typed as Any, so we assign to a typed variable for mypy.
    manager: InventoryManager = request.app.state.manager
    return manager


def to_category_out(category: Category) -> CategoryOut:
    """Convert a SQLAlchemy Category into a Pydantic response model."""
    return CategoryOut.model_validate(category)


def to_supplier_out(supplier: Supplier) -> SupplierOut:
    """Convert a SQLAlchemy Supplier into a Pydantic response model."""
    return SupplierOut.model_validate(supplier)


def to_ingredient_out(ingredient: Ingredient) -> IngredientOut:
    """Convert a SQLAlchemy Ingredient into a Pydantic response model."""
    return IngredientOut.model_validate(ingredient)


def to_transaction_out(transaction: StockTransaction) -> StockTransactionOut:
    """Convert a SQLAlchemy StockTransaction into a Pydantic response model."""
    return StockTransactionOut.model_validate(transaction)


# ---------------------------------------------------------------------------
# HTML page
# ---------------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> Any:
    """Serve the single-page frontend."""
    # In newer FastAPI/Starlette the first positional argument is the request.
    return templates.TemplateResponse(request, "index.html")


# ---------------------------------------------------------------------------
# Categories
# ---------------------------------------------------------------------------
@app.get("/api/categories", response_model=list[CategoryOut])
async def list_categories(request: Request) -> list[CategoryOut]:
    """Return all ingredient categories."""
    manager = get_manager(request)
    return [to_category_out(c) for c in manager.list_categories()]


@app.post("/api/categories", response_model=CategoryOut, status_code=201)
async def create_category(request: Request, payload: CategoryCreate) -> CategoryOut:
    """Create a new ingredient category."""
    manager = get_manager(request)
    return to_category_out(manager.add_category(payload.name, payload.description))


# ---------------------------------------------------------------------------
# Suppliers
# ---------------------------------------------------------------------------
@app.get("/api/suppliers", response_model=list[SupplierOut])
async def list_suppliers(request: Request) -> list[SupplierOut]:
    """Return all suppliers."""
    manager = get_manager(request)
    return [to_supplier_out(s) for s in manager.list_suppliers()]


@app.post("/api/suppliers", response_model=SupplierOut, status_code=201)
async def create_supplier(request: Request, payload: SupplierCreate) -> SupplierOut:
    """Create a new supplier."""
    manager = get_manager(request)
    return to_supplier_out(
        manager.add_supplier(
            name=payload.name,
            contact_name=payload.contact_name,
            phone=payload.phone,
            email=payload.email,
            address=payload.address,
        )
    )


# ---------------------------------------------------------------------------
# Ingredients
# ---------------------------------------------------------------------------
@app.get("/api/ingredients", response_model=list[IngredientOut])
async def list_ingredients(request: Request) -> list[IngredientOut]:
    """Return all ingredients with their categories and suppliers."""
    manager = get_manager(request)
    return [to_ingredient_out(i) for i in manager.list_ingredients()]


@app.post("/api/ingredients", response_model=IngredientOut, status_code=201)
async def create_ingredient(
    request: Request, payload: IngredientCreate
) -> IngredientOut:
    """Create a new ingredient."""
    manager = get_manager(request)
    return to_ingredient_out(
        manager.add_ingredient(
            sku=payload.sku,
            name=payload.name,
            unit=payload.unit,
            category_id=payload.category_id,
            supplier_id=payload.supplier_id,
            reorder_level=payload.reorder_level,
            reorder_quantity=payload.reorder_quantity,
            current_stock=payload.current_stock,
            cost_per_unit=payload.cost_per_unit,
        )
    )


@app.get("/api/ingredients/{ingredient_id}", response_model=IngredientOut)
async def get_ingredient(request: Request, ingredient_id: int) -> IngredientOut:
    """Return a single ingredient by id."""
    manager = get_manager(request)
    try:
        return to_ingredient_out(manager.get_ingredient(ingredient_id))
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get(
    "/api/ingredients/{ingredient_id}/transactions",
    response_model=list[StockTransactionOut],
)
async def get_ingredient_transactions(
    request: Request, ingredient_id: int, limit: int = 20
) -> list[StockTransactionOut]:
    """Return recent stock transactions for an ingredient."""
    manager = get_manager(request)
    transactions = manager.get_transactions(ingredient_id=ingredient_id, limit=limit)
    return [to_transaction_out(t) for t in transactions]


# ---------------------------------------------------------------------------
# Stock movements
# ---------------------------------------------------------------------------
@app.post("/api/ingredients/{ingredient_id}/receive", response_model=IngredientOut)
async def receive_stock(
    request: Request, ingredient_id: int, payload: StockMovement
) -> IngredientOut:
    """Receive stock for an ingredient."""
    manager = get_manager(request)
    try:
        return to_ingredient_out(
            manager.receive_stock(
                ingredient_id=ingredient_id,
                quantity=payload.quantity,
                reference=payload.reference,
                notes=payload.notes,
            )
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/ingredients/{ingredient_id}/use", response_model=IngredientOut)
async def use_stock(
    request: Request, ingredient_id: int, payload: StockMovement
) -> IngredientOut:
    """Use/remove stock for an ingredient."""
    manager = get_manager(request)
    try:
        return to_ingredient_out(
            manager.use_stock(
                ingredient_id=ingredient_id,
                quantity=payload.quantity,
                reference=payload.reference,
                notes=payload.notes,
            )
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except InsufficientStockError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/ingredients/{ingredient_id}/adjust", response_model=IngredientOut)
async def adjust_stock(
    request: Request, ingredient_id: int, payload: StockAdjustment
) -> IngredientOut:
    """Manually adjust stock for an ingredient."""
    manager = get_manager(request)
    try:
        return to_ingredient_out(
            manager.adjust_stock(
                ingredient_id=ingredient_id,
                new_quantity=payload.new_quantity,
                notes=payload.notes,
            )
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except InsufficientStockError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
