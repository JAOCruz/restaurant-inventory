/**
 * Restaurant Inventory Frontend
 *
 * This script is written in plain ("vanilla") JavaScript so it is easy to
 * teach and easy to read.  It connects the browser to the FastAPI backend.
 *
 * What it does:
 *   1. Loads categories, suppliers, ingredients, and recent transactions.
 *   2. Updates dashboard summary cards and the low-stock alert.
 *   3. Renders the inventory table with inline forms for stock operations.
 *   4. Sends HTTP requests to the API when the user performs actions.
 *   5. Shows toast notifications for success and error messages.
 */

const API_BASE = "";

// ---------------------------------------------------------------------------
// API helpers
// ---------------------------------------------------------------------------

async function apiGet(path) {
    const response = await fetch(`${API_BASE}${path}`);
    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: "Unknown error" }));
        throw new Error(error.detail || `HTTP ${response.status}`);
    }
    return response.json();
}

async function apiPost(path, body) {
    const response = await fetch(`${API_BASE}${path}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
    });
    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: "Unknown error" }));
        throw new Error(error.detail || `HTTP ${response.status}`);
    }
    return response.json();
}

// ---------------------------------------------------------------------------
// UI helpers
// ---------------------------------------------------------------------------

function showToast(message, type = "success") {
    const container = document.getElementById("toast-container");
    const toast = document.createElement("div");
    toast.className = `toast ${type}`;
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 4000);
}

function formatMoney(value) {
    if (value === null || value === undefined) return "-";
    return `$${parseFloat(value).toFixed(2)}`;
}

function formatDecimal(value) {
    return parseFloat(value).toFixed(3);
}

function formatDateTime(isoString) {
    if (!isoString) return "-";
    const date = new Date(isoString);
    return date.toLocaleString();
}

// Compute what percentage the current stock is of a sensible maximum.
// We use max(current_stock, reorder_level * 3, 1) so the bar never divides by
// zero and low-stock items still show a visible bar.
function stockPercent(current, reorder) {
    const max = Math.max(current, reorder * 3, 1);
    return Math.min(100, (current / max) * 100);
}

function stockBarClass(current, reorder) {
    if (current <= reorder) return "critical";
    if (current <= reorder * 1.5) return "low";
    return "good";
}

// ---------------------------------------------------------------------------
// Dashboard
// ---------------------------------------------------------------------------

function updateDashboard(ingredients, categories, suppliers) {
    document.getElementById("stat-total").textContent = ingredients.length;
    document.getElementById("stat-categories").textContent = categories.length;
    document.getElementById("stat-suppliers").textContent = suppliers.length;

    const lowCount = ingredients.filter((i) => i.needs_reorder).length;
    document.getElementById("stat-low").textContent = lowCount;

    const alert = document.getElementById("low-stock-alert");
    if (lowCount > 0) {
        alert.classList.remove("hidden");
        document.getElementById("low-stock-count").textContent = String(lowCount);
    } else {
        alert.classList.add("hidden");
    }
}

// ---------------------------------------------------------------------------
// Dropdowns
// ---------------------------------------------------------------------------

async function loadCategories() {
    const categories = await apiGet("/api/categories");
    const select = document.getElementById("category-select");
    for (const category of categories) {
        const option = document.createElement("option");
        option.value = category.id;
        option.textContent = category.name;
        select.appendChild(option);
    }
    return categories;
}

async function loadSuppliers() {
    const suppliers = await apiGet("/api/suppliers");
    const select = document.getElementById("supplier-select");
    for (const supplier of suppliers) {
        const option = document.createElement("option");
        option.value = supplier.id;
        option.textContent = supplier.name;
        select.appendChild(option);
    }
    return suppliers;
}

// ---------------------------------------------------------------------------
// Ingredient table
// ---------------------------------------------------------------------------

async function loadIngredients() {
    const ingredients = await apiGet("/api/ingredients");
    const tbody = document.getElementById("ingredients-body");
    tbody.innerHTML = "";

    if (ingredients.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" class="empty">No ingredients yet.</td></tr>';
        return ingredients;
    }

    for (const item of ingredients) {
        const row = document.createElement("tr");
        const percent = stockPercent(item.current_stock, item.reorder_level);
        const barClass = stockBarClass(item.current_stock, item.reorder_level);
        const statusBadge = item.needs_reorder
            ? '<span class="badge badge-low">LOW STOCK</span>'
            : '<span class="badge" style="background:#d1e7dd;color:#0f5132;">OK</span>';

        row.innerHTML = `
            <td><strong>${item.sku}</strong></td>
            <td>${item.name}</td>
            <td>${item.category ? item.category.name : "-"}</td>
            <td class="cell-stock">
                ${formatDecimal(item.current_stock)} ${item.unit}
                <div class="stock-bar-bg" title="${percent.toFixed(0)}% of reference level">
                    <div class="stock-bar-fill ${barClass}" style="width: ${percent}%"></div>
                </div>
            </td>
            <td>${formatDecimal(item.reorder_level)} ${item.unit}</td>
            <td>${formatMoney(item.cost_per_unit)}</td>
            <td>${statusBadge}</td>
            <td>
                <button class="small success" onclick="showReceiveForm(${item.id})">Receive</button>
                <button class="small warning" onclick="showUseForm(${item.id})">Use</button>
                <button class="small secondary" onclick="showAdjustForm(${item.id})">Adjust</button>
                <button class="small" onclick="viewTransactions(${item.id})">History</button>

                <!-- Inline receive form -->
                <div id="receive-form-${item.id}" class="inline-form">
                    <label>
                        Quantity
                        <input type="number" step="0.001" id="receive-qty-${item.id}" placeholder="10">
                    </label>
                    <label>
                        Reference
                        <input type="text" id="receive-ref-${item.id}" placeholder="PO-123">
                    </label>
                    <button class="small success" onclick="submitReceive(${item.id})">Save</button>
                    <button class="small secondary" onclick="hideForms(${item.id})">Cancel</button>
                </div>

                <!-- Inline use form -->
                <div id="use-form-${item.id}" class="inline-form">
                    <label>
                        Quantity
                        <input type="number" step="0.001" id="use-qty-${item.id}" placeholder="2.5">
                    </label>
                    <label>
                        Notes
                        <input type="text" id="use-notes-${item.id}" placeholder="Daily prep">
                    </label>
                    <button class="small warning" onclick="submitUse(${item.id})">Save</button>
                    <button class="small secondary" onclick="hideForms(${item.id})">Cancel</button>
                </div>

                <!-- Inline adjust form -->
                <div id="adjust-form-${item.id}" class="inline-form">
                    <label>
                        New Stock Level
                        <input type="number" step="0.001" id="adjust-qty-${item.id}" placeholder="8">
                    </label>
                    <label>
                        Notes
                        <input type="text" id="adjust-notes-${item.id}" placeholder="Inventory count">
                    </label>
                    <button class="small" onclick="submitAdjust(${item.id})">Save</button>
                    <button class="small secondary" onclick="hideForms(${item.id})">Cancel</button>
                </div>
            </td>
        `;
        tbody.appendChild(row);
    }
    return ingredients;
}

// ---------------------------------------------------------------------------
// Transactions table
// ---------------------------------------------------------------------------

async function loadTransactions(ingredientId = null) {
    const url = ingredientId
        ? `/api/ingredients/${ingredientId}/transactions?limit=10`
        : "/api/ingredients";

    let transactions;
    if (ingredientId) {
        transactions = await apiGet(url);
    } else {
        // Fetch recent transactions from the first few ingredients as a demo.
        const ingredients = await apiGet("/api/ingredients");
        const all = [];
        for (const ingredient of ingredients.slice(0, 5)) {
            const txs = await apiGet(`/api/ingredients/${ingredient.id}/transactions?limit=5`);
            all.push(...txs);
        }
        all.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
        transactions = all.slice(0, 10);
    }

    const tbody = document.getElementById("transactions-body");
    tbody.innerHTML = "";

    if (transactions.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="empty">No transactions yet.</td></tr>';
        return;
    }

    for (const t of transactions) {
        const row = document.createElement("tr");
        row.innerHTML = `
            <td>${t.id}</td>
            <td>${t.ingredient ? t.ingredient.name : t.ingredient_id}</td>
            <td>${t.transaction_type}</td>
            <td>${formatDecimal(t.quantity)}</td>
            <td>${t.reference || "-"}</td>
            <td>${formatDateTime(t.created_at)}</td>
        `;
        tbody.appendChild(row);
    }
}

// ---------------------------------------------------------------------------
// Inline form handlers
// ---------------------------------------------------------------------------

function hideForms(id) {
    document.getElementById(`receive-form-${id}`).classList.remove("active");
    document.getElementById(`use-form-${id}`).classList.remove("active");
    document.getElementById(`adjust-form-${id}`).classList.remove("active");
}

function showReceiveForm(id) {
    hideForms(id);
    document.getElementById(`receive-form-${id}`).classList.add("active");
}

function showUseForm(id) {
    hideForms(id);
    document.getElementById(`use-form-${id}`).classList.add("active");
}

function showAdjustForm(id) {
    hideForms(id);
    document.getElementById(`adjust-form-${id}`).classList.add("active");
}

async function submitReceive(id) {
    const qty = document.getElementById(`receive-qty-${id}`).value;
    const ref = document.getElementById(`receive-ref-${id}`).value;
    if (!qty) return;
    try {
        await apiPost(`/api/ingredients/${id}/receive`, {
            quantity: parseFloat(qty),
            reference: ref || null,
        });
        showToast("Stock received successfully.");
        await refreshAll();
    } catch (err) {
        showToast(err.message, "error");
    }
}

async function submitUse(id) {
    const qty = document.getElementById(`use-qty-${id}`).value;
    const notes = document.getElementById(`use-notes-${id}`).value;
    if (!qty) return;
    try {
        await apiPost(`/api/ingredients/${id}/use`, {
            quantity: parseFloat(qty),
            notes: notes || null,
        });
        showToast("Stock used successfully.");
        await refreshAll();
    } catch (err) {
        showToast(err.message, "error");
    }
}

async function submitAdjust(id) {
    const qty = document.getElementById(`adjust-qty-${id}`).value;
    const notes = document.getElementById(`adjust-notes-${id}`).value;
    if (!qty) return;
    try {
        await apiPost(`/api/ingredients/${id}/adjust`, {
            new_quantity: parseFloat(qty),
            notes: notes || null,
        });
        showToast("Stock adjusted successfully.");
        await refreshAll();
    } catch (err) {
        showToast(err.message, "error");
    }
}

async function viewTransactions(id) {
    await loadTransactions(id);
    showToast("Showing transaction history for ingredient " + id);
}

// Expose these to the inline onclick handlers.
window.showReceiveForm = showReceiveForm;
window.showUseForm = showUseForm;
window.showAdjustForm = showAdjustForm;
window.hideForms = hideForms;
window.submitReceive = submitReceive;
window.submitUse = submitUse;
window.submitAdjust = submitAdjust;
window.viewTransactions = viewTransactions;

// ---------------------------------------------------------------------------
// Add ingredient form
// ---------------------------------------------------------------------------

document.getElementById("add-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.target;
    const body = {
        sku: form.sku.value,
        name: form.name.value,
        unit: form.unit.value,
        category_id: form.category_id.value ? parseInt(form.category_id.value) : null,
        supplier_id: form.supplier_id.value ? parseInt(form.supplier_id.value) : null,
        current_stock: parseFloat(form.current_stock.value),
        reorder_level: parseFloat(form.reorder_level.value),
        reorder_quantity: 0,
        cost_per_unit: form.cost_per_unit.value ? parseFloat(form.cost_per_unit.value) : null,
    };
    try {
        await apiPost("/api/ingredients", body);
        showToast("Ingredient added successfully.");
        form.reset();
        await refreshAll();
    } catch (err) {
        showToast(err.message, "error");
    }
});

// ---------------------------------------------------------------------------
// Refresh everything
// ---------------------------------------------------------------------------

async function refreshAll() {
    const [ingredients, categories, suppliers] = await Promise.all([
        loadIngredients(),
        loadCategories(),
        loadSuppliers(),
    ]);
    updateDashboard(ingredients, categories, suppliers);
    await loadTransactions();
}

// ---------------------------------------------------------------------------
// Initialise
// ---------------------------------------------------------------------------

async function init() {
    await refreshAll();
}

init().catch((err) => {
    showToast(`Failed to load page: ${err.message}`, "error");
});
