"""Restaurant Inventory Management System.

This package exposes the public API of the inventory system.
Anything imported here can be used by other Python code (CLI, web API,
automated tests, Jupyter notebooks, etc.) without knowing the internal
file layout.

Example:
    >>> from inventory import InventoryManager
    >>> manager = InventoryManager()
    >>> category = manager.add_category("Produce")
"""

__version__ = "0.1.0"
__author__ = "Restaurant Inventory Team"

# Public API imports: these are the classes/functions we want consumers to use.
from .inventory import InventoryManager
from .models import Category, Ingredient, StockTransaction, Supplier

# __all__ tells IDEs and linters exactly what is considered public.
__all__ = [
    "InventoryManager",
    "Category",
    "Ingredient",
    "Supplier",
    "StockTransaction",
]
