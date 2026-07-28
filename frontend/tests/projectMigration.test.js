import test from "node:test";
import assert from "node:assert/strict";

import {
    PROJECT_MIGRATION_STORAGE_KEY,
    migrateLegacyProjects,
    readProjectMigrationProvenance
} from "../utils/projectMigration.js";
import { PROJECT_STORAGE_KEY } from "../utils/projectStorage.js";
import {
    migrateProjectsAfterInventory,
    migrateTasksAfterProjects,
    translateTaskProjectReferences
} from "../utils/migrationOrchestrator.js";


class MemoryStorage {
    constructor(values = {}) {
        this.values = new Map(Object.entries(values));
    }

    getItem(key) {
        return this.values.has(key) ? this.values.get(key) : null;
    }

    setItem(key, value) {
        this.values.set(key, String(value));
    }
}


function project(id, overrides = {}) {
    return {
        id,
        name: `Project ${id}`,
        type: "build",
        status: "planning",
        priority: "medium",
        progress: 10,
        startDate: "",
        targetDate: "",
        estimatedCost: 12.5,
        description: "Legacy",
        notes: "Retain",
        materials: [],
        createdAt: "2026-07-01T12:00:00.000Z",
        ...overrides
    };
}


function storageFor(records) {
    return new MemoryStorage({
        [PROJECT_STORAGE_KEY]: JSON.stringify(records)
    });
}


function apiError(status, message) {
    return Object.assign(new Error(message), { status });
}


function options(storage, migrateProject, inventory = []) {
    return {
        storage,
        migrateProject,
        loadInventory: async () => inventory,
        now: () => "2026-07-27T12:00:00.000Z"
    };
}


test("no legacy Projects returns nothing_to_migrate", async () => {
    const result = await migrateLegacyProjects({
        storage: new MemoryStorage(),
        migrateProject: async () => assert.fail("must not migrate"),
        loadInventory: async () => assert.fail("must not load Inventory")
    });

    assert.equal(result.status, "nothing_to_migrate");
    assert.equal(result.discovered, 0);
});


test("one valid Project migrates from a 201 result", async () => {
    const storage = storageFor([project("p1")]);
    const result = await migrateLegacyProjects(
        options(storage, async payload => ({
            id: "backend-p1",
            migrationStatus: "migrated",
            payload
        }))
    );

    assert.equal(result.status, "complete_success");
    assert.equal(result.newlyMigrated, 1);
    assert.equal(result.projectIdMappings.p1, "backend-p1");
});


test("a committed Project is recovered from a 200-style result", async () => {
    const storage = storageFor([project("p1")]);
    const result = await migrateLegacyProjects(
        options(storage, async () => ({
            id: "backend-existing",
            migrationStatus: "already-migrated"
        }))
    );

    assert.equal(result.previouslyMigrated, 1);
    assert.equal(result.projectIdMappings.p1, "backend-existing");
});


test("multiple valid Projects migrate successfully", async () => {
    const storage = storageFor([project("p1"), project("p2")]);
    const seen = [];
    const result = await migrateLegacyProjects(
        options(storage, async payload => {
            seen.push(payload.sourceRecordId);
            return {
                id: `backend-${payload.sourceRecordId}`,
                migrationStatus: "migrated"
            };
        })
    );

    assert.deepEqual(seen, ["p1", "p2"]);
    assert.equal(result.newlyMigrated, 2);
});


test("one Project failure does not hide another success", async () => {
    const storage = storageFor([project("bad"), project("good")]);
    const result = await migrateLegacyProjects(
        options(storage, async payload => {
            if (payload.sourceRecordId === "bad") {
                throw apiError(500, "temporary failure");
            }
            return { id: "backend-good", migrationStatus: "migrated" };
        })
    );

    assert.equal(result.status, "partial_success");
    assert.equal(result.newlyMigrated, 1);
    assert.equal(result.failed, 1);
});


test("rerun skips a locally confirmed migration", async () => {
    const storage = storageFor([project("p1")]);
    let calls = 0;
    const migrateProject = async () => {
        calls += 1;
        return { id: "backend-p1", migrationStatus: "migrated" };
    };

    await migrateLegacyProjects(options(storage, migrateProject));
    const retry = await migrateLegacyProjects(
        options(storage, migrateProject)
    );

    assert.equal(calls, 1);
    assert.equal(retry.skippedMigrated, 1);
    assert.equal(retry.projectIdMappings.p1, "backend-p1");
});


test("interrupted-response recovery reuses the stable sourceRecordId", async () => {
    const storage = storageFor([project("stable-source")]);
    const submitted = [];
    const result = await migrateLegacyProjects(
        options(storage, async payload => {
            submitted.push(payload.sourceRecordId);
            return {
                id: "backend-stable",
                migrationStatus: "already-migrated"
            };
        })
    );

    assert.deepEqual(submitted, ["stable-source"]);
    assert.equal(result.previouslyMigrated, 1);
});


