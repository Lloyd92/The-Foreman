import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

import {
    buildTaskCreatePayload,
    formatTaskDueDate
} from "../pages/tasks.js";
import { createBackendTask } from "../utils/tasksApi.js";
import {
    clearActiveSpace,
    setActiveSpace
} from "../utils/spaceContext.js";
import {
    setActiveConnectionController
} from "../utils/connectionState.js";


test("Task create payload preserves optional due date", () => {
    assert.deepEqual(
        buildTaskCreatePayload({
            title: "Cut parts",
            priority: "high",
            dueDate: "2026-08-20"
        }),
        {
            title: "Cut parts",
            priority: "high",
            dueDate: "2026-08-20"
        }
    );

    assert.deepEqual(
        buildTaskCreatePayload({
            title: "Clean bench",
            priority: "medium",
            dueDate: ""
        }),
        {
            title: "Clean bench",
            priority: "medium",
            dueDate: null
        }
    );
});


test("Task due-date presentation distinguishes dated and undated Work", () => {
    assert.equal(
        formatTaskDueDate("2026-08-20"),
        "Due 2026-08-20"
    );
    assert.equal(
        formatTaskDueDate(null),
        "No due date"
    );
});


test("native Task API serializes dueDate under active Space", async t => {
    const originalFetch = globalThis.fetch;
    const expected = {
        title: "Cut parts",
        priority: "high",
        dueDate: "2026-08-20"
    };

    setActiveConnectionController(null);
    clearActiveSpace();
    setActiveSpace({
        id: "space-work",
        name: "Work Test Space"
    });

    globalThis.fetch = async (path, options = {}) => {
        assert.equal(path, "/api/tasks");
        assert.equal(options.method, "POST");

        const headers = new Headers(options.headers || {});
        assert.equal(
            headers.get("X-Foreman-Space-Id"),
            "space-work"
        );

        assert.deepEqual(
            JSON.parse(options.body),
            expected
        );

        return new Response(
            JSON.stringify({
                id: "task-1",
                completed: false,
                projectId: null,
                responsibleMemberId: null,
                createdAt: "2026-08-08T12:00:00Z",
                updatedAt: "2026-08-08T12:00:00Z",
                ...expected
            }),
            {
                status: 201,
                headers: {
                    "Content-Type": "application/json"
                }
            }
        );
    };

    t.after(() => {
        globalThis.fetch = originalFetch;
        clearActiveSpace();
        setActiveConnectionController(null);
    });

    const created = await createBackendTask(expected);

    assert.equal(created.dueDate, "2026-08-20");
});


test("Task page uses tested due-date contracts", async () => {
    const source = await readFile(
        new URL("../pages/tasks.js", import.meta.url),
        "utf8"
    );

    assert.match(
        source,
        /createBackendTask\(\s*buildTaskCreatePayload\(\{/
    );
    assert.match(
        source,
        /formatTaskDueDate\(task\.dueDate\)/
    );
});
