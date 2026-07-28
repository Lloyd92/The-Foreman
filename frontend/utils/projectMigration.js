import { listInventoryItems } from "./inventoryApi.js";
import { PROJECT_STORAGE_KEY } from "./projectStorage.js";
import { migrateBrowserProject } from "./projectsApi.js";

export const PROJECT_MIGRATION_STORAGE_KEY =
    "foreman-project-migration-provenance-v1";
export const PROJECT_MIGRATION_SCHEMA_VERSION = 1;

const STATES = Object.freeze({
    pending: "pending",
    migrated: "migrated",
    conflict: "conflict",
    deleted: "deleted",
    invalid: "invalid",
    retryable: "retryable_error"
});


function canonicalize(value) {
    if (Array.isArray(value)) {
        return value.map(canonicalize);
    }

    if (value && typeof value === "object") {
        return Object.fromEntries(
            Object.keys(value)
                .sort()
                .map(key => [key, canonicalize(value[key])])
        );
    }

    return value;
}


export function stableFingerprint(value) {
    const input = JSON.stringify(canonicalize(value));
    let hash = 2166136261;

    for (let index = 0; index < input.length; index += 1) {
        hash ^= input.charCodeAt(index);
        hash = Math.imul(hash, 16777619);
    }

    return (hash >>> 0).toString(16).padStart(8, "0");
}


function emptyProvenance() {
    return {
        schemaVersion: PROJECT_MIGRATION_SCHEMA_VERSION,
        records: {}
    };
}


export function readProjectMigrationProvenance(storage = localStorage) {
    try {
        const raw = storage.getItem(PROJECT_MIGRATION_STORAGE_KEY);

        if (!raw) {
            return emptyProvenance();
        }

        const parsed = JSON.parse(raw);

        if (
            parsed?.schemaVersion !== PROJECT_MIGRATION_SCHEMA_VERSION ||
            !parsed.records ||
            typeof parsed.records !== "object" ||
            Array.isArray(parsed.records)
        ) {
            return emptyProvenance();
        }

        return parsed;
    } catch (error) {
        console.error("Unable to read Project migration provenance:", error);
        return emptyProvenance();
    }
}


function saveProvenance(storage, provenance) {
    try {
        storage.setItem(
            PROJECT_MIGRATION_STORAGE_KEY,
            JSON.stringify(provenance)
        );
        return true;
    } catch (error) {
        console.error("Unable to save Project migration provenance:", error);
        return false;
    }
}


export function discoverLegacyProjects(storage = localStorage) {
    const raw = storage.getItem(PROJECT_STORAGE_KEY);

    if (!raw) {
        return { records: [], error: null };
    }

    try {
        const records = JSON.parse(raw);

        if (!Array.isArray(records)) {
            return {
                records: [],
                error: "Legacy Project storage is not an array."
            };
        }

        return { records, error: null };
    } catch {
        return {
            records: [],
            error: "Legacy Project storage contains malformed JSON."
        };
    }
}


function nullableDate(value) {
    return value === "" || value === undefined ? null : value;
}


export function prepareLegacyProject(record) {
    if (!record || typeof record !== "object" || Array.isArray(record)) {
        throw new Error("Legacy Project record must be an object.");
    }

    if (
        typeof record.id !== "string" ||
        !record.id.trim() ||
        record.id.length > 120
    ) {
        throw new Error(
            "Legacy Project record requires a stable string ID."
        );
    }

    if (typeof record.name !== "string" || !record.name.trim()) {
        throw new Error("Legacy Project name is required.");
    }

    if (
        typeof record.createdAt !== "string" ||
        !Number.isFinite(Date.parse(record.createdAt))
    ) {
        throw new Error("Legacy Project createdAt is invalid.");
    }

    const materials = record.materials ?? [];

    if (!Array.isArray(materials)) {
        throw new Error("Legacy Project materials must be an array.");
    }

    const inventoryIds = new Set();
    const normalizedMaterials = materials.map(requirement => {
        const inventoryItemId = requirement?.inventoryItemId;
        const requiredQuantity = Number(
            requirement?.requiredQuantity
        );

        if (
            typeof inventoryItemId !== "string" ||
            !inventoryItemId ||
            inventoryIds.has(inventoryItemId) ||
            !Number.isFinite(requiredQuantity) ||
            requiredQuantity <= 0
        ) {
            throw new Error(
                "Legacy Project has an invalid or duplicate material "
                + "requirement."
            );
        }

        inventoryIds.add(inventoryItemId);
        return {
            inventoryItemId,
            requiredQuantity,
            note: typeof requirement.note === "string"
                ? requirement.note
                : ""
        };
    });
    const progress = Number(record.progress ?? 0);
    const estimatedCost = Number(record.estimatedCost ?? 0);

    if (
        !Number.isFinite(progress) ||
        progress < 0 ||
        progress > 100 ||
        !Number.isFinite(estimatedCost) ||
        estimatedCost < 0
    ) {
        throw new Error("Legacy Project numeric fields are invalid.");
    }

    return {
        sourceRecordId: record.id,
        name: record.name,
        type: record.type ?? "other",
        status: record.status ?? "planning",
        priority: record.priority ?? "medium",
        progress,
        startDate: nullableDate(record.startDate),
        targetDate: nullableDate(record.targetDate),
        estimatedCost,
        description: typeof record.description === "string"
            ? record.description
            : "",
        notes: typeof record.notes === "string" ? record.notes : "",
        materials: normalizedMaterials,
        createdAt: record.createdAt,
        updatedAt: record.updatedAt ?? null
    };
}


