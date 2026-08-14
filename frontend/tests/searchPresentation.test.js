import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

import {
    routeForSearchResult
} from "../pages/search.js";


const [html, appSource, pageSource, apiSource] = await Promise.all([
    readFile(new URL("../index.html", import.meta.url), "utf8"),
    readFile(new URL("../app.js", import.meta.url), "utf8"),
    readFile(new URL("../pages/search.js", import.meta.url), "utf8"),
    readFile(new URL("../utils/searchApi.js", import.meta.url), "utf8")
]);


test(
    "Universal Search presentation uses active-Space backend authority",
    () => {
        assert.match(
            apiSource,
            /import \{ spaceApiRequest \} from "\.\/spaceApi\.js";/
        );
        assert.match(apiSource, /\/api\/search/);
        assert.doesNotMatch(apiSource, /\bfetch\s*\(/);
        assert.doesNotMatch(
            `${apiSource}\n${pageSource}`,
            /localStorage|sessionStorage|indexedDB/
        );
    }
);


test(
    "Library exposes cross-domain Universal Search presentation",
    () => {
        assert.match(html, /id="universal-search-form"/);
        assert.match(html, /id="universal-search-results"/);
        assert.match(html, /id="universal-search-empty"/);
        assert.match(
            appSource,
            /initializeSearchPresentation\(\)/
        );
    }
);


test(
    "Search results navigate to owning screens without creating ownership",
    () => {
        assert.equal(routeForSearchResult("project"), "projects");
        assert.equal(routeForSearchResult("task"), "tasks");
        assert.equal(routeForSearchResult("tool"), "tools");
        assert.equal(routeForSearchResult("inventory"), "inventory");
        assert.equal(routeForSearchResult("care_plan"), "care");
        assert.equal(routeForSearchResult("calendar_entry"), "calendar");
        assert.equal(routeForSearchResult("calendar_series"), "calendar");
        assert.equal(routeForSearchResult("money_account"), "money");
        assert.equal(routeForSearchResult("library_record"), "library");

        assert.equal(routeForSearchResult("person"), null);
        assert.equal(routeForSearchResult("organization"), null);

        assert.doesNotMatch(
            pageSource,
            /createProject|createTask|createTool|createMoney|createLibrary/
        );
    }
);
