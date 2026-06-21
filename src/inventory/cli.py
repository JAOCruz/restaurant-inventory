"""Command-line interface for the inventory system.

This file is the "adapter" between a human typing commands in a terminal and
 the InventoryManager.  It does not contain business logic; it only:

    1. Parses command-line arguments with the `argparse` module.
    2. Builds a Config and InventoryManager.
    3. Calls the right manager method.
    4. Prints the result or a friendly error message.

Why argparse?
    It is part of the Python standard library, so there are no extra
    dependencies.  It is also straightforward to extend: adding a new command
    means adding a new subparser and a new handler function.

How to add a new command:
    1. Write a `cmd_<command>` function that takes (args, manager) and returns
       an integer exit code (0 = success, non-zero = error).
    2. Register it in the `handlers` dictionary inside `main()`.
    3. Add a subparser in `build_parser()`.

Error exit codes:
    0 = success
    1 = not found
    2 = insufficient stock
    This makes it easy for shell scripts to react differently to each failure.
"""

import argparse
import sys
from decimal import Decimal

from .config import Config
from .database import Database
from .inventory import (
    InsufficientStockError,
    InventoryManager,
    NotFoundError,
)


def _fmt_money(value: Decimal | None) -> str:
    """Format a Decimal amount as dollars, or '-' when missing."""
    return f"${value:.2f}" if value is not None else "-"


def _print_table(headers: list[str], rows: list[list[str]]) -> None:
    """Print a simple text table to the terminal.

    This is a minimal formatting helper.  In a real web app, you would render
    an HTML table instead; the CLI just needs readable plain text.
    """
    if not rows:
        print("No records found.")
        return
    widths = [len(h) for h in headers]
    for row in rows:
        widths = [max(w, len(cell)) for w, cell in zip(widths, row, strict=True)]
    separator = "+-" + "-+-".join("-" * w for w in widths) + "-+"
    print(separator)
    print(
        "| "
        + " | ".join(h.ljust(w) for h, w in zip(headers, widths, strict=True))
        + " |"
    )
    print(separator)
    for row in rows:
        print(
            "| "
            + " | ".join(c.ljust(w) for c, w in zip(row, widths, strict=True))
            + " |"
        )
    print(separator)


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------
# Each handler receives the parsed argparse.Namespace and an InventoryManager.
# It returns an integer that becomes the process exit code.


def cmd_init(args: argparse.Namespace, manager: InventoryManager) -> int:
    """Initialize the database schema."""
    manager.db.create_tables()
    print("Database schema created successfully.")
    return 0


def cmd_add_category(args: argparse.Namespace, manager: InventoryManager) -> int:
    """Handle `inventory add-category <name> [--description ...]`."""
    category = manager.add_category(args.name, args.description)
    print(f"Created category: {category.name} (id={category.id})")
    return 0


def cmd_add_supplier(args: argparse.Namespace, manager: InventoryManager) -> int:
    """Handle `inventory add-supplier <name> [options]`."""
    supplier = manager.add_supplier(
        args.name, args.contact, args.phone, args.email, args.address
    )
    print(f"Created supplier: {supplier.name} (id={supplier.id})")
    return 0


def cmd_add_ingredient(args: argparse.Namespace, manager: InventoryManager) -> int:
    """Handle `inventory add-ingredient <sku> <name> <unit> [options]`."""
    ingredient = manager.add_ingredient(
        sku=args.sku,
        name=args.name,
        unit=args.unit,
        category_id=args.category,
        supplier_id=args.supplier,
        reorder_level=args.reorder_level,
        reorder_quantity=args.reorder_quantity,
        current_stock=args.current_stock,
        cost_per_unit=args.cost,
    )
    print(
        f"Created ingredient: {ingredient.name} (id={ingredient.id}, sku={ingredient.sku})"
    )
    return 0


def cmd_list_ingredients(args: argparse.Namespace, manager: InventoryManager) -> int:
    """Handle `inventory list-ingredients`."""
    ingredients = manager.list_ingredients()
    # Convert each Ingredient object into a list of strings for the table.
    rows = [
        [
            str(i.id),
            i.sku,
            i.name,
            i.category.name if i.category else "-",
            f"{i.current_stock} {i.unit}",
            f"{i.reorder_level} {i.unit}",
            _fmt_money(i.cost_per_unit),
            "YES" if i.needs_reorder else "NO",
        ]
        for i in ingredients
    ]
    _print_table(
        ["ID", "SKU", "Name", "Category", "Stock", "Reorder", "Cost/Unit", "Low?"],
        rows,
    )
    return 0


def cmd_low_stock(args: argparse.Namespace, manager: InventoryManager) -> int:
    """Handle `inventory low-stock`."""
    ingredients = manager.low_stock_items()
    rows = [
        [
            str(i.id),
            i.sku,
            i.name,
            f"{i.current_stock} {i.unit}",
            f"{i.reorder_level} {i.unit}",
            f"{i.reorder_quantity} {i.unit}",
        ]
        for i in ingredients
    ]
    _print_table(["ID", "SKU", "Name", "Stock", "Reorder Level", "Reorder Qty"], rows)
    return 0


def cmd_receive(args: argparse.Namespace, manager: InventoryManager) -> int:
    """Handle `inventory receive <ingredient_id> <quantity> [options]`."""
    ingredient = manager.receive_stock(
        args.ingredient, args.quantity, args.reference, args.notes
    )
    print(
        f"Received {args.quantity} {ingredient.unit} of {ingredient.name}. "
        f"New stock: {ingredient.current_stock} {ingredient.unit}"
    )
    return 0


