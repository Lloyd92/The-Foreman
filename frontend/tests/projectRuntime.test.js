import test from "node:test";
import assert from "node:assert/strict";

import {
    loadBackendProjects,
    mergePersistedProject,
    removePersistedProject
} from "../utils/projectRuntime.js";


function project(id, overrides = {}) {
    return {
        id,
        name: `Project ${id}`,
        materials: [],
        ...overrides
    };
}


test("backend Projects load without consulting browser storage", async () => {
    const expected = [project("backend-1")];
    let calls = 0;

    const loaded = await loadBackendProjects(async () => {
        calls += 1;
        return expected;
    });

    assert.equal(calls, 1);
    assert.deepEqual(loaded, expected);
});


test("an empty backend Project list remains an explicit empty state", async () => {
    assert.deepEqual(
        await loadBackendProjects(async () => []),
        []
    );
});


test("malformed Project list and records fail deterministically", async () => {
    await assert.rejects(
        loadBackendProjects(async () => ({ projects: [] })),
        /malformed Project list/
    );
    await assert.rejects(
        loadBackendProjects(async () => [{ id: "missing-fields" }]),
        /malformed Project record/
    );
});


test("persisted create and update responses are merged by backend ID", () => {
    const first = project("one", { name: "Same name" });
    const second = project("two", { name: "Same name" });
    const created = mergePersistedProject([first], second);

    assert.deepEqual(created.map(item => item.id), ["one", "two"]);

    const updated = mergePersistedProject(
        created,
        project("one", { name: "Updated", progress: 60 })
    );

    assert.equal(updated.length, 2);
    assert.equal(updated[0].name, "Updated");
    assert.equal(updated[0].progress, 60);
});


test("a malformed persistence response leaves prior state unchanged", () => {
    const existing = [project("one")];

    assert.throws(
        () => mergePersistedProject(existing, { id: "bad" }),
        /malformed Project record/
    );
    assert.deepEqual(existing, [project("one")]);
});


test("deletion removes only the matching backend Project ID", () => {
    const existing = [
        project("one", { name: "Same name" }),
        project("two", { name: "Same name" })
    ];

    assert.deepEqual(
        removePersistedProject(existing, "one"),
        [existing[1]]
    );
    assert.deepEqual(
        removePersistedProject(existing, "missing"),
        existing
    );
});
