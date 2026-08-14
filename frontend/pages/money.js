import {
    createMoneyAccount,
    createMoneyBudget,
    createMoneyCategory,
    createMoneyObligation,
    createMoneyTransaction,
    deleteMoneyAccount,
    deleteMoneyBudget,
    deleteMoneyCategory,
    deleteMoneyObligation,
    deleteMoneyTransaction,
    listMoneyAccounts,
    listMoneyBudgets,
    listMoneyCategories,
    listMoneyObligations,
    listMoneyTransactions
} from "../utils/moneyApi.js";


let moneyInitialized = false;
let state = {
    accounts: [],
    categories: [],
    transactions: [],
    budgets: [],
    obligations: []
};


function clean(value) {
    return String(value ?? "").trim();
}


function minorUnits(value) {
    const number = Number(value);
    return Number.isFinite(number)
        ? Math.round(number * 100)
        : 0;
}


function formatMoney(value, currency = "USD") {
    return new Intl.NumberFormat(
        undefined,
        {
            style: "currency",
            currency
        }
    ).format((Number(value) || 0) / 100);
}


function setMessage(message, isError = false) {
    const element = document.getElementById("money-page-message");

    if (!element) {
        return;
    }

    element.textContent = message;
    element.classList.toggle("error", isError);
}


function option(value, label, isDefault = false) {
    const element = document.createElement("option");
    element.value = value;
    element.textContent = label;
    element.defaultSelected = isDefault;
    element.selected = isDefault;
    return element;
}


function refreshReferenceSelects() {
    const accountSelect = document.getElementById(
        "money-transaction-account"
    );
    const categorySelects = [
        document.getElementById("money-transaction-category"),
        document.getElementById("money-budget-category"),
        document.getElementById("money-obligation-category")
    ];
    const obligationAccount = document.getElementById(
        "money-obligation-account"
    );

    if (accountSelect) {
        accountSelect.replaceChildren(
            option("", "Choose account…", true),
            ...state.accounts.map(account => (
                option(account.id, account.name)
            ))
        );
    }

    if (obligationAccount) {
        obligationAccount.replaceChildren(
            option("", "No account", true),
            ...state.accounts.map(account => (
                option(account.id, account.name)
            ))
        );
    }

    for (const select of categorySelects) {
        if (!select) {
            continue;
        }

        select.replaceChildren(
            option("", "No category", true),
            ...state.categories.map(category => (
                option(
                    category.id,
                    `${category.name} (${category.kind})`
                )
            ))
        );
    }
}


function renderRows(id, records, rowBuilder) {
    const body = document.getElementById(id);

    if (!body) {
        return;
    }

    body.replaceChildren();

    for (const record of records) {
        body.appendChild(rowBuilder(record));
    }
}


function actionButton(type, id) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "table-action-button resource-delete-button";
    button.dataset.moneyDelete = type;
    button.dataset.id = id;
    button.textContent = "Delete";
    return button;
}


function renderMoney() {
    renderRows(
        "money-accounts-body",
        state.accounts,
        account => {
            const row = document.createElement("tr");
            row.innerHTML = `
                <td></td><td></td><td></td><td></td><td></td>
            `;
            row.children[0].textContent = account.name;
            row.children[1].textContent = account.kind;
            row.children[2].textContent = formatMoney(
                account.openingBalanceMinor,
                account.currencyCode
            );
            row.children[3].textContent = account.isActive
                ? "Active"
                : "Inactive";
            row.children[4].appendChild(
                actionButton("account", account.id)
            );
            return row;
        }
    );

    renderRows(
        "money-categories-body",
        state.categories,
        category => {
            const row = document.createElement("tr");
            row.innerHTML = `<td></td><td></td><td></td>`;
            row.children[0].textContent = category.name;
            row.children[1].textContent = category.kind;
            row.children[2].appendChild(
                actionButton("category", category.id)
            );
            return row;
        }
    );

    renderRows(
        "money-transactions-body",
        state.transactions,
        transaction => {
            const row = document.createElement("tr");
            row.innerHTML = `
                <td></td><td></td><td></td><td></td><td></td>
            `;
            row.children[0].textContent = transaction.occurredOn;
            row.children[1].textContent = transaction.description;
            row.children[2].textContent = transaction.kind;
            row.children[3].textContent = formatMoney(
                transaction.amountMinor,
                transaction.currencyCode
            );
            row.children[4].appendChild(
                actionButton("transaction", transaction.id)
            );
            return row;
        }
    );

    renderRows(
        "money-budgets-body",
        state.budgets,
        budget => {
            const row = document.createElement("tr");
            row.innerHTML = `
                <td></td><td></td><td></td><td></td>
            `;
            row.children[0].textContent = budget.name;
            row.children[1].textContent = formatMoney(
                budget.amountMinor,
                budget.currencyCode
            );
            row.children[2].textContent =
                `${budget.startDate} – ${budget.endDate}`;
            row.children[3].appendChild(
                actionButton("budget", budget.id)
            );
            return row;
        }
    );

    renderRows(
        "money-obligations-body",
        state.obligations,
        obligation => {
            const row = document.createElement("tr");
            row.innerHTML = `
                <td></td><td></td><td></td><td></td>
            `;
            row.children[0].textContent = obligation.name;
            row.children[1].textContent = formatMoney(
                obligation.amountMinor,
                obligation.currencyCode
            );
            row.children[2].textContent =
                obligation.intervalValue === 1
                    ? obligation.frequency
                    : (
                        `Every ${obligation.intervalValue} ` +
                        obligation.frequency
                    );
            row.children[3].appendChild(
                actionButton("obligation", obligation.id)
            );
            return row;
        }
    );

    refreshReferenceSelects();
}


