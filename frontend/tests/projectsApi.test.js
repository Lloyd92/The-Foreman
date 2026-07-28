import test from "node:test";
import assert from "node:assert/strict";

import { BackendApiError } from "../utils/api.js";
import {
    createProject,
    deleteProject,
    getProject,
    listProjects,
    migrateBrowserProject,
    updateProject
} from "../utils/projectsApi.js";


test("Project API utility constructs normal CRUD requests", async t => {
    const originalFetch = globalThis.fetch;
    const requests = [];

    globalThis.fetch = async (path, options = {}) => {
        requests.push({ path, options });

        if (options.method === "DELETE") {
            return new Response(null, { status: 204 });
        }

        return new Response(JSON.stringify({ id: "project-1" }), {
            status: options.method === "POST" ? 201 : 200,
            headers: { "Content-Type": "application/json" }
        });
    };
    t.after(() => {
        globalThis.fetch = originalFetch;
    });

    await listProjects(true);
    await getProject("project/id");
    await createProject({ name: "Project" });
    await updateProject("project/id", { progress: 50 });
    await deleteProject("project/id");

    assert.deepEqual(
        requests.map(request => request.path),
        [
            "/api/projects?includeArchived=true",
            "/api/projects/project%2Fid",
            "/api/projects",
            "/api/projects/project%2Fid",
            "/api/projects/project%2Fid"
        ]
    );
    assert.deepEqual(
        requests.map(request => request.options.method || "GET"),
        ["GET", "GET", "POST", "PATCH", "DELETE"]
    );
});


test("Project migration utility posts the finalized contract route", async t => {
    const originalFetch = globalThis.fetch;
    let request;

    globalThis.fetch = async (path, options) => {
        request = { path, options };
        return new Response(JSON.stringify({
            id: "backend-project",
            migrationStatus: "migrated"
        }), {
            status: 201,
            headers: { "Content-Type": "application/json" }
        });
    };
    t.after(() => {
        globalThis.fetch = originalFetch;
    });

    const payload = {
        sourceRecordId: "legacy-project",
        name: "Project"
    };
    const result = await migrateBrowserProject(payload);

    assert.equal(request.path, "/api/project-migrations/browser");
    assert.equal(request.options.method, "POST");
    assert.deepEqual(JSON.parse(request.options.body), payload);
    assert.equal(result.migrationStatus, "migrated");
});


for (const status of [409, 410, 422, 500]) {
    test(`Project API normalizes backend status ${status}`, async t => {
        const originalFetch = globalThis.fetch;

        globalThis.fetch = async () => new Response(
            JSON.stringify({ detail: `failure-${status}` }),
            {
                status,
                headers: { "Content-Type": "application/json" }
            }
        );
        t.after(() => {
            globalThis.fetch = originalFetch;
        });

        await assert.rejects(
            migrateBrowserProject({
                sourceRecordId: "legacy",
                name: "Project"
            }),
            error => {
                assert.ok(error instanceof BackendApiError);
                assert.equal(error.status, status);
                assert.equal(error.message, `failure-${status}`);
                return true;
            }
        );
    });
}


test("Project API preserves network failures as retryable errors", async t => {
    const originalFetch = globalThis.fetch;

    globalThis.fetch = async () => {
        throw new TypeError("network unavailable");
    };
    t.after(() => {
        globalThis.fetch = originalFetch;
    });

    await assert.rejects(
        migrateBrowserProject({
            sourceRecordId: "legacy",
            name: "Project"
        }),
        /network unavailable/
    );
});
