"""Unit tests for the inventory manager."""

from decimal import Decimal

import pytest

from inventory import InventoryManager
from inventory.database import Database
from inventory.inventory import InsufficientStockError, NotFoundError


@pytest.fixture
def manager(tmp_path):
    """Provide an isolated InventoryManager using a temporary SQLite database."""
    db_path = tmp_path / "inventory.db"
    database = Database(
        __import__("inventory.config", fromlist=["Config"]).Config(
            database_url=f"sqlite:///{db_path}"
        )
    )
    database.create_tables()
    return InventoryManager(database)


class TestCategories:
    def test_add_and_get_category(self, manager):
        category = manager.add_category("Produce", "Fresh vegetables")
        fetched = manager.get_category(category.id)
        assert fetched.name == "Produce"
        assert fetched.description == "Fresh vegetables"

    def test_get_missing_category(self, manager):
        with pytest.raises(NotFoundError):
            manager.get_category(999)


class TestSuppliers:
    def test_add_and_get_supplier(self, manager):
        supplier = manager.add_supplier(
            "Green Valley", "Maria", "555-0101", "maria@example.com"
        )
        fetched = manager.get_supplier(supplier.id)
        assert fetched.name == "Green Valley"
        assert fetched.email == "maria@example.com"


class TestIngredients:
    def test_add_ingredient(self, manager):
        ingredient = manager.add_ingredient(
            sku="TOM-001",
            name="Tomato",
            unit="kg",
            current_stock="10.5",
            reorder_level="5",
            cost_per_unit="2.50",
        )
        assert ingredient.sku == "TOM-001"
        assert ingredient.current_stock == Decimal("10.5")
        assert ingredient.cost_per_unit == Decimal("2.50")

    def test_get_ingredient_by_sku(self, manager):
        manager.add_ingredient(sku="LET-001", name="Lettuce", unit="piece")
        fetched = manager.get_ingredient_by_sku("LET-001")
        assert fetched.name == "Lettuce"

    def test_low_stock_detection(self, manager):
        manager.add_ingredient(
            sku="LOW-001",
            name="Low Stock Item",
            unit="kg",
            current_stock="2",
            reorder_level="5",
        )
        low = manager.low_stock_items()
        assert len(low) == 1
        assert low[0].sku == "LOW-001"


class TestStockMovements:
    def test_receive_stock(self, manager):
        ingredient = manager.add_ingredient(
            sku="RICE-001", name="Rice", unit="kg", current_stock="10"
        )
        updated = manager.receive_stock(ingredient.id, "5")
        assert updated.current_stock == Decimal("15")

    def test_use_stock(self, manager):
        ingredient = manager.add_ingredient(
            sku="OIL-001", name="Oil", unit="liter", current_stock="10"
        )
        updated = manager.use_stock(ingredient.id, "3")
        assert updated.current_stock == Decimal("7")

    def test_use_stock_insufficient(self, manager):
        ingredient = manager.add_ingredient(
            sku="MIL-001", name="Milk", unit="liter", current_stock="2"
        )
        with pytest.raises(InsufficientStockError):
            manager.use_stock(ingredient.id, "5")

    def test_adjust_stock(self, manager):
        ingredient = manager.add_ingredient(
            sku="SUG-001", name="Sugar", unit="kg", current_stock="10"
        )
        updated = manager.adjust_stock(ingredient.id, "4")
        assert updated.current_stock == Decimal("4")

    def test_transactions_recorded(self, manager):
        ingredient = manager.add_ingredient(
            sku="FLO-001", name="Flour", unit="kg", current_stock="0"
        )
        manager.receive_stock(ingredient.id, "20", reference="PO-123")
        manager.use_stock(ingredient.id, "5")
        transactions = manager.get_transactions(ingredient.id)
        assert len(transactions) == 2
        assert transactions[0].transaction_type == "usage"
        assert transactions[1].transaction_type == "receipt"
