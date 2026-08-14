import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

import {
    buildLibraryPayload
} from "../pages/library.js";


const [html, appSource, pageSource, apiSource] = await Promise.all([
    readFile(
        new URL("../index.html", import.meta.url),
        "utf8"
    ),
    readFile(
        new URL("../app.js", import.meta.url),
        "utf8"
    ),
    readFile(
        new URL("../pages/library.js", import.meta.url),
        "utf8"
    ),
    readFile(
        new URL("../utils/libraryApi.js", import.meta.url),
        "utf8"
    )
]);


test(
    "Library API stays active-Space centralized and backend authoritative",
    () => {
        assert.match(
            apiSource,
            /import \{ spaceApiRequest \} from "\.\/spaceApi\.js";/
        );
        assert.doesNotMatch(apiSource, /\bfetch\s*\(/);
        assert.doesNotMatch(
            apiSource,
            /localStorage|sessionStorage|indexedDB/
        );

        assert.match(apiSource, /\/api\/library/);

        for (const method of ["POST", "PATCH", "DELETE"]) {
            assert.match(
                apiSource,
                new RegExp(`"${method}"`)
            );
        }
    }
);


test(
    "Library placeholder is replaced by selected-Space record workflows",
    () => {
        assert.match(html, /id="library-record-form"/);
        assert.match(html, /id="library-search"/);
        assert.match(html, /id="library-kind-filter"/);
        assert.match(html, /id="library-records-body"/);
        assert.match(html, /id="library-empty-state"/);

        assert.doesNotMatch(
            html,
            /Library capabilities are planned for a future release/
        );

        assert.match(
            appSource,
            /initializeLibraryPage\(\)/
        );
    }
);


test(
    "Library page uses Library authority without cross-domain search presentation",
    () => {
        assert.match(pageSource, /\blistLibraryRecords\b/);
        assert.match(pageSource, /\bcreateLibraryRecord\b/);
        assert.match(pageSource, /\bupdateLibraryRecord\b/);
        assert.match(pageSource, /\bdeleteLibraryRecord\b/);

        assert.doesNotMatch(pageSource, /\/api\/search/);
        assert.doesNotMatch(apiSource, /\/api\/search/);
        assert.doesNotMatch(
            pageSource,
            /localStorage|sessionStorage|indexedDB/
        );
    }
);


test(
    "Library payload preserves backend record authority fields",
    () => {
        assert.deepEqual(
            buildLibraryPayload({
                kind: " manual ",
                title: " CNC Manual ",
                content: " Setup notes ",
                referenceLocation: " Shelf A "
            }),
            {
                kind: "manual",
                title: "CNC Manual",
                content: "Setup notes",
                referenceLocation: "Shelf A"
            }
        );
    }
);