test("partial retry selects only the unresolved Project", async () => {
    const storage = storageFor([project("p1"), project("p2")]);
    const firstCalls = [];

    await migrateLegacyProjects(
        options(storage, async payload => {
            firstCalls.push(payload.sourceRecordId);
            if (payload.sourceRecordId === "p2") {
                throw apiError(0, "offline");
            }
            return { id: "backend-p1", migrationStatus: "migrated" };
        })
    );

    const retryCalls = [];
    const retry = await migrateLegacyProjects(
        options(storage, async payload => {
            retryCalls.push(payload.sourceRecordId);
            return { id: "backend-p2", migrationStatus: "migrated" };
        })
    );

    assert.deepEqual(firstCalls, ["p1", "p2"]);
    assert.deepEqual(retryCalls, ["p2"]);
    assert.equal(retry.skippedMigrated, 1);
});


test("missing Inventory produces deterministic warnings", async () => {
    const storage = storageFor([
        project("p1", {
            materials: [{
                inventoryItemId: "missing-1",
                requiredQuantity: 2
            }]
        })
    ]);
    const result = await migrateLegacyProjects(
        options(storage, async () => assert.fail("must not submit"))
    );

    assert.equal(result.warningCount, 1);
    assert.equal(result.outcomes[0].failureCategory, "missing_inventory");
    assert.equal(
        result.outcomes[0].warnings[0],
        "Project p1 references missing Inventory missing-1."
    );
});


test("missing Inventory does not abort unrelated Projects", async () => {
    const storage = storageFor([
        project("bad", {
            materials: [{
                inventoryItemId: "missing",
                requiredQuantity: 1
            }]
        }),
        project("good")
    ]);
    const result = await migrateLegacyProjects(
        options(storage, async () => ({
            id: "backend-good",
            migrationStatus: "migrated"
        }))
    );

    assert.equal(result.status, "partial_success");
    assert.equal(result.newlyMigrated, 1);
    assert.equal(result.failed, 1);
});


test("payload conflict is recorded and not automatically retried", async () => {
    const storage = storageFor([project("p1")]);
    let calls = 0;
    const migrateProject = async () => {
        calls += 1;
        throw apiError(409, "different Project data");
    };

    const first = await migrateLegacyProjects(
        options(storage, migrateProject)
    );
    const retry = await migrateLegacyProjects(
        options(storage, migrateProject)
    );

    assert.equal(first.outcomes[0].state, "conflict");
    assert.equal(retry.skipped, 1);
    assert.equal(calls, 1);
});


test("changed source data makes a prior conflict eligible again", async () => {
    const storage = storageFor([project("p1")]);

    await migrateLegacyProjects(
        options(storage, async () => {
            throw apiError(409, "different Project data");
        })
    );
    storage.setItem(
        PROJECT_STORAGE_KEY,
        JSON.stringify([project("p1", { notes: "Changed" })])
    );
    let calls = 0;
    await migrateLegacyProjects(
        options(storage, async () => {
            calls += 1;
            return { id: "backend-p1", migrationStatus: "migrated" };
        })
    );

    assert.equal(calls, 1);
});


test("changed data after migration is surfaced as a conflict", async () => {
    const storage = storageFor([project("p1")]);
    await migrateLegacyProjects(
        options(storage, async () => ({
            id: "backend-p1",
            migrationStatus: "migrated"
        }))
    );
    storage.setItem(
        PROJECT_STORAGE_KEY,
        JSON.stringify([project("p1", { notes: "Edited locally" })])
    );
    let calls = 0;
    const result = await migrateLegacyProjects(
        options(storage, async () => {
            calls += 1;
            throw apiError(409, "different Project data");
        })
    );

    assert.equal(calls, 1);
    assert.equal(result.outcomes[0].state, "conflict");
});


test("deleted migration is tombstoned and never recreated", async () => {
    const storage = storageFor([project("p1")]);
    let calls = 0;
    const migrateProject = async () => {
        calls += 1;
        throw apiError(410, "deleted and will not be recreated");
    };

    const first = await migrateLegacyProjects(
        options(storage, migrateProject)
    );
    const retry = await migrateLegacyProjects(
        options(storage, migrateProject)
    );

    assert.equal(first.outcomes[0].state, "deleted");
    assert.equal(retry.skipped, 1);
    assert.equal(calls, 1);
});


test("malformed individual Project does not crash migration", async () => {
    const storage = storageFor([
        { id: "bad", name: "", createdAt: "not-a-date" },
        project("good")
    ]);
    const result = await migrateLegacyProjects(
        options(storage, async () => ({
            id: "backend-good",
            migrationStatus: "migrated"
        }))
    );

    assert.equal(result.status, "partial_success");
    assert.equal(result.failed, 1);
    assert.equal(result.newlyMigrated, 1);
});


test("malformed browser JSON is reported safely", async () => {
    const storage = new MemoryStorage({
        [PROJECT_STORAGE_KEY]: "{not json"
    });
    const result = await migrateLegacyProjects(
        options(storage, async () => assert.fail("must not submit"))
    );

    assert.equal(result.status, "complete_failure");
    assert.equal(result.outcomes[0].failureCategory, "malformed_storage");
    assert.equal(
        readProjectMigrationProvenance(storage)
            .records["storage:malformed"].state,
        "invalid"
    );
});