function shouldSkip(previous, fingerprint) {
    if (!previous) {
        return false;
    }

    if (previous.state === STATES.migrated) {
        return previous.sourceFingerprint === fingerprint;
    }

    if (previous.state === STATES.deleted) {
        return true;
    }

    return (
        (previous.state === STATES.conflict ||
            previous.state === STATES.invalid) &&
        previous.sourceFingerprint === fingerprint
    );
}


function classifyApiFailure(error) {
    const detail = error?.message || "Unknown Project migration failure.";

    if (error?.status === 410) {
        return {
            state: STATES.deleted,
            failureCategory: "deleted",
            retryEligible: false,
            detail
        };
    }

    if (error?.status === 409) {
        const missingInventory = detail === "Inventory item not found.";

        return {
            state: missingInventory
                ? STATES.retryable
                : STATES.conflict,
            failureCategory: missingInventory
                ? "missing_inventory"
                : "payload_conflict",
            retryEligible: missingInventory,
            detail
        };
    }

    if (error?.status === 422) {
        return {
            state: STATES.invalid,
            failureCategory: "invalid",
            retryEligible: false,
            detail
        };
    }

    return {
        state: STATES.retryable,
        failureCategory: error?.status
            ? "server_error"
            : "network_error",
        retryEligible: true,
        detail
    };
}


function overallStatus(result) {
    if (result.discovered === 0 && result.failed === 0) {
        return "nothing_to_migrate";
    }

    const successes =
        result.newlyMigrated +
        result.previouslyMigrated +
        result.skippedMigrated;

    if (result.failed === 0) {
        return "complete_success";
    }

    return successes > 0 ? "partial_success" : "complete_failure";
}


function migrationResult() {
    return {
        status: "nothing_to_migrate",
        discovered: 0,
        attempted: 0,
        newlyMigrated: 0,
        previouslyMigrated: 0,
        skipped: 0,
        skippedMigrated: 0,
        failed: 0,
        retryableFailures: 0,
        warningCount: 0,
        outcomes: [],
        projectIdMappings: {}
    };
}


