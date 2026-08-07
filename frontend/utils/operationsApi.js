import { spaceApiRequest } from "./spaceApi.js";


export const OPERATIONAL_FACT_TYPES = Object.freeze({
    projectLifecycle: "project.lifecycle",
    projectMaterialReadiness: "project.material-readiness",
    taskWorkState: "task.work-state",
    inventoryStockLevel: "inventory.stock-level"
});

const FACT_RULES = Object.freeze({
    [OPERATIONAL_FACT_TYPES.projectLifecycle]: {
        subjectType: "project",
        states: new Set([
            "planning",
            "active",
            "on-hold",
            "completed",
            "archived",
            "invalid"
        ])
    },
    [OPERATIONAL_FACT_TYPES.projectMaterialReadiness]: {
        subjectType: "project",
        states: new Set([
            "ready",
            "needs-materials",
            "not-applicable",
            "invalid"
        ])
    },
    [OPERATIONAL_FACT_TYPES.taskWorkState]: {
        subjectType: "task",
        states: new Set(["open", "completed"])
    },
    [OPERATIONAL_FACT_TYPES.inventoryStockLevel]: {
        subjectType: "inventory",
        states: new Set([
            "in-stock",
            "low-stock",
            "out-of-stock",
            "invalid"
        ])
    }
});

const SUMMARY_SECTIONS = Object.freeze({
    "projects.byStatus": [
        "planning",
        "active",
        "onHold",
        "completed",
        "archived",
        "invalid"
    ],
    "projects.materialReadiness": [
        "ready",
        "needsMaterials",
        "notApplicable",
        "invalid"
    ],
    "tasks": ["open", "completed"],
    "tasks.byPriority": ["high", "medium", "low"],
    "inventory": [
        "total",
        "inStock",
        "lowStock",
        "outOfStock",
        "lowOrOutOfStock",
        "invalid"
    ]
});

const CANONICAL_NON_FINITE_NUMBERS = new Set([
    "NaN",
    "Infinity",
    "-Infinity"
]);


export class OperationalFactsContractError extends Error {
    constructor(message) {
        super(`Operational facts contract error: ${message}`);
        this.name = "OperationalFactsContractError";
        this.code = "OPERATIONAL_FACTS_CONTRACT_INVALID";
    }
}


function isRecord(value) {
    return Boolean(
        value &&
        typeof value === "object" &&
        !Array.isArray(value)
    );
}


function requireRecord(value, path) {
    if (!isRecord(value)) {
        throw new OperationalFactsContractError(
            `${path} must be an object.`
        );
    }

    return value;
}


function requireNonemptyString(value, path) {
    if (typeof value !== "string" || value.trim() === "") {
        throw new OperationalFactsContractError(
            `${path} must be a nonempty string.`
        );
    }
}


function requireCount(value, path) {
    if (!Number.isInteger(value) || value < 0) {
        throw new OperationalFactsContractError(
            `${path} must be a nonnegative integer.`
        );
    }
}


function sectionAt(summary, path) {
    return path.split(".").reduce(
        (current, segment) => requireRecord(
            current?.[segment],
            `summary.${path}`
        ),
        summary
    );
}


function validateSummary(summary) {
    requireRecord(summary, "summary");

    Object.entries(SUMMARY_SECTIONS).forEach(([path, keys]) => {
        const section = sectionAt(summary, path);

        keys.forEach(key => {
            requireCount(
                section[key],
                `summary.${path}.${key}`
            );
        });
    });
}


function isOperationalNumber(value) {
    return (
        typeof value === "number" &&
        Number.isFinite(value)
    ) || (
        typeof value === "string" &&
        CANONICAL_NON_FINITE_NUMBERS.has(value)
    );
}


function validateMaterialEvidence(fact, index) {
    const evidence = requireRecord(
        fact.evidence,
        `facts[${index}].evidence`
    );

    if (!Array.isArray(evidence.requirements)) {
        throw new OperationalFactsContractError(
            `facts[${index}].evidence.requirements must be an array.`
        );
    }

    evidence.requirements.forEach((requirement, requirementIndex) => {
        const path = (
            `facts[${index}].evidence.requirements[${requirementIndex}]`
        );
        requireRecord(requirement, path);
        requireNonemptyString(
            requirement.inventoryItemId,
            `${path}.inventoryItemId`
        );

        if (!isOperationalNumber(requirement.requiredQuantity)) {
            throw new OperationalFactsContractError(
                `${path}.requiredQuantity must be operational numeric evidence.`
            );
        }
        if (
            requirement.availableQuantity !== null &&
            !isOperationalNumber(requirement.availableQuantity)
        ) {
            throw new OperationalFactsContractError(
                `${path}.availableQuantity must be operational numeric evidence or null.`
            );
        }
        if (
            requirement.shortageQuantity !== null &&
            (
                typeof requirement.shortageQuantity !== "number" ||
                !Number.isFinite(requirement.shortageQuantity)
            )
        ) {
            throw new OperationalFactsContractError(
                `${path}.shortageQuantity must be a finite number or null.`
            );
        }
        requireNonemptyString(
            requirement.reasonCode,
            `${path}.reasonCode`
        );
    });
}


