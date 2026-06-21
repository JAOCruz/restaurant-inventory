# Web App Example

This directory contains a minimal but complete web application built with
**FastAPI** and a vanilla JavaScript frontend.  It uses the exact same
`InventoryManager` as the CLI, demonstrating how the core business logic is
independent of the user interface.

## What you will learn here

- How to expose `InventoryManager` methods as HTTP endpoints.
- How Pydantic schemas separate the API contract from the database models.
- How a browser frontend calls the backend with `fetch()`.
- How the backend returns JSON that the frontend renders into HTML.

## Files

```
web/
├── api.py              # FastAPI application and routes
├── schemas.py          # Pydantic request/response models
├── requirements.txt    # Extra dependencies for the web app
├── README.md           # This file
└── static/
    ├── index.html      # Single-page frontend
    └── app.js          # Frontend logic
```

## Run the web app

From the project root:

```bash
cd web
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# The PYTHONPATH must include the src/ directory so the API can import inventory.
export PYTHONPATH=../src
uvicorn api:app --reload
```

Open your browser:

- Frontend: http://localhost:8000
- Interactive API docs: http://localhost:8000/docs

## API endpoints

| Method | Endpoint | Description |
| ------ | -------- | ----------- |
| GET | `/` | Serve the HTML frontend |
| GET | `/api/categories` | List categories |
| POST | `/api/categories` | Create a category |
| GET | `/api/suppliers` | List suppliers |
| POST | `/api/suppliers` | Create a supplier |
| GET | `/api/ingredients` | List ingredients |
| POST | `/api/ingredients` | Create an ingredient |
| GET | `/api/ingredients/{id}` | Get one ingredient |
| GET | `/api/ingredients/{id}/transactions` | List transactions for an ingredient |
| POST | `/api/ingredients/{id}/receive` | Receive stock |
| POST | `/api/ingredients/{id}/use` | Use stock |
| POST | `/api/ingredients/{id}/adjust` | Adjust stock |

## Example API call with curl

```bash
curl -X POST http://localhost:8000/api/categories \
  -H "Content-Type: application/json" \
  -d '{"name": "Produce"}'

curl -X POST http://localhost:8000/api/ingredients \
  -H "Content-Type: application/json" \
  -d '{
    "sku": "TOM-001",
    "name": "Roma Tomatoes",
    "unit": "kg",
    "category_id": 1,
    "current_stock": 12.5,
    "reorder_level": 5
  }'

curl -X POST http://localhost:8000/api/ingredients/1/receive \
  -H "Content-Type: application/json" \
  -d '{"quantity": 10, "reference": "PO-123"}'
```

## How the frontend connects to the backend

1. The browser loads `index.html` from the root path `/`.
2. `index.html` loads `app.js` from `/static/app.js`.
3. `app.js` calls `fetch("/api/ingredients")` to get JSON data.
4. FastAPI receives the request, calls `InventoryManager.list_ingredients()`,
   and returns JSON.
5. `app.js` parses the JSON and updates the HTML table.

No page reloads are required after the initial load.
