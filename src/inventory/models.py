"""SQLAlchemy ORM models for the restaurant inventory system.

What is an ORM?
    ORM stands for Object-Relational Mapper.  It lets us define database tables
    as Python classes and rows as instances of those classes.  Instead of
    writing raw SQL like:

        INSERT INTO ingredients (sku, name, unit) VALUES ('TOM-001', 'Tomato', 'kg');

    we can write Python like:

        tomato = Ingredient(sku='TOM-001', name='Tomato', unit='kg')
        session.add(tomato)
        session.commit()

    SQLAlchemy translates between Python objects and SQL for us.

How this file is organised:
    - Enums for fixed sets of values (transaction types, units of measure).
    - Base class that all models inherit from.
    - One class per table: Category, Supplier, Ingredient, StockTransaction.
    - Relationships link tables together (e.g., an Ingredient belongs to a Category).

Why use Mapped[...]?
    Mapped is part of SQLAlchemy 2.0's type-annotated declaration style.  It
    tells SQLAlchemy which class attributes are database columns and lets
    type-checkers understand the model.

Why Decimal instead of float?
    Floats cannot represent most decimal numbers exactly (0.1 + 0.2 != 0.3).
    For money and weights we use Decimal to avoid rounding errors.
"""

import enum
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all ORM models.

    Every table in our system inherits from Base.  SQLAlchemy collects all
    subclasses of Base and uses them to build the database schema.
    """


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------
# Enums keep our data clean.  Instead of allowing any string in the
# transaction_type column, we only allow the four values below.  Using a
# Python enum means the compiler/IDE can catch typos early.
class TransactionType(str, enum.Enum):
    """Supported stock transaction types."""

    RECEIPT = "receipt"  # stock added (e.g., a delivery arrived)
    USAGE = "usage"  # stock removed for cooking
    WASTE = "waste"  # stock discarded
    ADJUSTMENT = "adjustment"  # manual correction during inventory count


class UnitOfMeasure(str, enum.Enum):
    """Common units of measure for inventory items.

    These are examples.  The `unit` column on Ingredient stores a string, so
    the application can support additional units without changing the schema.
    """

    KILOGRAM = "kg"
    GRAM = "g"
    LITER = "l"
    MILLILITER = "ml"
    PIECE = "piece"
    BOX = "box"
    BOTTLE = "bottle"


# ---------------------------------------------------------------------------
# Categories
# ---------------------------------------------------------------------------
class Category(Base):
    """A logical grouping of ingredients (e.g., produce, dairy, meat).

    Think of this as a folder on a file system: it does not hold stock itself,
    but it groups related items together so reports are easier to read.
    """

    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    # relationship() tells SQLAlchemy how Category rows relate to Ingredient rows.
    # back_populates creates a two-way link: category.ingredients and
    # ingredient.category both work automatically.
    ingredients: Mapped[list["Ingredient"]] = relationship(
        "Ingredient", back_populates="category"
    )

    def __repr__(self) -> str:
        return f"<Category id={self.id} name={self.name!r}>"


# ---------------------------------------------------------------------------
# Suppliers
# ---------------------------------------------------------------------------
class Supplier(Base):
    """A vendor that supplies ingredients to the restaurant."""

    __tablename__ = "suppliers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    contact_name: Mapped[str | None] = mapped_column(String(150))
    phone: Mapped[str | None] = mapped_column(String(30))
    email: Mapped[str | None] = mapped_column(String(150))
    address: Mapped[str | None] = mapped_column(Text)

    ingredients: Mapped[list["Ingredient"]] = relationship(
        "Ingredient", back_populates="supplier"
    )

    def __repr__(self) -> str:
        return f"<Supplier id={self.id} name={self.name!r}>"


# ---------------------------------------------------------------------------
# Ingredients
# ---------------------------------------------------------------------------
class Ingredient(Base):
    """A raw material tracked in the inventory.

    This is the central table of the application.  Each row represents one
    type of ingredient (tomatoes, chicken breast, olive oil, etc.) and keeps
    track of how much of it is currently in stock.

    Important fields:
        sku: Stock-keeping unit — a short, unique code used in kitchens and
             invoices (e.g., TOM-001).
        reorder_level: When current_stock falls to or below this value, the
                       ingredient should be reordered.
        reorder_quantity: How much to order when restocking.
        current_stock: The real-time quantity on hand.
        cost_per_unit: Average purchase cost, used for cost-of-goods reports.
    """

    __tablename__ = "ingredients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sku: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)

    # ForeignKey creates a database-level relationship between tables.
    # ondelete="SET NULL" means: if a category is deleted, its ingredients
    # become uncategorised instead of being deleted.
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL")
    )
    supplier_id: Mapped[int | None] = mapped_column(
        ForeignKey("suppliers.id", ondelete="SET NULL")
    )

    unit: Mapped[str] = mapped_column(String(20), nullable=False)
    reorder_level: Mapped[Decimal] = mapped_column(
        Numeric(12, 3), nullable=False, default=Decimal("0")
    )
    reorder_quantity: Mapped[Decimal] = mapped_column(
        Numeric(12, 3), nullable=False, default=Decimal("0")
    )
    current_stock: Mapped[Decimal] = mapped_column(
        Numeric(12, 3), nullable=False, default=Decimal("0")
    )
    cost_per_unit: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))

    # Timestamps are stored with timezone info so they remain correct even if
    # the server moves to a different time zone.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    category: Mapped["Category"] = relationship(
        "Category", back_populates="ingredients"
    )
    supplier: Mapped["Supplier"] = relationship(
        "Supplier", back_populates="ingredients"
    )
    # cascade="all, delete-orphan" means: when an Ingredient is deleted, all of
    # its StockTransaction rows are deleted automatically.  This keeps the audit
    # trail consistent with the ingredient that no longer exists.
    transactions: Mapped[list["StockTransaction"]] = relationship(
        "StockTransaction", back_populates="ingredient", cascade="all, delete-orphan"
    )

    # __table_args__ is where we put database-level constraints that involve
    # more than one column or need a custom name.
    __table_args__ = (
        CheckConstraint("current_stock >= 0", name="ck_ingredients_non_negative_stock"),
        CheckConstraint("reorder_level >= 0", name="ck_ingredients_reorder_level"),
    )

    @property
    def needs_reorder(self) -> bool:
        """Return True when current stock is at or below the reorder level.

        This is a computed property, not a database column.  It is calculated
        on the fly whenever you read ingredient.needs_reorder.
        """
        return self.current_stock <= self.reorder_level

    def __repr__(self) -> str:
        return f"<Ingredient id={self.id} sku={self.sku!r} name={self.name!r}>"


# ---------------------------------------------------------------------------
# Stock Transactions
# ---------------------------------------------------------------------------
class StockTransaction(Base):
    """A single movement of stock for an ingredient.

    This table is the audit trail.  Every time stock is received, used,
    wasted, or adjusted, a row is written here.  You should never edit or
    delete historical transactions; instead, create a new adjustment if a
    correction is needed.
    """

    __tablename__ = "stock_transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ingredient_id: Mapped[int] = mapped_column(
        ForeignKey("ingredients.id", ondelete="CASCADE"), nullable=False
    )
    # transaction_type stores one of the TransactionType enum values as text.
    transaction_type: Mapped[str] = mapped_column(String(20), nullable=False)
    # Quantity is always positive; the transaction_type tells you the direction.
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    reference: Mapped[str | None] = mapped_column(String(100))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    ingredient: Mapped["Ingredient"] = relationship(
        "Ingredient", back_populates="transactions"
    )

    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_transactions_positive_quantity"),
    )

    def __repr__(self) -> str:
        return (
            f"<StockTransaction id={self.id} "
            f"ingredient_id={self.ingredient_id} "
            f"type={self.transaction_type!r} "
            f"quantity={self.quantity}>"
        )
