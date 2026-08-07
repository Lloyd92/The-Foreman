import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

import {
    createRecoveryPageController,
    saveRecoveryAttachment
} from "../pages/recovery.js";
import {
    RESTORE_CONFIRMATION_PHRASE
} from "../utils/recoveryApi.js";


class FakeElement {
    constructor() {
        this.dataset = {};
        this.disabled = false;
        this.files = [];
        this.hidden = false;
        this.listeners = new Map();
        this.textContent = "";
        this.value = "";
    }

    addEventListener(type, listener) {
        const listeners = this.listeners.get(type) || [];
        listeners.push(listener);
        this.listeners.set(type, listeners);
    }

    async dispatch(type) {
        const event = {
            preventDefaultCalls: 0,
            preventDefault() {
                this.preventDefaultCalls += 1;
            }
        };

        for (const listener of this.listeners.get(type) || []) {
            await listener(event);
        }

        await new Promise(resolve => setTimeout(resolve, 0));
        return event;
    }
}


function createElements() {
    return {
        backupButton: new FakeElement(),
        backupStatus: new FakeElement(),
        exportButton: new FakeElement(),
        exportStatus: new FakeElement(),
        restoreForm: new FakeElement(),
        fileInput: new FakeElement(),
        prepareStatus: new FakeElement(),
        prepareButton: new FakeElement(),
        review: new FakeElement(),
        preflightVersion: new FakeElement(),
        preflightSchema: new FakeElement(),
        preflightExpiration: new FakeElement(),
        preflightUpgrade: new FakeElement(),
        preflightCounts: new FakeElement(),
        confirmationForm: new FakeElement(),
        confirmationInput: new FakeElement(),
        activateButton: new FakeElement(),
        activationStatus: new FakeElement()
    };
}


function preflight() {
    return {
        token: "restore-token",
        expiresAt: "2026-08-02T00:15:00Z",
        confirmationPhrase: RESTORE_CONFIRMATION_PHRASE,
        manifest: {
            applicationVersion: "0.7.3"
        },
        candidateDatabase: {
            userVersion: 14,
            tables: ["projects", "tasks"]
        },
        recordCounts: {
            projects: 2,
            tasks: 5
        },
        wasUpgraded: false
    };
}


function createApi(overrides = {}) {
    return {
        async downloadVerifiedBackup() {
            return {
                blob: new Blob(["backup"]),
                filename: "backup.zip"
            };
        },
        async downloadPortableDataExport() {
            return {
                blob: new Blob(["export"]),
                filename: "export.json"
            };
        },
        async prepareRestorePreflight() {
            return preflight();
        },
        async activateRestore() {
            return {
                status: "restored",
                reloadRequired: true
            };
        },
        ...overrides
    };
}


test("downloads backup and portable export through explicit browser saves", async () => {
    const elements = createElements();
    const downloads = [];
    const controller = createRecoveryPageController({
        elements,
        downloadAttachment: attachment => {
            downloads.push(attachment);
        },
        windowRef: { location: { reload() {} } },
        api: createApi()
    });
    controller.bind();

    await elements.backupButton.dispatch("click");
    await elements.exportButton.dispatch("click");

    assert.deepEqual(
        downloads.map(download => download.filename),
        ["backup.zip", "export.json"]
    );
    assert.equal(
        elements.backupStatus.textContent,
        "Verified backup downloaded."
    );
    assert.equal(
        elements.exportStatus.textContent,
        "Portable data export downloaded."
    );
});


test("verified preflight renders facts and requires the exact phrase", async () => {
    const elements = createElements();
    const backup = new Blob(["zip"], { type: "application/zip" });
    let receivedFile = null;
    const controller = createRecoveryPageController({
        elements,
        downloadAttachment() {},
        windowRef: { location: { reload() {} } },
        api: createApi({
            async prepareRestorePreflight(file) {
                receivedFile = file;
                return preflight();
            }
        })
    });
    controller.bind();
    elements.fileInput.files = [backup];

    await elements.restoreForm.dispatch("submit");

    assert.equal(receivedFile, backup);
    assert.equal(elements.review.hidden, false);
    assert.equal(elements.preflightVersion.textContent, "0.7.3");
    assert.equal(elements.preflightSchema.textContent, "14");
    assert.equal(
        elements.preflightCounts.textContent,
        "projects: 2 · tasks: 5"
    );
    assert.equal(elements.confirmationInput.disabled, false);
    assert.equal(elements.activateButton.disabled, true);

    elements.confirmationInput.value = "RESTORE";
    await elements.confirmationInput.dispatch("input");
    assert.equal(elements.activateButton.disabled, true);

    elements.confirmationInput.value = RESTORE_CONFIRMATION_PHRASE;
    await elements.confirmationInput.dispatch("input");
    assert.equal(elements.activateButton.disabled, false);
});


