import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

import {
    BackendApiError
} from "../utils/api.js";
import {
    activateRestore,
    downloadPortableDataExport,
    downloadVerifiedBackup,
    prepareRestorePreflight,
    RecoveryApiContractError,
    RESTORE_CONFIRMATION_PHRASE
} from "../utils/recoveryApi.js";


function manifest() {
    return {
        backupFormatVersion: 1,
        applicationName: "The Foreman",
        applicationVersion: "0.7.3",
        createdAt: "2026-08-01T22:00:00Z",
        operationalFactSchemaVersion: 1,
        database: {
            filename: "foreman.db",
            byteSize: 4096,
            sha256: "a".repeat(64),
            userVersion: 2,
            integrityCheck: "ok",
            foreignKeyViolationCount: 0,
            tables: ["projects"]
        },
        recordCounts: { projects: 1 }
    };
}


function preflightResponse(overrides = {}) {
    const sourceManifest = manifest();

    return {
        token: "preflight-token",
        expiresAt: "2026-08-01T22:15:00Z",
        confirmationPhrase: RESTORE_CONFIRMATION_PHRASE,
        manifest: sourceManifest,
        candidateDatabase: sourceManifest.database,
        recordCounts: { projects: 1 },
        wasUpgraded: false,
        ...overrides
    };
}


function activationResponse(overrides = {}) {
    return {
        status: "restored",
        recordCounts: { projects: 1 },
        operationalFactCount: 3,
        safetyBackupRetained: true,
        reloadRequired: true,
        ...overrides
    };
}


test("downloads a verified backup with its safe server filename", async t => {
    const originalFetch = globalThis.fetch;
    let request;

    globalThis.fetch = async (path, options) => {
        request = { path, options };
        return new Response(new Blob(["backup-bytes"]), {
            status: 200,
            headers: {
                "Content-Type": "application/zip",
                "Content-Disposition": (
                    'attachment; filename="foreman-backup.zip"'
                )
            }
        });
    };
    t.after(() => {
        globalThis.fetch = originalFetch;
    });

    const result = await downloadVerifiedBackup();

    assert.equal(request.path, "/api/recovery/backups");
    assert.equal(request.options.method, "POST");
    assert.equal(request.options.cache, "no-store");
    assert.equal(
        request.options.headers.get("Accept"),
        "application/zip"
    );
    assert.equal(result.filename, "foreman-backup.zip");
    assert.equal(await result.blob.text(), "backup-bytes");
});


test("downloads portable data and decodes filename star safely", async t => {
    const originalFetch = globalThis.fetch;

    globalThis.fetch = async () => new Response(
        new Blob(['{"projects":[]}']),
        {
            status: 200,
            headers: {
                "Content-Type": "application/json; charset=utf-8",
                "Content-Disposition": (
                    "attachment; filename*=UTF-8''foreman-data-export.json"
                )
            }
        }
    );
    t.after(() => {
        globalThis.fetch = originalFetch;
    });

    const result = await downloadPortableDataExport();

    assert.equal(result.filename, "foreman-data-export.json");
    assert.equal(await result.blob.text(), '{"projects":[]}');
});


test("preflight uploads the ZIP body and validates its summary", async t => {
    const originalFetch = globalThis.fetch;
    const backup = new Blob(["zip-bytes"], {
        type: "application/zip"
    });
    let request;

    globalThis.fetch = async (path, options) => {
        request = { path, options };
        return new Response(
            JSON.stringify(preflightResponse()),
            {
                status: 200,
                headers: { "Content-Type": "application/json" }
            }
        );
    };
    t.after(() => {
        globalThis.fetch = originalFetch;
    });

    const result = await prepareRestorePreflight(backup);

    assert.equal(
        request.path,
        "/api/recovery/restores/preflight"
    );
    assert.equal(request.options.method, "POST");
    assert.equal(request.options.body, backup);
    assert.equal(
        request.options.headers.get("Content-Type"),
        "application/zip"
    );
    assert.equal(result.token, "preflight-token");
    assert.deepEqual(result.recordCounts, { projects: 1 });
});


