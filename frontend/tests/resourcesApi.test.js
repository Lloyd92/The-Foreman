import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";


const toolsSource = await readFile(
    new URL("../utils/toolsApi.js", import.meta.url),
    "utf8"
);
const careSource = await readFile(
    new URL("../utils/careApi.js", import.meta.url),
    "utf8"
);


test(
    "Tools API stays active-Space centralized and backend authoritative",
    () => {
        assert.match(
            toolsSource,
            /import \{ spaceApiRequest \} from "\.\/spaceApi\.js";/
        );
        assert.doesNotMatch(toolsSource, /\bfetch\s*\(/);
        assert.doesNotMatch(
            toolsSource,
            /localStorage|sessionStorage|indexedDB/
        );

        assert.match(toolsSource, /\/api\/tools/);
        assert.match(toolsSource, /\/maintenance/);

        for (const method of ["POST", "PATCH", "DELETE"]) {
            assert.match(
                toolsSource,
                new RegExp(`method: "${method}"`)
            );
        }
    }
);


test(
    "Care API stays active-Space centralized and backend authoritative",
    () => {
        assert.match(
            careSource,
            /import \{ spaceApiRequest \} from "\.\/spaceApi\.js";/
        );
        assert.doesNotMatch(careSource, /\bfetch\s*\(/);
        assert.doesNotMatch(
            careSource,
            /localStorage|sessionStorage|indexedDB/
        );

        assert.match(careSource, /\/api\/care-plans/);

        for (const method of ["POST", "PATCH", "DELETE"]) {
            assert.match(
                careSource,
                new RegExp(`method: "${method}"`)
            );
        }
    }
);


test(
    "Resources frontend does not create universal Resources authority",
    () => {
        const combined = `${toolsSource}\n${careSource}`;

        assert.doesNotMatch(
            combined,
            /["'`]\/api\/resources(?:["'`/?])/
        );
        assert.doesNotMatch(
            combined,
            /resourceItems|resource_items/
        );
    }
);