def cmd_use(args: argparse.Namespace, manager: InventoryManager) -> int:
    """Handle `inventory use <ingredient_id> <quantity> [options]`."""
    ingredient = manager.use_stock(
        args.ingredient, args.quantity, args.reference, args.notes
    )
    print(
        f"Used {args.quantity} {ingredient.unit} of {ingredient.name}. "
        f"Remaining stock: {ingredient.current_stock} {ingredient.unit}"
    )
    return 0


def cmd_adjust(args: argparse.Namespace, manager: InventoryManager) -> int:
    """Handle `inventory adjust <ingredient_id> <new_quantity> [options]`."""
    ingredient = manager.adjust_stock(args.ingredient, args.quantity, args.notes)
    print(
        f"Adjusted {ingredient.name} stock to {ingredient.current_stock} {ingredient.unit}"
    )
    return 0


def cmd_transactions(args: argparse.Namespace, manager: InventoryManager) -> int:
    """Handle `inventory transactions [--ingredient id] [--limit n]`."""
    transactions = manager.get_transactions(args.ingredient, args.limit)
    rows = [
        [
            str(t.id),
            str(t.ingredient_id),
            t.ingredient.name,
            t.transaction_type,
            str(t.quantity),
            t.reference or "-",
            t.created_at.strftime("%Y-%m-%d %H:%M") if t.created_at else "-",
        ]
        for t in transactions
    ]
    _print_table(
        ["ID", "Ingredient ID", "Ingredient", "Type", "Qty", "Reference", "When"],
        rows,
    )
    return 0


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------
# argparse lets us define subcommands (`init`, `add-category`, `receive`, ...)
# with their own positional and optional arguments.


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="inventory",
        description="Restaurant inventory management system.",
    )
    parser.add_argument(
        "--database-url",
        default=None,
        help="Override the DATABASE_URL environment variable.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable SQL echoing for debugging.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # init
    subparsers.add_parser("init", help="Create the database schema")

    # category
    cat = subparsers.add_parser("add-category", help="Add an ingredient category")
    cat.add_argument("name")
    cat.add_argument("--description", default=None)

    # supplier
    sup = subparsers.add_parser("add-supplier", help="Add a supplier")
    sup.add_argument("name")
    sup.add_argument("--contact", default=None)
    sup.add_argument("--phone", default=None)
    sup.add_argument("--email", default=None)
    sup.add_argument("--address", default=None)

    # ingredient
    ing = subparsers.add_parser("add-ingredient", help="Add an ingredient")
    ing.add_argument("sku")
    ing.add_argument("name")
    ing.add_argument("unit")
    ing.add_argument("--category", type=int, default=None)
    ing.add_argument("--supplier", type=int, default=None)
    ing.add_argument("--reorder-level", type=Decimal, default="0")
    ing.add_argument("--reorder-quantity", type=Decimal, default="0")
    ing.add_argument("--current-stock", type=Decimal, default="0")
    ing.add_argument("--cost", type=Decimal, default=None)

    # list
    subparsers.add_parser("list-ingredients", help="List all ingredients")

    # low stock
    subparsers.add_parser("low-stock", help="List ingredients below reorder level")

    # receive
    rec = subparsers.add_parser("receive", help="Receive stock")
    rec.add_argument("ingredient", type=int)
    rec.add_argument("quantity", type=Decimal)
    rec.add_argument("--reference", default=None)
    rec.add_argument("--notes", default=None)

    # use
    use = subparsers.add_parser("use", help="Use/remove stock")
    use.add_argument("ingredient", type=int)
    use.add_argument("quantity", type=Decimal)
    use.add_argument("--reference", default=None)
    use.add_argument("--notes", default=None)

    # adjust
    adj = subparsers.add_parser("adjust", help="Adjust stock to a specific level")
    adj.add_argument("ingredient", type=int)
    adj.add_argument("quantity", type=Decimal)
    adj.add_argument("--notes", default=None)

    # transactions
    tx = subparsers.add_parser("transactions", help="Show recent stock transactions")
    tx.add_argument("--ingredient", type=int, default=None)
    tx.add_argument("--limit", type=int, default=100)

    return parser


def main(argv: list[str] | None = None) -> int:
    """Entry point for the CLI.

    This function is called by `python -m inventory` and by the `inventory`
    console script defined in pyproject.toml.
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    # Map subcommand names to the functions that handle them.
    handlers = {
        "init": cmd_init,
        "add-category": cmd_add_category,
        "add-supplier": cmd_add_supplier,
        "add-ingredient": cmd_add_ingredient,
        "list-ingredients": cmd_list_ingredients,
        "low-stock": cmd_low_stock,
        "receive": cmd_receive,
        "use": cmd_use,
        "adjust": cmd_adjust,
        "transactions": cmd_transactions,
    }

    # Build a fresh Config from CLI flags and environment variables.
    env = {
        "DATABASE_URL": args.database_url or Config.from_env().database_url,
        "DEBUG": "true" if args.debug else "false",
        "LOG_LEVEL": "DEBUG" if args.debug else "INFO",
    }

    config = Config(
        database_url=env["DATABASE_URL"],
        debug=env["DEBUG"].lower() == "true",
        log_level=env["LOG_LEVEL"],
    )
    manager = InventoryManager(Database(config))

    try:
        return handlers[args.command](args, manager)
    except NotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except InsufficientStockError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