function validateFact(fact, index) {
    const path = `facts[${index}]`;
    requireRecord(fact, path);
    requireNonemptyString(fact.factId, `${path}.factId`);
    requireNonemptyString(fact.factType, `${path}.factType`);
    requireNonemptyString(fact.subjectType, `${path}.subjectType`);
    requireNonemptyString(fact.subjectId, `${path}.subjectId`);
    requireNonemptyString(fact.state, `${path}.state`);

    const rule = FACT_RULES[fact.factType];

    if (!rule) {
        throw new OperationalFactsContractError(
            `${path}.factType is unsupported: ${fact.factType}.`
        );
    }
    if (fact.subjectType !== rule.subjectType) {
        throw new OperationalFactsContractError(
            `${path}.subjectType does not match ${fact.factType}.`
        );
    }
    if (!rule.states.has(fact.state)) {
        throw new OperationalFactsContractError(
            `${path}.state is unsupported for ${fact.factType}.`
        );
    }
    if (!Array.isArray(fact.reasonCodes)) {
        throw new OperationalFactsContractError(
            `${path}.reasonCodes must be an array.`
        );
    }
    fact.reasonCodes.forEach((reasonCode, reasonIndex) => {
        requireNonemptyString(
            reasonCode,
            `${path}.reasonCodes[${reasonIndex}]`
        );
    });
    requireRecord(fact.evidence, `${path}.evidence`);

    if (!Array.isArray(fact.sourceRecords)) {
        throw new OperationalFactsContractError(
            `${path}.sourceRecords must be an array.`
        );
    }

    if (
        fact.factType ===
        OPERATIONAL_FACT_TYPES.projectMaterialReadiness
    ) {
        validateMaterialEvidence(fact, index);
    }
}


export function validateOperationalFactsResponse(response) {
    requireRecord(response, "response");

    if (response.schemaVersion !== 1) {
        throw new OperationalFactsContractError(
            "schemaVersion must equal numeric 1."
        );
    }
    if (!Array.isArray(response.facts)) {
        throw new OperationalFactsContractError(
            "facts must be an array."
        );
    }

    validateSummary(response.summary);

    const factIds = new Set();

    response.facts.forEach((fact, index) => {
        validateFact(fact, index);

        if (factIds.has(fact.factId)) {
            throw new OperationalFactsContractError(
                `factId must be unique: ${fact.factId}.`
            );
        }
        factIds.add(fact.factId);
    });

    return response;
}


export async function getOperationalFacts() {
    return validateOperationalFactsResponse(
        await spaceApiRequest("/api/operational-facts")
    );
}


function factsFrom(responseOrFacts) {
    const facts = Array.isArray(responseOrFacts)
        ? responseOrFacts
        : responseOrFacts?.facts;

    if (!Array.isArray(facts)) {
        throw new OperationalFactsContractError(
            "facts must be available for indexing."
        );
    }

    return facts;
}


export function indexFactsById(responseOrFacts) {
    return new Map(
        factsFrom(responseOrFacts).map(fact => [
            fact.factId,
            fact
        ])
    );
}


function typeSubjectKey(factType, subjectId) {
    return `${factType}\u0000${subjectId}`;
}


export function indexFactsByTypeAndSubject(responseOrFacts) {
    return new Map(
        factsFrom(responseOrFacts).map(fact => [
            typeSubjectKey(fact.factType, fact.subjectId),
            fact
        ])
    );
}


function getFact(responseOrIndex, factType, subjectId) {
    const index = responseOrIndex instanceof Map
        ? responseOrIndex
        : indexFactsByTypeAndSubject(responseOrIndex);

    return index.get(typeSubjectKey(factType, subjectId)) ?? null;
}


export function getProjectMaterialReadinessFact(
    responseOrIndex,
    projectId
) {
    return getFact(
        responseOrIndex,
        OPERATIONAL_FACT_TYPES.projectMaterialReadiness,
        projectId
    );
}


export function getInventoryStockLevelFact(
    responseOrIndex,
    inventoryItemId
) {
    return getFact(
        responseOrIndex,
        OPERATIONAL_FACT_TYPES.inventoryStockLevel,
        inventoryItemId
    );
}