test("backend unavailability creates retryable outcomes", async () => {
    const storage = storageFor([project("p1")]);
    const result = await migrateLegacyProjects({
        storage,
        migrateProject: async () => assert.fail("must not submit"),
        loadInventory: async () => {
            throw new Error("offline");
        }
    });

    assert.equal(result.retryableFailures, 1);
    assert.equal(result.outcomes[0].state, "retryable_error");
});


test("legacy source remains byte-for-byte unchanged after success", async () => {
    const storage = storageFor([project("p1")]);
    const before = storage.getItem(PROJECT_STORAGE_KEY);

    await migrateLegacyProjects(
        options(storage, async () => ({
            id: "backend-p1",
            migrationStatus: "migrated"
        }))
    );

    assert.equal(storage.getItem(PROJECT_STORAGE_KEY), before);
});


test("legacy source remains unchanged after partial failure", async () => {
    const storage = storageFor([project("p1"), project("p2")]);
    const before = storage.getItem(PROJECT_STORAGE_KEY);

    await migrateLegacyProjects(
        options(storage, async payload => {
            if (payload.sourceRecordId === "p1") {
                throw apiError(500, "failed");
            }
            return { id: "backend-p2", migrationStatus: "migrated" };
        })
    );

    assert.equal(storage.getItem(PROJECT_STORAGE_KEY), before);
});


test("Project migration waits for Inventory migration", async () => {
    const events = [];
    let finishInventory;
    const inventory = new Promise(resolve => {
        finishInventory = () => {
            events.push("inventory");
            resolve();
        };
    });
    const running = migrateProjectsAfterInventory(inventory, async () => {
        events.push("projects");
        return { projectIdMappings: {} };
    });

    await Promise.resolve();
    assert.deepEqual(events, []);
    finishInventory();
    await running;
    assert.deepEqual(events, ["inventory", "projects"]);
});


test("Task migration waits for Project migration", async () => {
    const events = [];
    let finishProjects;
    const projects = new Promise(resolve => {
        finishProjects = () => {
            events.push("projects");
            resolve({ projectIdMappings: {} });
        };
    });
    const running = migrateTasksAfterProjects(
        projects,
        [],
        async () => {
            events.push("tasks");
            return {};
        }
    );

    await Promise.resolve();
    assert.deepEqual(events, []);
    finishProjects();
    await running;
    assert.deepEqual(events, ["projects", "tasks"]);
});


test("Project migration rejection does not prevent Task migration", async () => {
    let migrated = false;
    await migrateTasksAfterProjects(
        Promise.reject(new Error("Project migration failed")),
        [],
        async () => {
            migrated = true;
            return {};
        }
    );

    assert.equal(migrated, true);
});


test("successful Project mappings are passed into Task migration", async () => {
    let submitted;
    await migrateTasksAfterProjects(
        Promise.resolve({
            projectIdMappings: { legacy: "backend" }
        }),
        [{ id: "task", projectId: "legacy" }],
        async tasks => {
            submitted = tasks;
            return {};
        }
    );

    assert.equal(submitted[0].projectId, "backend");
});


test("failed Project references retain missing-reference behavior", () => {
    const tasks = [{ id: "task", projectId: "failed-project" }];
    const translated = translateTaskProjectReferences(tasks, {
        projectIdMappings: {}
    });

    assert.equal(translated[0].projectId, "failed-project");
});


test("browser provenance remains readable across reloads", async () => {
    const storage = storageFor([project("p1")]);
    await migrateLegacyProjects(
        options(storage, async () => ({
            id: "backend-p1",
            migrationStatus: "migrated"
        }))
    );

    const reloaded = readProjectMigrationProvenance(storage);
    assert.equal(reloaded.records.p1.backendProjectId, "backend-p1");
    assert.ok(storage.getItem(PROJECT_MIGRATION_STORAGE_KEY));
});


test("material requirements are not resubmitted after success", async () => {
    const storage = storageFor([
        project("p1", {
            materials: [{
                inventoryItemId: "inventory-1",
                requiredQuantity: 2
            }]
        })
    ]);
    let calls = 0;
    const migrateProject = async payload => {
        calls += 1;
        assert.equal(payload.materials.length, 1);
        return { id: "backend-p1", migrationStatus: "migrated" };
    };
    const migrationOptions = options(
        storage,
        migrateProject,
        [{ id: "inventory-1" }]
    );

    await migrateLegacyProjects(migrationOptions);
    await migrateLegacyProjects(migrationOptions);
    assert.equal(calls, 1);
});


test("identical content with different IDs migrates separately", async () => {
    const first = project("p1", { name: "Identical" });
    const second = project("p2", { name: "Identical" });
    const storage = storageFor([first, second]);
    const sources = [];

    await migrateLegacyProjects(
        options(storage, async payload => {
            sources.push(payload.sourceRecordId);
            return {
                id: `backend-${payload.sourceRecordId}`,
                migrationStatus: "migrated"
            };
        })
    );

    assert.deepEqual(sources, ["p1", "p2"]);
});