export async function migrateLegacyProjects({
    storage = localStorage,
    migrateProject = migrateBrowserProject,
    loadInventory = listInventoryItems,
    now = () => new Date().toISOString()
} = {}) {
    const result = migrationResult();
    const discovery = discoverLegacyProjects(storage);
    const provenance = readProjectMigrationProvenance(storage);

    if (discovery.error) {
        const outcome = {
            sourceRecordId: null,
            state: STATES.invalid,
            failureCategory: "malformed_storage",
            detail: discovery.error,
            retryEligible: false,
            warnings: [discovery.error]
        };

        result.failed = 1;
        result.warningCount = 1;
        result.outcomes.push(outcome);
        provenance.records["storage:malformed"] = {
            ...outcome,
            lastAttemptAt: now(),
            sourceFingerprint: stableFingerprint(
                storage.getItem(PROJECT_STORAGE_KEY)
            )
        };
        saveProvenance(storage, provenance);
        result.status = overallStatus(result);
        return result;
    }

    result.discovered = discovery.records.length;

    if (result.discovered === 0) {
        return result;
    }

    const candidates = [];

    discovery.records.forEach((record, index) => {
        let payload;
        let sourceRecordId =
            typeof record?.id === "string" ? record.id : null;
        let fingerprint = stableFingerprint(record);

        try {
            payload = prepareLegacyProject(record);
            sourceRecordId = payload.sourceRecordId;
            fingerprint = stableFingerprint(payload);
        } catch (error) {
            const key = sourceRecordId || `invalid:${index}:${fingerprint}`;
            const previous = provenance.records[key];

            if (shouldSkip(previous, fingerprint)) {
                result.skipped += 1;
                result.failed += 1;
                result.outcomes.push({ ...previous, skipped: true });
                return;
            }

            const outcome = {
                sourceRecordId,
                state: STATES.invalid,
                failureCategory: "invalid",
                detail: error.message,
                retryEligible: false,
                warnings: []
            };
            result.failed += 1;
            result.outcomes.push(outcome);
            provenance.records[key] = {
                ...outcome,
                lastAttemptAt: now(),
                sourceFingerprint: fingerprint
            };
            saveProvenance(storage, provenance);
            return;
        }

        const previous = provenance.records[sourceRecordId];

        if (shouldSkip(previous, fingerprint)) {
            result.skipped += 1;

            if (previous.state === STATES.migrated) {
                result.skippedMigrated += 1;
                result.projectIdMappings[sourceRecordId] =
                    previous.backendProjectId;
            } else {
                result.failed += 1;
            }

            result.outcomes.push({ ...previous, skipped: true });
            return;
        }

        candidates.push({
            payload,
            sourceRecordId,
            fingerprint
        });
    });

    if (candidates.length === 0) {
        result.status = overallStatus(result);
        return result;
    }

    let inventoryItems;

    try {
        inventoryItems = await loadInventory();
    } catch (error) {
        candidates.forEach(({ sourceRecordId, fingerprint }) => {
            const outcome = {
                sourceRecordId,
                state: STATES.retryable,
                failureCategory: "inventory_unavailable",
                detail: error?.message || "Inventory is unavailable.",
                retryEligible: true,
                warnings: []
            };

            result.failed += 1;
            result.retryableFailures += 1;
            result.outcomes.push(outcome);
            provenance.records[sourceRecordId] = {
                ...outcome,
                lastAttemptAt: now(),
                sourceFingerprint: fingerprint
            };
        });
        saveProvenance(storage, provenance);
        result.status = overallStatus(result);
        return result;
    }

    const availableInventoryIds = new Set(
        inventoryItems.map(item => item.id)
    );

    for (const candidate of candidates) {
        const { payload, sourceRecordId, fingerprint } = candidate;
        const missingInventoryIds = payload.materials
            .map(material => material.inventoryItemId)
            .filter(id => !availableInventoryIds.has(id))
            .sort();

        if (missingInventoryIds.length > 0) {
            const warnings = missingInventoryIds.map(id =>
                `Project ${sourceRecordId} references missing Inventory ${id}.`
            );
            const outcome = {
                sourceRecordId,
                state: STATES.retryable,
                failureCategory: "missing_inventory",
                detail: "Project was not submitted because material "
                    + "requirements reference missing Inventory.",
                retryEligible: true,
                warnings
            };

            result.failed += 1;
            result.retryableFailures += 1;
            result.warningCount += warnings.length;
            result.outcomes.push(outcome);
            provenance.records[sourceRecordId] = {
                ...outcome,
                lastAttemptAt: now(),
                sourceFingerprint: fingerprint
            };
            saveProvenance(storage, provenance);
            continue;
        }

        result.attempted += 1;

        try {
            const migrated = await migrateProject(payload);
            const migrationStatus = migrated.migrationStatus;
            const outcome = {
                sourceRecordId,
                state: STATES.migrated,
                backendProjectId: migrated.id,
                migrationStatus,
                failureCategory: null,
                detail: null,
                retryEligible: false,
                warnings: []
            };

            if (migrationStatus === "already-migrated") {
                result.previouslyMigrated += 1;
            } else {
                result.newlyMigrated += 1;
            }

            result.projectIdMappings[sourceRecordId] = migrated.id;
            result.outcomes.push(outcome);
            provenance.records[sourceRecordId] = {
                ...outcome,
                lastAttemptAt: now(),
                sourceFingerprint: fingerprint
            };
        } catch (error) {
            const classified = classifyApiFailure(error);
            const warnings = classified.failureCategory ===
                "missing_inventory"
                ? [
                    `Project ${sourceRecordId} was rejected because an `
                    + "Inventory reference is missing."
                ]
                : [];
            const outcome = {
                sourceRecordId,
                ...classified,
                warnings
            };

            result.failed += 1;
            result.retryableFailures += Number(
                classified.retryEligible
            );
            result.warningCount += warnings.length;
            result.outcomes.push(outcome);
            provenance.records[sourceRecordId] = {
                ...outcome,
                lastAttemptAt: now(),
                sourceFingerprint: fingerprint
            };
        }

        saveProvenance(storage, provenance);
    }

    result.status = overallStatus(result);
    return result;
}


export { STATES as PROJECT_MIGRATION_STATES };
