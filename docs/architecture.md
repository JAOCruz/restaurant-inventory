# Architecture

This document explains the architecture of the restaurant inventory system
using visual diagrams.

## High-level system architecture

```mermaid
flowchart TB
    subgraph "User Interfaces"
        CLI["CLI<br/>python -m inventory"]
        WEB["Web App<br/>FastAPI + HTML/JS"]
        TESTS["Tests<br/>pytest"]
    end

    subgraph "Application Core"
        MANAGER["InventoryManager<br/>Business logic"]
        DB["Database<br/>Engine & sessions"]
    end

    subgraph "Storage"
        SQLITE[(SQLite<br/>local dev)]
        POSTGRES[(PostgreSQL<br/>Docker / prod)]
    end

    CLI --> MANAGER
    WEB --> MANAGER
    TESTS --> MANAGER
    MANAGER --> DB
    DB --> SQLITE
    DB --> POSTGRES
```

The diagram shows that the user interface (CLI, web, tests) never talks to the
database directly.  All data access goes through `InventoryManager`, which
keeps business rules in one place.

## Database entity-relationship diagram

```mermaid
erDiagram
    CATEGORY ||--o{ INGREDIENT : groups
    SUPPLIER ||--o{ INGREDIENT : supplies
    INGREDIENT ||--o{ STOCK_TRANSACTION : has

    CATEGORY {
        int id PK
        string name "unique"
        text description
    }

    SUPPLIER {
        int id PK
        string name
        string contact_name
        string phone
        string email
        text address
    }

    INGREDIENT {
        int id PK
        string sku "unique"
        string name
        int category_id FK
        int supplier_id FK
        string unit
        decimal reorder_level
        decimal reorder_quantity
        decimal current_stock
        decimal cost_per_unit
        datetime created_at
        datetime updated_at
    }

    STOCK_TRANSACTION {
        int id PK
        int ingredient_id FK
        string transaction_type
        decimal quantity
        string reference
        text notes
        datetime created_at
    }
```

- A **Category** groups many **Ingredients**.
- A **Supplier** supplies many **Ingredients**.
- An **Ingredient** has many **StockTransactions** (its audit trail).

## Sequence diagram: receiving stock

This diagram shows what happens when the web API receives a `POST
/api/ingredients/1/receive` request.

```mermaid
sequenceDiagram
    participant Browser
    participant FastAPI as FastAPI route
    participant Manager as InventoryManager
    participant DB as Database.session()
    participant SQL as SQL database

    Browser->>FastAPI: POST /api/ingredients/1/receive<br/>{ "quantity": 10 }
    FastAPI->>Manager: receive_stock(1, 10)
    Manager->>DB: open session
    DB->>SQL: SELECT ingredient WHERE id=1
    SQL-->>DB: Ingredient row
    DB-->>Manager: Ingredient object
    Manager->>Manager: current_stock += 10
    Manager->>DB: create StockTransaction
    DB->>SQL: INSERT transaction
    Manager->>DB: flush + refresh
    DB->>SQL: UPDATE ingredient
    DB-->>Manager: updated Ingredient
    Manager-->>FastAPI: Ingredient object
    FastAPI-->>Browser: 200 OK + JSON
```

Notice that the whole operation is one database transaction.  If anything
fails, the context manager rolls back both the stock update and the audit row,
keeping the data consistent.

## Frontend / backend request flow

```mermaid
sequenceDiagram
    participant User
    participant FE as Browser (HTML/JS)
    participant BE as FastAPI backend
    participant DB as Database

    User->>FE: clicks "Receive 10 kg"
    FE->>FE: build JSON body { quantity: 10 }
    FE->>BE: fetch POST /api/ingredients/1/receive
    BE->>BE: parse JSON with Pydantic
    BE->>DB: InventoryManager.receive_stock(1, 10)
    DB-->>BE: updated ingredient
    BE->>BE: convert to JSON response
    BE-->>FE: 200 OK + ingredient JSON
    FE->>FE: update DOM (show new stock)
    FE-->>User: page shows new stock level
```

This is the typical modern web-app pattern:

1. The browser sends JSON over HTTP.
2. The backend validates the JSON, runs business logic, and talks to the DB.
3. The backend returns JSON.
4. The browser updates the page without reloading it.

## Layered code organisation

```mermaid
flowchart LR
    subgraph "Presentation"
        CLI_LAYER["src/inventory/cli.py"]
        WEB_LAYER["web/api.py"]
    end

    subgraph "Application"
        SERVICE["src/inventory/inventory.py"]
    end

    subgraph "Data"
        DATABASE["src/inventory/database.py"]
        MODELS["src/inventory/models.py"]
    end

    subgraph "Config"
        CONFIG["src/inventory/config.py"]
    end

    CLI_LAYER --> SERVICE
    WEB_LAYER --> SERVICE
    SERVICE --> DATABASE
    DATABASE --> MODELS
    CONFIG --> DATABASE
    CONFIG --> WEB_LAYER
```

Each arrow means "depends on" or "uses".  The important rule is that arrows
only point downward: the CLI depends on the service layer, but the service
layer does not depend on the CLI.  This is what makes the code easy to test and
reuse.
