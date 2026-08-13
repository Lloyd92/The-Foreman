import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";


const [
    html,
    app,
    calendarSource,
    calendarApiSource,
    workerSource
] = await Promise.all([
    readFile(new URL("../index.html", import.meta.url), "utf8"),
    readFile(new URL("../app.js", import.meta.url), "utf8"),
    readFile(
        new URL("../pages/calendar.js", import.meta.url),
        "utf8"
    ),
    readFile(
        new URL("../utils/calendarApi.js", import.meta.url),
        "utf8"
    ),
    readFile(
        new URL("../service-worker.js", import.meta.url),
        "utf8"
    )
]);


test(
    "Calendar frontend exposes factual agenda and fixed-entry CRUD",
    () => {
        for (const marker of [
            "getCalendarSettings",
            "listCalendarOccurrences",
            "createCalendarEntry",
            "updateCalendarEntry",
            "deleteCalendarEntry",
            "listMembers",
            "listPeople"
        ]) {
            assert.match(
                calendarSource,
                new RegExp(`\\b${marker}\\b`)
            );
        }

        assert.match(html, /data-page="calendar"/);
        assert.match(html, /id="calendar-table-body"/);
        assert.match(html, /id="calendar-entry-form"/);
        assert.match(html, /id="calendar-member-filter"/);
        assert.match(html, /id="calendar-date"/);
    }
);


test(
    "Calendar remains factual and outside Capacity and Priority authority",
    () => {
        assert.match(
            html,
            /Calendar does not decide Work feasibility\./
        );

        assert.doesNotMatch(
            calendarSource,
            /getOperationalFacts|operationsApi/
        );
        assert.doesNotMatch(
            calendarSource,
            /\bcapacity\b|\bpriority\b/i
        );
        assert.doesNotMatch(calendarSource, /\bfetch\s*\(/);
        assert.doesNotMatch(
            calendarSource,
            /localStorage|sessionStorage|indexedDB/
        );
    }
);


test(
    "Calendar API uses centralized active-Space transport",
    () => {
        assert.match(
            calendarApiSource,
            /spaceApiRequest\("\/api\/calendar\/settings"/
        );
        assert.match(
            calendarApiSource,
            /spaceApiRequest\("\/api\/calendar\/entries"/
        );
        assert.match(
            calendarApiSource,
            /spaceApiRequest\("\/api\/calendar\/series"/
        );
        assert.match(
            calendarApiSource,
            /\/api\/calendar\/occurrences/
        );
        assert.match(
            calendarApiSource,
            /spaceApiRequest\("\/api\/members"/
        );
        assert.match(
            calendarApiSource,
            /apiRequest\("\/api\/people"/
        );

        assert.doesNotMatch(calendarApiSource, /\bfetch\s*\(/);
        assert.doesNotMatch(
            calendarApiSource,
            /localStorage|sessionStorage|indexedDB/
        );
    }
);


test(
    "Calendar is a permanent startup page and PWA shell asset",
    () => {
        assert.match(
            app,
            /import \{ initializeCalendarPage \} from "\.\/pages\/calendar\.js";/
        );
        assert.match(app, /initializeCalendarPage\(\)/);

        assert.match(workerSource, /"\/pages\/calendar\.js"/);
        assert.match(workerSource, /"\/utils\/calendarApi\.js"/);
    }
);
