import { listModules } from "./modulesApi.js";


const CONTRIBUTION_LOCATIONS = new Set([
    "today",
    "calendar",
    "work",
    "resources",
    "money",
    "library",
    "settings"
]);

let modulesById = null;


function requireString(value, path) {
    if (typeof value !== "string" || !value.trim()) {
        throw new TypeError(`${path} must be a nonempty string.`);
    }

    return value.trim();
}


function requireStringArray(value, path) {
    if (!Array.isArray(value)) {
        throw new TypeError(`${path} must be an array.`);
    }

    const normalized = value.map((item, index) => (
        requireString(item, `${path}[${index}]`)
    ));

    if (normalized.length !== new Set(normalized).size) {
        throw new TypeError(`${path} must contain unique values.`);
    }

    return normalized;
}


function validateModule(value, index) {
    const path = `modules[${index}]`;

    if (!value || typeof value !== "object" || Array.isArray(value)) {
        throw new TypeError(`${path} must be an object.`);
    }

    const moduleId = requireString(value.moduleId, `${path}.moduleId`)
        .toLowerCase();
    const name = requireString(value.name, `${path}.name`);
    const description = typeof value.description === "string"
        ? value.description
        : null;
    const dependencies = requireStringArray(
        value.dependencies,
        `${path}.dependencies`
    ).map(dependency => dependency.toLowerCase());

    if (dependencies.length !== new Set(dependencies).size) {
        throw new TypeError(
            `${path}.dependencies must be canonically unique.`
        );
    }

    const contributionLocations = requireStringArray(
        value.contributionLocations,
        `${path}.contributionLocations`
    );

    contributionLocations.forEach(location => {
        if (!CONTRIBUTION_LOCATIONS.has(location)) {
            throw new TypeError(
                `${path}.contributionLocations contains an unknown location.`
            );
        }
    });

    if (typeof value.defaultEnabled !== "boolean") {
        throw new TypeError(`${path}.defaultEnabled must be boolean.`);
    }

    if (typeof value.enabled !== "boolean") {
        throw new TypeError(`${path}.enabled must be boolean.`);
    }

    if (value.safeEnableRule !== "dependencies-satisfied") {
        throw new TypeError(`${path}.safeEnableRule is unsupported.`);
    }

    if (value.safeDisableRule !== "no-enabled-dependents") {
        throw new TypeError(`${path}.safeDisableRule is unsupported.`);
    }

    if (value.dataRetentionBehavior !== "retain") {
        throw new TypeError(
            `${path}.dataRetentionBehavior is unsupported.`
        );
    }

    if (value.health !== "ready") {
        throw new TypeError(`${path}.health is unsupported.`);
    }

    return Object.freeze({
        moduleId,
        name,
        description,
        dependencies: Object.freeze(dependencies),
        contributionLocations: Object.freeze(
            contributionLocations
        ),
        safeEnableRule: value.safeEnableRule,
        safeDisableRule: value.safeDisableRule,
        dataRetentionBehavior: value.dataRetentionBehavior,
        defaultEnabled: value.defaultEnabled,
        enabled: value.enabled,
        health: value.health
    });
}


export function setModuleRegistry(value) {
    if (!Array.isArray(value)) {
        throw new TypeError("Module registry response must be an array.");
    }

    const modules = value.map(validateModule);
    const nextModulesById = new Map();

    modules.forEach(module => {
        if (nextModulesById.has(module.moduleId)) {
            throw new TypeError(
                `Duplicate module identifier: ${module.moduleId}.`
            );
        }

        nextModulesById.set(module.moduleId, module);
    });

    modules.forEach(module => {
        module.dependencies.forEach(dependencyId => {
            if (!nextModulesById.has(dependencyId)) {
                throw new TypeError(
                    `Module ${module.moduleId} has an unknown dependency.`
                );
            }
        });
    });

    modulesById = nextModulesById;
    return getModules();
}


export async function initializeModuleContext() {
    return setModuleRegistry(await listModules());
}


export function clearModuleContext() {
    modulesById = null;
}


export function getModules() {
    return modulesById
        ? Object.freeze([...modulesById.values()])
        : Object.freeze([]);
}


export function getModule(moduleId) {
    if (!modulesById || typeof moduleId !== "string") {
        return null;
    }

    return modulesById.get(moduleId.trim().toLowerCase()) ?? null;
}


export function isModuleEnabled(moduleId) {
    return getModule(moduleId)?.enabled === true;
}
