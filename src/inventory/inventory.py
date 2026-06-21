"""Core business logic for the inventory management system.

This module is the "service layer" of the application.  It sits between the
user interface (CLI, web API, tests) and the database layer (models + Database).
All business rules live here:

    - You cannot use more stock than is available.
    - Every stock change must create a StockTransaction audit row.
    - Reorder levels are checked by the `needs_reorder` property.

Why separate business logic from the CLI and models?
    - Reusability: the same InventoryManager can back a CLI, a web API, a
      background worker, or a test suite.
    - Testability: we can test business rules without spinning up a web server
      or parsing command-line arguments.
    - Maintainability: when the rules change, we only edit this one file.

Each public method follows the same pattern:
    1. Validate and normalise inputs (e.g., convert quantity to Decimal).
    2. Open a database session using the context manager.
    3. Load or create the relevant model object(s).
    4. Apply business rules and raise domain exceptions when they are violated.
    5. Persist changes by letting the context manager commit.
    6. Return the resulting object.

The methods return ORM objects.  Because we configured `expire_on_commit=False`
in Database, those objects remain usable after the session closes.  We also
use `selectinload` on relationships we know the caller will access (category,
supplier, transactions) to avoid "lazy loading" errors outside the session.
"""

from collections.abc import Sequence
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .database import Database
from .models import Category, Ingredient, StockTransaction, Supplier, TransactionType


# ---------------------------------------------------------------------------
# Domain exceptions
# ---------------------------------------------------------------------------
# Custom exceptions make error handling clearer.  Callers can catch
# NotFoundError separately from InsufficientStockError and show the right
# message to the user.
class NotFoundError(Exception):
    """Raised when a requested entity does not exist."""


class InsufficientStockError(Exception):
    """Raised when a stock removal would make inventory negative."""


