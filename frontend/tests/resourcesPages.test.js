import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

import {
    maintenanceTimestampFromLocal
} from "../pages/tools.js";
import {
    buildCarePayload,
    formatCareFrequency
} from "../pages/care.js";


const [html, app, toolsSource, careSource] =
    await Promise.all([
        readFile(
            new URL("../index.html", import.meta.url),
            "utf8"
        ),
        readFile(
            new URL("../app.js", import.meta.url),
            "utf8"
        ),
        readFile(
            new URL("../pages/tools.js", import.meta.url),
            "utf8"
        ),
        readFile(
            new URL("../pages/care.js", import.meta.url),
            "utf8"
        )
    ]);


test(
    "Tools runtime exposes backend CRUD and factual maintenance history",
    () => {
        for (const marker of [
            "listTools",
            "createTool",
            "updateTool",
            "deleteTool",
            "listToolMaintenance",
            "createToolMaintenance",
            "updateToolMaintenance",
            "deleteToolMaintenance"
        ]) {
            assert.match(
                toolsSource,
                new RegExp(`\\b${marker}\\b`)
            );
        }

        assert.match(html, /id="tool-form"/);
        assert.match(html, /id="maintenance-form"/);
        assert.match(html, /id="maintenance-list"/);
        assert.match(html, /Factual History/);

        assert.doesNotMatch(toolsSource, /\bfetch\s*\(/);
        assert.doesNotMatch(
            toolsSource,
            /localStorage|sessionStorage|indexedDB/
        );
        assert.doesNotMatch(
            toolsSource,
            /getOperationalFacts|operationsApi/
        );
    }
);


test(
    "maintenance performedAt becomes timezone-aware before mutation",
    () => {
        const input = "2026-08-10T12:30";
        const result = maintenanceTimestampFromLocal(input);

        assert.match(result, /Z$/);
        assert.equal(
            Date.parse(result),
            new Date(input).getTime()
        );
        assert.equal(
            maintenanceTimestampFromLocal(""),
            null
        );
        assert.equal(
            maintenanceTimestampFromLocal("not-a-date"),
            null
        );
    }
);


test(
    "Care frequency metadata stays paired and Tool linking stays optional",
    () => {
        assert.deepEqual(
            buildCarePayload({
                name: "Clean workbench",
                careType: "cleaning"
            }),
            {
                name: "Clean workbench",
                careType: "cleaning",
                toolId: null,
                description: "",
                frequencyValue: null,
                frequencyUnit: null,
                notes: ""
            }
        );

        assert.deepEqual(
            buildCarePayload({
                name: "Inspect saw",
                careType: "inspection",
                toolId: "tool-1",
                frequencyValue: "3",
                frequencyUnit: "months"
            }),
            {
                name: "Inspect saw",
                careType: "inspection",
                toolId: "tool-1",
                description: "",
                frequencyValue: 3,
                frequencyUnit: "months",
                notes: ""
            }
        );

        assert.throws(
            () => buildCarePayload({
                name: "Incomplete frequency",
                careType: "inspection",
                frequencyValue: "2"
            }),
            /provided together/
        );

        assert.equal(
            formatCareFrequency({
                frequencyValue: 3,
                frequencyUnit: "months"
            }),
            "3 months"
        );
        assert.equal(
            formatCareFrequency({
                frequencyValue: null,
                frequencyUnit: null
            }),
            "Not specified"
        );
    }
);


test(
    "Care remains usable independently when Tools is disabled",
    () => {
        assert.match(
            careSource,
            /if \(toolsEnabled\) \{[\s\S]*await listTools\(\)/
        );
        assert.match(
            careSource,
            /toolLookupState = "disabled"/
        );
        assert.match(
            careSource,
            /Care remains available independently/
        );

        assert.match(
            app,
            /const toolsEnabled = isModuleEnabled\("tools"\);/
        );
        assert.match(
            app,
            /const careEnabled = isModuleEnabled\("care"\);/
        );
        assert.match(
            app,
            /if \(toolsEnabled\) \{[\s\S]*initializeToolsPage\(\)/
        );
        assert.match(
            app,
            /if \(careEnabled\) \{[\s\S]*initializeCarePage\(\{[\s\S]*toolsEnabled/
        );
    }
);


test(
    "Resources runtime does not introduce Step-7 or decision-engine authority",
    () => {
        const combined = `${toolsSource}\n${careSource}`;

        assert.doesNotMatch(
            combined,
            /getOperationalFacts|operationsApi/
        );
        assert.doesNotMatch(
            combined,
            /\bcapacity\b|\bpriority\b|\brecommendations?\b/i
        );
        assert.doesNotMatch(
            combined,
            /\/api\/resources\b|resource_items|resourceItems/
        );

        assert.match(
            html,
            /Frequency is descriptive metadata only/
        );
        assert.match(
            html,
            /does not create Calendar events or\s+scheduled occurrences/
        );
    }
);
