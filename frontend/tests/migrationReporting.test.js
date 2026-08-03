import assert from "node:assert/strict";
import test from "node:test";

import {
    inventoryMigrationReport,
    projectMigrationReport,
    taskMigrationReport
} from "../utils/migrationReporting.js";


test("Inventory success uses the normalized retained-evidence message", () => {
    const report = inventoryMigrationReport({
        browserRecordCount: 3,
        migration: {
            status: "success",
            migrated: 2,
            alreadyMigrated: 1,
            duplicates: 0,
            malformed: 0,
            errors: []
        }
    });

    assert.equal(report.severity, "info");
    assert.equal(report.importedCount, 2);
    assert.equal(report.confirmedCount, 1);
    assert.equal(report.attentionCount, 0);
    assert.equal(
        report.message,
        "Inventory browser migration complete. " +
        "2 imported, 1 already confirmed, 0 records need attention. " +
        "Browser records were retained only as migration and recovery evidence."
    );
});


test("Inventory attention counts are normalized without exposing errors", () => {
    const sensitiveReason =
        "Validation failed at /home/owner/private/inventory.json";
    const report = inventoryMigrationReport({
        browserRecordCount: 4,
        migration: {
            status: "partial",
            migrated: 2,
            alreadyMigrated: 0,
            duplicates: 1,
            malformed: 1,
            errors: [
                { sourceRecordId: "private-one", reason: sensitiveReason },
                { sourceRecordId: "private-two", reason: "Secret payload" }
            ]
        }
    });

    assert.equal(report.severity, "warning");
    assert.equal(report.attentionCount, 2);
    assert.doesNotMatch(JSON.stringify(report), /private-one|private-two/);
    assert.doesNotMatch(JSON.stringify(report), /Secret payload|\/home\//);
});


test("Task complete failure uses only bounded aggregate counts", () => {
    const report = taskMigrationReport({
        browserRecordCount: 2,
        migration: {
            status: "failed",
            migrated: 0,
            alreadyMigrated: 0,
            skipped: 2,
            errors: [
                { reason: "Sensitive task title" },
                { reason: "Database path /data/foreman.db" }
            ]
        }
    });

    assert.equal(report.severity, "error");
    assert.equal(report.attentionCount, 2);
    assert.match(report.message, /Task browser migration requires attention/);
    assert.doesNotMatch(
        JSON.stringify(report),
        /Sensitive task title|foreman\.db/
    );
});


test("Project reporting maps provenance and retry counts consistently", () => {
    const report = projectMigrationReport({
        status: "partial_success",
        discovered: 4,
        newlyMigrated: 1,
        previouslyMigrated: 1,
        skippedMigrated: 1,
        failed: 1,
        retryableFailures: 1,
        warningCount: 2,
        outcomes: [{
            sourceRecordId: "private-project",
            detail: "Do not expose this"
        }]
    });

    assert.equal(report.severity, "warning");
    assert.equal(report.importedCount, 1);
    assert.equal(report.confirmedCount, 2);
    assert.equal(report.attentionCount, 1);
    assert.equal(report.retryableCount, 1);
    assert.equal(report.warningCount, 2);
    assert.doesNotMatch(
        JSON.stringify(report),
        /private-project|Do not expose this/
    );
});


test("empty migration state produces no user-facing report", () => {
    assert.equal(inventoryMigrationReport(), null);
    assert.equal(taskMigrationReport(), null);
    assert.equal(projectMigrationReport({
        status: "nothing_to_migrate",
        discovered: 0,
        newlyMigrated: 0,
        previouslyMigrated: 0,
        skippedMigrated: 0,
        failed: 0,
        retryableFailures: 0,
        warningCount: 0
    }), null);
});


test("missing result with discovered browser records fails closed", () => {
    const inventory = inventoryMigrationReport({
        browserRecordCount: 2,
        migration: null
    });
    const tasks = taskMigrationReport({
        browserRecordCount: 1,
        migration: null
    });

    assert.equal(inventory.severity, "error");
    assert.equal(inventory.attentionCount, 2);
    assert.equal(tasks.severity, "error");
    assert.equal(tasks.attentionCount, 1);
});


test("all operational pages use the shared migration reporter", async () => {
    const { readFile } = await import("node:fs/promises");

    const [inventory, projects, tasks, styles, worker] =
        await Promise.all([
            readFile(
                new URL("../pages/inventory.js", import.meta.url),
                "utf8"
            ),
            readFile(
                new URL("../pages/projects.js", import.meta.url),
                "utf8"
            ),
            readFile(
                new URL("../pages/tasks.js", import.meta.url),
                "utf8"
            ),
            readFile(
                new URL("../styles.css", import.meta.url),
                "utf8"
            ),
            readFile(
                new URL("../service-worker.js", import.meta.url),
                "utf8"
            )
        ]);

    assert.match(inventory, /inventoryMigrationReport/);
    assert.match(projects, /projectMigrationReport/);
    assert.match(tasks, /taskMigrationReport/);
    assert.doesNotMatch(tasks, /migration\.errors\.forEach/);
    assert.match(styles, /\.inventory-page-message\.error/);
    assert.match(worker, /\/utils\/migrationReporting\.js/);
});