async function loadMoney() {
    const [
        accounts,
        categories,
        transactions,
        budgets,
        obligations
    ] = await Promise.all([
        listMoneyAccounts(),
        listMoneyCategories(),
        listMoneyTransactions(),
        listMoneyBudgets(),
        listMoneyObligations()
    ]);

    state = {
        accounts,
        categories,
        transactions,
        budgets,
        obligations
    };

    renderMoney();
}


async function submitAccount(form) {
    const data = new FormData(form);

    await createMoneyAccount({
        name: clean(data.get("name")),
        kind: clean(data.get("kind")),
        currencyCode: "USD",
        openingBalanceMinor: minorUnits(
            data.get("openingBalance")
        ),
        notes: clean(data.get("notes"))
    });
}


async function submitCategory(form) {
    const data = new FormData(form);

    await createMoneyCategory({
        name: clean(data.get("name")),
        kind: clean(data.get("kind"))
    });
}


async function submitTransaction(form) {
    const data = new FormData(form);
    const categoryId = clean(data.get("categoryId"));

    await createMoneyTransaction({
        accountId: clean(data.get("accountId")),
        categoryId: categoryId || null,
        kind: clean(data.get("kind")),
        amountMinor: minorUnits(data.get("amount")),
        currencyCode: "USD",
        occurredOn: clean(data.get("occurredOn")),
        description: clean(data.get("description")),
        counterparty: clean(data.get("counterparty")),
        notes: clean(data.get("notes"))
    });
}


async function submitBudget(form) {
    const data = new FormData(form);
    const categoryId = clean(data.get("categoryId"));

    await createMoneyBudget({
        categoryId: categoryId || null,
        name: clean(data.get("name")),
        amountMinor: minorUnits(data.get("amount")),
        currencyCode: "USD",
        startDate: clean(data.get("startDate")),
        endDate: clean(data.get("endDate")),
        notes: clean(data.get("notes"))
    });
}


async function submitObligation(form) {
    const data = new FormData(form);
    const accountId = clean(data.get("accountId"));
    const categoryId = clean(data.get("categoryId"));

    await createMoneyObligation({
        accountId: accountId || null,
        categoryId: categoryId || null,
        name: clean(data.get("name")),
        amountMinor: minorUnits(data.get("amount")),
        currencyCode: "USD",
        frequency: clean(data.get("frequency")),
        intervalValue: Number(data.get("intervalValue")) || 1,
        startDate: clean(data.get("startDate")),
        endDate: clean(data.get("endDate")) || null,
        notes: clean(data.get("notes"))
    });
}


const submitters = {
    "money-account-form": submitAccount,
    "money-category-form": submitCategory,
    "money-transaction-form": submitTransaction,
    "money-budget-form": submitBudget,
    "money-obligation-form": submitObligation
};


const deleters = {
    account: deleteMoneyAccount,
    category: deleteMoneyCategory,
    transaction: deleteMoneyTransaction,
    budget: deleteMoneyBudget,
    obligation: deleteMoneyObligation
};


function bindForms() {
    for (const [id, submitter] of Object.entries(submitters)) {
        const form = document.getElementById(id);

        form?.addEventListener("submit", async event => {
            event.preventDefault();

            try {
                await submitter(form);
                form.reset();
                await loadMoney();
                setMessage("Money record saved.");
            } catch (error) {
                console.error("Money record save failed:", error);
                setMessage("Unable to save Money record.", true);
            }
        });
    }
}


function bindDeletes() {
    document.addEventListener("click", async event => {
        const button = event.target.closest("[data-money-delete]");

        if (!button) {
            return;
        }

        const deleter = deleters[button.dataset.moneyDelete];

        if (!deleter) {
            return;
        }

        try {
            await deleter(button.dataset.id);
            await loadMoney();
            setMessage("Money record deleted.");
        } catch (error) {
            console.error("Money record delete failed:", error);
            setMessage("Unable to delete Money record.", true);
        }
    });
}


export async function initializeMoneyPage() {
    if (moneyInitialized) {
        return {
            status: "already-initialized"
        };
    }

    moneyInitialized = true;
    bindForms();
    bindDeletes();

    try {
        await loadMoney();
        return {
            status: "complete"
        };
    } catch (error) {
        console.error("Money initialization failed:", error);
        setMessage("Money records are currently unavailable.", true);

        return {
            status: "unavailable",
            error
        };
    }
}