test("activation posts the exact token and confirmation", async t => {
    const originalFetch = globalThis.fetch;
    let request;

    globalThis.fetch = async (path, options) => {
        request = { path, options };
        return new Response(
            JSON.stringify(activationResponse()),
            {
                status: 200,
                headers: { "Content-Type": "application/json" }
            }
        );
    };
    t.after(() => {
        globalThis.fetch = originalFetch;
    });

    const result = await activateRestore(
        "preflight-token",
        RESTORE_CONFIRMATION_PHRASE
    );

    assert.equal(
        request.path,
        "/api/recovery/restores/activate"
    );
    assert.equal(request.options.method, "POST");
    assert.deepEqual(
        JSON.parse(request.options.body),
        {
            token: "preflight-token",
            confirmationPhrase: RESTORE_CONFIRMATION_PHRASE
        }
    );
    assert.equal(result.reloadRequired, true);
});


test("structured recovery errors preserve backend code and message", async t => {
    const originalFetch = globalThis.fetch;

    globalThis.fetch = async () => new Response(
        JSON.stringify({
            detail: {
                code: "RESTORE_PREFLIGHT_EXPIRED",
                message: "The restore preflight session has expired."
            }
        }),
        {
            status: 410,
            headers: { "Content-Type": "application/json" }
        }
    );
    t.after(() => {
        globalThis.fetch = originalFetch;
    });

    await assert.rejects(
        activateRestore(
            "preflight-token",
            RESTORE_CONFIRMATION_PHRASE
        ),
        error => {
            assert.ok(error instanceof BackendApiError);
            assert.equal(error.status, 410);
            assert.equal(
                error.message,
                "The restore preflight session has expired."
            );
            assert.equal(
                error.data.detail.code,
                "RESTORE_PREFLIGHT_EXPIRED"
            );
            return true;
        }
    );
});


test("malformed recovery responses fail closed", async t => {
    const originalFetch = globalThis.fetch;
    const responses = [
        preflightResponse({
            confirmationPhrase: "RESTORE"
        }),
        activationResponse({
            safetyBackupRetained: false
        })
    ];

    globalThis.fetch = async () => new Response(
        JSON.stringify(responses.shift()),
        {
            status: 200,
            headers: { "Content-Type": "application/json" }
        }
    );
    t.after(() => {
        globalThis.fetch = originalFetch;
    });

    await assert.rejects(
        prepareRestorePreflight(
            new Blob(["zip"], { type: "application/zip" })
        ),
        RecoveryApiContractError
    );
    await assert.rejects(
        activateRestore(
            "preflight-token",
            RESTORE_CONFIRMATION_PHRASE
        ),
        RecoveryApiContractError
    );
});


test("empty uploads and invalid attachment types are rejected", async t => {
    const originalFetch = globalThis.fetch;
    let fetchCalls = 0;

    globalThis.fetch = async () => {
        fetchCalls += 1;
        return new Response(new Blob(["not-a-zip"]), {
            status: 200,
            headers: { "Content-Type": "text/plain" }
        });
    };
    t.after(() => {
        globalThis.fetch = originalFetch;
    });

    await assert.rejects(
        prepareRestorePreflight(new Blob([])),
        /nonempty backup file/
    );
    assert.equal(fetchCalls, 0);

    await assert.rejects(
        downloadVerifiedBackup(),
        RecoveryApiContractError
    );
    assert.equal(fetchCalls, 1);
});


test("recovery utility has no storage, direct fetch, or download side effects", async () => {
    const source = await readFile(
        new URL("../utils/recoveryApi.js", import.meta.url),
        "utf8"
    );

    assert.match(
        source,
        /import \{[\s\S]*apiRequest,[\s\S]*apiResponse[\s\S]*\} from "\.\/api\.js"/
    );
    assert.doesNotMatch(source, /\bfetch\s*\(/);
    assert.doesNotMatch(
        source,
        /localStorage|sessionStorage|indexedDB|createObjectURL|click\(\)/
    );
});