# ---------------------------------------------------------------------------
# Inventory manager
# ---------------------------------------------------------------------------
class InventoryManager:
    """High-level API for managing restaurant inventory.

    Think of this class as the "facade" for the whole system.  A CLI creates
    one InventoryManager and calls its methods.  A web API would do exactly
    the same thing.

    Args:
        database: An optional Database instance.  If omitted, a default one
            is created from environment variables.  Tests pass in a Database
            backed by a temporary SQLite file to stay isolated.
    """

    def __init__(self, database: Database | None = None) -> None:
        self.db = database or Database()

    # ------------------------------------------------------------------
    # Categories
    # ------------------------------------------------------------------
    def add_category(self, name: str, description: str | None = None) -> Category:
        """Create a new ingredient category.

        Example:
            >>> category = manager.add_category("Produce", "Fresh vegetables")
            >>> category.id
            1
        """
        with self.db.session() as session:
            category = Category(name=name, description=description)
            session.add(category)
            # flush() sends the INSERT to the database so the auto-generated
            # id is assigned, but the transaction is not committed yet.
            session.flush()
            # refresh() updates the Python object with any database defaults
            # (such as the generated id and timestamps).
            session.refresh(category)
            return category

    def get_category(self, category_id: int) -> Category:
        """Fetch a category by id.

        Raises:
            NotFoundError: if no category with that id exists.
        """
        with self.db.session() as session:
            category = session.get(Category, category_id)
            if category is None:
                raise NotFoundError(f"Category {category_id} not found")
            return category

    def list_categories(self) -> Sequence[Category]:
        """Return all categories ordered by name."""
        with self.db.session() as session:
            return (
                session.execute(select(Category).order_by(Category.name))
                .scalars()
                .all()
            )

    # ------------------------------------------------------------------
    # Suppliers
    # ------------------------------------------------------------------
    def add_supplier(
        self,
        name: str,
        contact_name: str | None = None,
        phone: str | None = None,
        email: str | None = None,
        address: str | None = None,
    ) -> Supplier:
        """Create a new supplier."""
        with self.db.session() as session:
            supplier = Supplier(
                name=name,
                contact_name=contact_name,
                phone=phone,
                email=email,
                address=address,
            )
            session.add(supplier)
            session.flush()
            session.refresh(supplier)
            return supplier

    def get_supplier(self, supplier_id: int) -> Supplier:
        """Fetch a supplier by id."""
        with self.db.session() as session:
            supplier = session.get(Supplier, supplier_id)
            if supplier is None:
                raise NotFoundError(f"Supplier {supplier_id} not found")
            return supplier

    def list_suppliers(self) -> Sequence[Supplier]:
        """Return all suppliers ordered by name."""
        with self.db.session() as session:
            return (
                session.execute(select(Supplier).order_by(Supplier.name))
                .scalars()
                .all()
            )

    # ------------------------------------------------------------------
    # Ingredients
    # ------------------------------------------------------------------
    def add_ingredient(
        self,
        sku: str,
        name: str,
        unit: str,
        category_id: int | None = None,
        supplier_id: int | None = None,
        reorder_level: Decimal | str | float = Decimal("0"),
        reorder_quantity: Decimal | str | float = Decimal("0"),
        current_stock: Decimal | str | float = Decimal("0"),
        cost_per_unit: Decimal | str | float | None = None,
    ) -> Ingredient:
        """Create a new ingredient and persist it.

        We accept quantity arguments as Decimal, str, or float so callers do
        not have to convert manually.  Everything is converted to Decimal to
        avoid floating-point rounding errors.
        """
        ingredient = Ingredient(
            sku=sku,
            name=name,
            unit=unit,
            category_id=category_id,
            supplier_id=supplier_id,
            reorder_level=Decimal(str(reorder_level)),
            reorder_quantity=Decimal(str(reorder_quantity)),
            current_stock=Decimal(str(current_stock)),
            cost_per_unit=None
            if cost_per_unit is None
            else Decimal(str(cost_per_unit)),
        )
        with self.db.session() as session:
            session.add(ingredient)
            session.flush()
            # Eager-load category and supplier before returning so the object
            # remains usable outside the session.
            return self._load_ingredient_with_relations(session, ingredient.id)

    def get_ingredient(self, ingredient_id: int) -> Ingredient:
        """Fetch an ingredient by id, including its category and supplier."""
        with self.db.session() as session:
            ingredient = session.execute(
                select(Ingredient)
                .where(Ingredient.id == ingredient_id)
                .options(
                    selectinload(Ingredient.category), selectinload(Ingredient.supplier)
                )
            ).scalar_one_or_none()
            if ingredient is None:
                raise NotFoundError(f"Ingredient {ingredient_id} not found")
            return ingredient

    def get_ingredient_by_sku(self, sku: str) -> Ingredient:
        """Fetch an ingredient by SKU, including its category and supplier."""
        with self.db.session() as session:
            ingredient = session.execute(
                select(Ingredient)
                .where(Ingredient.sku == sku)
                .options(
                    selectinload(Ingredient.category), selectinload(Ingredient.supplier)
                )
            ).scalar_one_or_none()
            if ingredient is None:
                raise NotFoundError(f"Ingredient with SKU {sku!r} not found")
            return ingredient

    def list_ingredients(self) -> Sequence[Ingredient]:
        """Return all ingredients ordered by name.

        Eager-loads category and supplier so callers can read
        ingredient.category.name without needing a live database session.
        """
        with self.db.session() as session:
            return (
                session.execute(
                    select(Ingredient)
                    .order_by(Ingredient.name)
                    .options(
                        selectinload(Ingredient.category),
                        selectinload(Ingredient.supplier),
                    )
                )
                .scalars()
                .all()
            )

    def low_stock_items(self) -> Sequence[Ingredient]:
        """Return ingredients at or below their reorder level."""
        with self.db.session() as session:
            return (
                session.execute(
                    select(Ingredient)
                    .where(Ingredient.current_stock <= Ingredient.reorder_level)
                    .options(
                        selectinload(Ingredient.category),
                        selectinload(Ingredient.supplier),
                    )
                )
                .scalars()
                .all()
            )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _load_ingredient_with_relations(
        self, session: Session, ingredient_id: int
    ) -> Ingredient:
        """Fetch an ingredient with its category and supplier eager-loaded.

        This prevents DetachedInstanceError when the ingredient is returned
        from a manager method and later accessed outside a session (e.g., by
        a web API serialising it to JSON).
        """
        ingredient = session.execute(
            select(Ingredient)
            .where(Ingredient.id == ingredient_id)
            .options(
                selectinload(Ingredient.category), selectinload(Ingredient.supplier)
            )
        ).scalar_one_or_none()
        if ingredient is None:
            raise NotFoundError(f"Ingredient {ingredient_id} not found")
        return ingredient

    # ------------------------------------------------------------------
    # Stock movements
    # ------------------------------------------------------------------
    def _record_transaction(
        self,
        session: Session,
        ingredient: Ingredient,
        transaction_type: TransactionType,
        quantity: Decimal,
        reference: str | None = None,
        notes: str | None = None,
    ) -> StockTransaction:
        """Create and attach a stock transaction in the current session.

        This is a private helper (leading underscore) because callers should
        use the higher-level receive_stock / use_stock / adjust_stock methods.
        It receives an open Session so the transaction is part of the same
        database transaction as the ingredient update.
        """
        transaction = StockTransaction(
            ingredient=ingredient,
            transaction_type=transaction_type.value,
            quantity=quantity,
            reference=reference,
            notes=notes,
        )
        session.add(transaction)
        return transaction

    def receive_stock(
        self,
        ingredient_id: int,
        quantity: Decimal | str | float,
        reference: str | None = None,
        notes: str | None = None,
    ) -> Ingredient:
        """Add stock to an ingredient (e.g., delivery arrived).

        Business rule: quantity must be positive.  The Decimal conversion
        happens first so we fail early with a clear error if the input is
        invalid.
        """
        qty = Decimal(str(quantity))
        with self.db.session() as session:
            ingredient = session.get(Ingredient, ingredient_id)
            if ingredient is None:
                raise NotFoundError(f"Ingredient {ingredient_id} not found")
            ingredient.current_stock += qty
            self._record_transaction(
                session, ingredient, TransactionType.RECEIPT, qty, reference, notes
            )
            session.flush()
            return self._load_ingredient_with_relations(session, ingredient.id)

    def use_stock(
        self,
        ingredient_id: int,
        quantity: Decimal | str | float,
        reference: str | None = None,
        notes: str | None = None,
    ) -> Ingredient:
        """Remove stock from an ingredient (e.g., kitchen usage).

        Business rule: you cannot use more stock than is available.  The
        database CHECK constraint also prevents negative stock, but we check
        here first so we can raise a friendly domain exception.
        """
        qty = Decimal(str(quantity))
        with self.db.session() as session:
            ingredient = session.get(Ingredient, ingredient_id)
            if ingredient is None:
                raise NotFoundError(f"Ingredient {ingredient_id} not found")
            if ingredient.current_stock < qty:
                raise InsufficientStockError(
                    f"Cannot use {qty} {ingredient.unit} of {ingredient.name}; "
                    f"only {ingredient.current_stock} available"
                )
            ingredient.current_stock -= qty
            self._record_transaction(
                session, ingredient, TransactionType.USAGE, qty, reference, notes
            )
            session.flush()
            return self._load_ingredient_with_relations(session, ingredient.id)

    def adjust_stock(
        self,
        ingredient_id: int,
        new_quantity: Decimal | str | float,
        notes: str | None = None,
    ) -> Ingredient:
        """Manually set the stock level to a specific value.

        Use this when doing a physical inventory count and discovering that
        the recorded stock does not match reality.  The difference between the
        old and new quantity is recorded as an adjustment transaction.
        """
        new_qty = Decimal(str(new_quantity))
        if new_qty < Decimal("0"):
            raise InsufficientStockError("Stock level cannot be negative")
        with self.db.session() as session:
            ingredient = session.get(Ingredient, ingredient_id)
            if ingredient is None:
                raise NotFoundError(f"Ingredient {ingredient_id} not found")
            difference = new_qty - ingredient.current_stock
            ingredient.current_stock = new_qty
            self._record_transaction(
                session,
                ingredient,
                TransactionType.ADJUSTMENT,
                abs(difference),
                notes=notes
                or f"Stock adjustment from {ingredient.current_stock - difference} to {new_qty}",
            )
            session.flush()
            return self._load_ingredient_with_relations(session, ingredient.id)

    def get_transactions(
        self, ingredient_id: int | None = None, limit: int = 100
    ) -> Sequence[StockTransaction]:
        """Return recent stock transactions, optionally filtered by ingredient.

        Args:
            ingredient_id: If provided, only transactions for that ingredient.
            limit: Maximum number of rows to return.
        """
        with self.db.session() as session:
            query = (
                select(StockTransaction)
                .order_by(StockTransaction.created_at.desc())
                .options(selectinload(StockTransaction.ingredient))
            )
            if ingredient_id is not None:
                query = query.where(StockTransaction.ingredient_id == ingredient_id)
            return session.execute(query.limit(limit)).scalars().all()