test("activation sends the prepared token and reloads exactly once", async () => {
    const elements = createElements();
    const activations = [];
    let reloads = 0;
    const controller = createRecoveryPageController({
        elements,
        downloadAttachment() {},
        windowRef: {
            location: {
                reload() {
                    reloads += 1;
                }
            }
        },
        api: createApi({
            async activateRestore(token, phrase) {
                activations.push({ token, phrase });
                return {
                    status: "restored",
                    reloadRequired: true
                };
            }
        })
    });
    controller.bind();
    elements.fileInput.files = [
        new Blob(["zip"], { type: "application/zip" })
    ];
    await elements.restoreForm.dispatch("submit");

    elements.confirmationInput.value = RESTORE_CONFIRMATION_PHRASE;
    await elements.confirmationInput.dispatch("input");
    await elements.confirmationForm.dispatch("submit");

    assert.deepEqual(activations, [{
        token: "restore-token",
        phrase: RESTORE_CONFIRMATION_PHRASE
    }]);
    assert.equal(reloads, 1);
    assert.match(
        elements.activationStatus.textContent,
        /Restore completed/
    );
});


test("changing the selected file invalidates a prepared restore", async () => {
    const elements = createElements();
    const controller = createRecoveryPageController({
        elements,
        downloadAttachment() {},
        windowRef: { location: { reload() {} } },
        api: createApi()
    });
    controller.bind();
    elements.fileInput.files = [
        new Blob(["first"], { type: "application/zip" })
    ];
    await elements.restoreForm.dispatch("submit");
    assert.ok(controller.getPreparedRestore());

    elements.fileInput.files = [
        new Blob(["second"], { type: "application/zip" })
    ];
    await elements.fileInput.dispatch("change");

    assert.equal(controller.getPreparedRestore(), null);
    assert.equal(elements.review.hidden, true);
    assert.equal(elements.confirmationInput.disabled, true);
    assert.equal(elements.activateButton.disabled, true);
});


test("activation failure preserves the review and never reloads", async () => {
    const elements = createElements();
    let reloads = 0;
    const controller = createRecoveryPageController({
        elements,
        downloadAttachment() {},
        windowRef: {
            location: {
                reload() {
                    reloads += 1;
                }
            }
        },
        api: createApi({
            async activateRestore() {
                throw new Error("Restore maintenance conflict.");
            }
        })
    });
    controller.bind();
    elements.fileInput.files = [
        new Blob(["zip"], { type: "application/zip" })
    ];
    await elements.restoreForm.dispatch("submit");
    elements.confirmationInput.value = RESTORE_CONFIRMATION_PHRASE;
    await elements.confirmationInput.dispatch("input");
    await elements.confirmationForm.dispatch("submit");

    assert.equal(reloads, 0);
    assert.equal(elements.review.hidden, false);
    assert.equal(elements.confirmationInput.disabled, false);
    assert.equal(
        elements.activationStatus.textContent,
        "Restore maintenance conflict."
    );
    assert.equal(elements.activationStatus.dataset.state, "error");
});


test("attachment saving revokes its temporary URL after one click", () => {
    const calls = {
        appended: 0,
        clicked: 0,
        removed: 0,
        revoked: []
    };
    const anchor = {
        click() {
            calls.clicked += 1;
        },
        remove() {
            calls.removed += 1;
        }
    };
    const documentRef = {
        body: {
            appendChild(received) {
                assert.equal(received, anchor);
                calls.appended += 1;
            }
        },
        createElement(tag) {
            assert.equal(tag, "a");
            return anchor;
        }
    };
    const urlRef = {
        createObjectURL(blob) {
            assert.equal(blob.size, 4);
            return "blob:foreman-download";
        },
        revokeObjectURL(value) {
            calls.revoked.push(value);
        }
    };

    saveRecoveryAttachment(
        {
            blob: new Blob(["data"]),
            filename: "backup.zip"
        },
        { documentRef, urlRef }
    );

    assert.equal(anchor.download, "backup.zip");
    assert.equal(anchor.href, "blob:foreman-download");
    assert.deepEqual(calls, {
        appended: 1,
        clicked: 1,
        removed: 1,
        revoked: ["blob:foreman-download"]
    });
});


test("recovery UI remains linked from Settings with no direct backend transport", async () => {
    const [html, source] = await Promise.all([
        readFile(new URL("../index.html", import.meta.url), "utf8"),
        readFile(new URL("../pages/recovery.js", import.meta.url), "utf8")
    ]);

    assert.match(
        html,
        /data-page="settings"[\s\S]*href="#recovery"/
    );
    assert.match(html, /data-page="recovery"/);
    assert.match(html, /RESTORE THE FOREMAN/);
    assert.match(
        source,
        /from "\.\.\/utils\/recoveryApi\.js"/
    );
    assert.doesNotMatch(source, /\bfetch\s*\(/);
    assert.doesNotMatch(
        source,
        /localStorage|sessionStorage|indexedDB/
    );
});

test("page routes are unique and main page markup is balanced", async () => {
    const html = await readFile(
        new URL("../index.html", import.meta.url),
        "utf8"
    );
    const routes = [
        ...html.matchAll(/data-page="([^"]+)"/g)
    ].map(match => match[1]);
    const openingMainTags = html.match(/<main\b/g) || [];
    const closingMainTags = html.match(/<\/main>/g) || [];

    assert.equal(routes.length, new Set(routes).size);
    assert.equal(openingMainTags.length, closingMainTags.length);
});
