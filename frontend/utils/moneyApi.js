import { spaceApiRequest } from "./spaceApi.js";


function jsonOptions(method, data) {
    return {
        method,
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(data)
    };
}


export function listMoneyAccounts() {
    return spaceApiRequest("/api/money/accounts");
}

export function createMoneyAccount(data) {
    return spaceApiRequest(
        "/api/money/accounts",
        jsonOptions("POST", data)
    );
}

export function updateMoneyAccount(accountId, data) {
    return spaceApiRequest(
        `/api/money/accounts/${accountId}`,
        jsonOptions("PATCH", data)
    );
}

export function deleteMoneyAccount(accountId) {
    return spaceApiRequest(
        `/api/money/accounts/${accountId}`,
        { method: "DELETE" }
    );
}


export function listMoneyCategories() {
    return spaceApiRequest("/api/money/categories");
}

export function createMoneyCategory(data) {
    return spaceApiRequest(
        "/api/money/categories",
        jsonOptions("POST", data)
    );
}

export function deleteMoneyCategory(categoryId) {
    return spaceApiRequest(
        `/api/money/categories/${categoryId}`,
        { method: "DELETE" }
    );
}


export function listMoneyTransactions() {
    return spaceApiRequest("/api/money/transactions");
}

export function createMoneyTransaction(data) {
    return spaceApiRequest(
        "/api/money/transactions",
        jsonOptions("POST", data)
    );
}

export function deleteMoneyTransaction(transactionId) {
    return spaceApiRequest(
        `/api/money/transactions/${transactionId}`,
        { method: "DELETE" }
    );
}


export function listMoneyBudgets() {
    return spaceApiRequest("/api/money/budgets");
}

export function createMoneyBudget(data) {
    return spaceApiRequest(
        "/api/money/budgets",
        jsonOptions("POST", data)
    );
}

export function deleteMoneyBudget(budgetId) {
    return spaceApiRequest(
        `/api/money/budgets/${budgetId}`,
        { method: "DELETE" }
    );
}


export function listMoneyObligations() {
    return spaceApiRequest("/api/money/obligations");
}

export function createMoneyObligation(data) {
    return spaceApiRequest(
        "/api/money/obligations",
        jsonOptions("POST", data)
    );
}

export function deleteMoneyObligation(obligationId) {
    return spaceApiRequest(
        `/api/money/obligations/${obligationId}`,
        { method: "DELETE" }
    );
}
