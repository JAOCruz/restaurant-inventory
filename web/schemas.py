"""Pydantic schemas for the FastAPI web example.

Pydantic validates data that comes from HTTP requests and formats data that
goes back in HTTP responses.  These schemas are separate from the SQLAlchemy
models so the API contract does not have to match the database schema exactly.

Key concepts:
    - Request schemas (e.g., IngredientCreate) define what the client must send.
    - Response schemas (e.g., IngredientOut) define what the server returns.
    - `from_attributes=True` tells Pydantic it can read attributes from ORM
      objects, not just dictionaries.
"""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


# ---------------------------------------------------------------------------
# Shared base schemas
# ---------------------------------------------------------------------------
class CategoryBase(BaseModel):
    """Fields common to category requests and responses."""

    name: str
    description: str | None = None


class CategoryCreate(CategoryBase):
    """Schema for creating a new category."""


class CategoryOut(CategoryBase):
    """Schema returned when reading a category."""

    model_config = ConfigDict(from_attributes=True)

    id: int


class SupplierBase(BaseModel):
    """Fields common to supplier requests and responses."""

    name: str
    contact_name: str | None = None
    phone: str | None = None
    email: str | None = None
    address: str | None = None


class SupplierCreate(SupplierBase):
    """Schema for creating a new supplier."""


class SupplierOut(SupplierBase):
    """Schema returned when reading a supplier."""

    model_config = ConfigDict(from_attributes=True)

    id: int


class IngredientBase(BaseModel):
    """Fields common to ingredient requests and responses."""

    sku: str
    name: str
    unit: str
    category_id: int | None = None
    supplier_id: int | None = None
    reorder_level: Decimal = Decimal("0")
    reorder_quantity: Decimal = Decimal("0")
    current_stock: Decimal = Decimal("0")
    cost_per_unit: Decimal | None = None


class IngredientCreate(IngredientBase):
    """Schema for creating a new ingredient."""


class IngredientOut(IngredientBase):
    """Schema returned when reading an ingredient.

    Includes nested category and supplier objects, plus a computed
    needs_reorder flag.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    category: CategoryOut | None = None
    supplier: SupplierOut | None = None
    needs_reorder: bool


class StockMovement(BaseModel):
    """Schema for a stock receipt or usage request."""

    quantity: Decimal
    reference: str | None = None
    notes: str | None = None


class StockAdjustment(BaseModel):
    """Schema for a manual stock adjustment request."""

    new_quantity: Decimal
    notes: str | None = None


class StockTransactionOut(BaseModel):
    """Schema returned for a stock transaction."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    ingredient_id: int
    transaction_type: str
    quantity: Decimal
    reference: str | None = None
    notes: str | None = None
    # Pydantic automatically serialises datetime to an ISO 8601 string in JSON.
    created_at: datetime | None = None
