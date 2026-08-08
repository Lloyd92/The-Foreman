import { spaceApiRequest } from "./spaceApi.js";


const RECORD_TYPES = new Set(["task", "project"]);
const TASK_LIFECYCLE_STATES = new Set([
    "open",
    "completed"
]);
const PROJECT_LIFECYCLE_STATES = new Set([
    "planning",
    "active",
    "on-hold",
    "completed",
    "archived"
]);
const TASK_PRIORITIES = new Set([
    "low",
    "medium",
    "high"
]);
const PROJECT_PRIORITIES = new Set([
    "low",
    "medium",
    "high",
    "urgent"
]);


function requireNullableString(value, path) {
    if (value !== null && typeof value !== "string") {
        throw new Error(`${path} must be a string or null.`);
    }
}


function validateWorkItem(item, index) {
    const path = `items[${index}]`;

    if (!item || typeof item !== "object" || Array.isArray(item)) {
        throw new Error(`${path} must be an object.`);
    }
    if (!RECORD_TYPES.has(item.recordType)) {
        throw new Error(`${path}.recordType is invalid.`);
    }
    if (typeof item.id !== "string" || !item.id) {
        throw new Error(`${path}.id must be a non-empty string.`);
    }
    if (typeof item.title !== "string" || !item.title) {
        throw new Error(`${path}.title must be a non-empty string.`);
    }
    const lifecycleStates = item.recordType === "task"
        ? TASK_LIFECYCLE_STATES
        : PROJECT_LIFECYCLE_STATES;
    const priorities = item.recordType === "task"
        ? TASK_PRIORITIES
        : PROJECT_PRIORITIES;

    if (!lifecycleStates.has(item.lifecycleState)) {
        throw new Error(
            `${path}.lifecycleState is invalid for ${item.recordType}.`
        );
    }
    if (!priorities.has(item.priority)) {
        throw new Error(
            `${path}.priority is invalid for ${item.recordType}.`
        );
    }
    if (
        typeof item.progress !== "number" ||
        !Number.isFinite(item.progress) ||
        item.progress < 0 ||
        item.progress > 100
    ) {
        throw new Error(`${path}.progress must be between 0 and 100.`);
    }

    for (const field of [
        "startDate",
        "targetDate",
        "dueDate",
        "responsibleMemberId",
        "projectId"
    ]) {
        requireNullableString(item[field], `${path}.${field}`);
    }

    if (item.recordType === "task") {
        if (item.startDate !== null || item.targetDate !== null) {
            throw new Error(
                `${path} Task startDate and targetDate must be null.`
            );
        }

        const expectedProgress =
            item.lifecycleState === "completed" ? 100 : 0;

        if (item.progress !== expectedProgress) {
            throw new Error(
                `${path}.progress does not match Task lifecycleState.`
            );
        }
    }

    if (item.recordType === "project") {
        if (item.dueDate !== null || item.projectId !== null) {
            throw new Error(
                `${path} Project dueDate and projectId must be null.`
            );
        }
    }

    if (
        typeof item.createdAt !== "string" ||
        typeof item.updatedAt !== "string"
    ) {
        throw new Error(`${path} timestamps are invalid.`);
    }

    return item;
}


function validateDependency(dependency, index) {
    const path = `dependencies[${index}]`;

    if (
        !dependency ||
        typeof dependency !== "object" ||
        Array.isArray(dependency)
    ) {
        throw new Error(`${path} must be an object.`);
    }

    for (const field of ["dependentType", "prerequisiteType"]) {
        if (!RECORD_TYPES.has(dependency[field])) {
            throw new Error(`${path}.${field} is invalid.`);
        }
    }

    for (const field of [
        "id",
        "dependentId",
        "prerequisiteId",
        "createdAt"
    ]) {
        if (
            typeof dependency[field] !== "string" ||
            !dependency[field]
        ) {
            throw new Error(`${path}.${field} must be non-empty.`);
        }
    }

    return dependency;
}


export function validateWorkResponse(response) {
    if (!response || typeof response !== "object") {
        throw new Error("Work response must be an object.");
    }
    if (!Array.isArray(response.items)) {
        throw new Error("Work response items must be an array.");
    }
    if (!Array.isArray(response.dependencies)) {
        throw new Error(
            "Work response dependencies must be an array."
        );
    }

    response.items.forEach(validateWorkItem);
    response.dependencies.forEach(validateDependency);

    return response;
}


export async function getWork() {
    return validateWorkResponse(
        await spaceApiRequest("/api/work")
    );
}
