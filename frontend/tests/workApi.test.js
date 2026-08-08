import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

import {
    validateWorkResponse
} from "../utils/workApi.js";


function workItem(overrides = {}) {
    return {
        recordType: "task",
        id: "task-1",
        title: "Cut parts",
        lifecycleState: "open",
        priority: "high",
        progress: 0,
        startDate: null,
        targetDate: null,
        dueDate: "2026-08-20",
        responsibleMemberId: null,
        projectId: "project-1",
        createdAt: "2026-08-08T12:00:00Z",
        updatedAt: "2026-08-08T12:00:00Z",
        ...overrides
    };
}


function dependency(overrides = {}) {
    return {
        id: "dependency-1",
        dependentType: "task",
        dependentId: "task-1",
        prerequisiteType: "project",
        prerequisiteId: "project-1",
        createdAt: "2026-08-08T12:00:00Z",
        ...overrides
    };
}


test("normalized Work response accepts factual backend state", () => {
    const response = {
        items: [
            workItem(),
            workItem({
                recordType: "project",
                id: "project-1",
                title: "Workbench",
                lifecycleState: "active",
                priority: "urgent",
                progress: 37.5,
                startDate: "2026-08-01",
                targetDate: "2026-08-31",
                dueDate: null,
                projectId: null
            })
        ],
        dependencies: [dependency()]
    };

    assert.equal(validateWorkResponse(response), response);
});


test("normalized Work validation rejects malformed records", () => {
    assert.throws(
        () => validateWorkResponse(null),
        /must be an object/
    );

    assert.throws(
        () => validateWorkResponse({
            items: {},
            dependencies: []
        }),
        /items must be an array/
    );

    assert.throws(
        () => validateWorkResponse({
            items: [workItem({ recordType: "inventory" })],
            dependencies: []
        }),
        /recordType is invalid/
    );

    assert.throws(
        () => validateWorkResponse({
            items: [workItem({ progress: 101 })],
            dependencies: []
        }),
        /progress must be between 0 and 100/
    );

    assert.throws(
        () => validateWorkResponse({
            items: [workItem()],
            dependencies: [
                dependency({ prerequisiteType: "calendar" })
            ]
        }),
        /prerequisiteType is invalid/
    );
});


test("normalized Work enforces native Task and Project semantics", () => {
    assert.throws(
        () => validateWorkResponse({
            items: [
                workItem({
                    lifecycleState: "planning"
                })
            ],
            dependencies: []
        }),
        /lifecycleState is invalid for task/
    );

    assert.throws(
        () => validateWorkResponse({
            items: [
                workItem({
                    priority: "urgent"
                })
            ],
            dependencies: []
        }),
        /priority is invalid for task/
    );

    assert.throws(
        () => validateWorkResponse({
            items: [
                workItem({
                    progress: 100
                })
            ],
            dependencies: []
        }),
        /progress does not match Task lifecycleState/
    );

    assert.throws(
        () => validateWorkResponse({
            items: [
                workItem({
                    startDate: "2026-08-01"
                })
            ],
            dependencies: []
        }),
        /Task startDate and targetDate must be null/
    );

    assert.throws(
        () => validateWorkResponse({
            items: [
                workItem({
                    recordType: "project",
                    id: "project-1",
                    lifecycleState: "active",
                    priority: "high",
                    progress: 25,
                    startDate: "2026-08-01",
                    targetDate: "2026-08-31",
                    dueDate: "2026-08-20",
                    projectId: null
                })
            ],
            dependencies: []
        }),
        /Project dueDate and projectId must be null/
    );
});


test("Work API is Space-aware and has no browser persistence", async () => {
    const source = await readFile(
        new URL("../utils/workApi.js", import.meta.url),
        "utf8"
    );

    assert.match(
        source,
        /import \{ spaceApiRequest \} from "\.\/spaceApi\.js"/
    );
    assert.match(
        source,
        /spaceApiRequest\("\/api\/work"\)/
    );
    assert.doesNotMatch(source, /\bfetch\s*\(/);
    assert.doesNotMatch(source, /localStorage|indexedDB/i);
    assert.doesNotMatch(
        source,
        /capacity|recommend|morning briefing|scheduling|ranking/i
    );
});
