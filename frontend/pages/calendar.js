import {
    createCalendarEntry,
    deleteCalendarEntry,
    getCalendarSettings,
    listCalendarOccurrences,
    listMembers,
    listPeople,
    updateCalendarEntry
} from "../utils/calendarApi.js";


let selectedDate = "";
let calendarTimezone = "";
let occurrences = [];
let members = [];
let people = [];
let editingEntryId = null;
let calendarInitialized = false;


function clean(value) {
    return String(value ?? "").trim();
}


function isoDate(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, "0");
    const day = String(date.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
}


function addDays(value, amount) {
    const [year, month, day] = value.split("-").map(Number);
    const date = new Date(year, month - 1, day + amount, 12);
    return isoDate(date);
}


function todayInTimezone(timezoneName) {
    const parts = new Intl.DateTimeFormat("en-CA", {
        timeZone: timezoneName,
        year: "numeric",
        month: "2-digit",
        day: "2-digit"
    }).formatToParts(new Date());

    const values = Object.fromEntries(
        parts.map(part => [part.type, part.value])
    );

    return `${values.year}-${values.month}-${values.day}`;
}


function memberName(memberId) {
    if (!memberId) {
        return "Unassigned";
    }

    const member = members.find(value => value.id === memberId);
    const person = member
        ? people.find(value => value.id === member.personId)
        : null;

    return person?.displayName || member?.role || "Unknown Member";
}


function formatTime(value) {
    if (!value) {
        return "";
    }

    return new Intl.DateTimeFormat([], {
        timeZone: calendarTimezone,
        hour: "numeric",
        minute: "2-digit"
    }).format(new Date(value));
}


function localInputValue(value) {
    if (!value) {
        return "";
    }

    const parts = new Intl.DateTimeFormat("en-CA", {
        timeZone: calendarTimezone,
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
        hourCycle: "h23"
    }).formatToParts(new Date(value));

    const values = Object.fromEntries(
        parts.map(part => [part.type, part.value])
    );

    return (
        `${values.year}-${values.month}-${values.day}` +
        `T${values.hour}:${values.minute}`
    );
}


function setMessage(message, isError = false) {
    const element = document.getElementById("calendar-page-message");

    if (element) {
        element.textContent = message;
        element.classList.toggle("error", isError);
    }
}


function updateMemberOptions() {
    for (const id of [
        "calendar-member-filter",
        "calendar-entry-member"
    ]) {
        const select = document.getElementById(id);

        if (!select) {
            continue;
        }

        const firstLabel = id === "calendar-member-filter"
            ? "All Members"
            : "Unassigned";
        const firstValue = id === "calendar-member-filter"
            ? "all"
            : "";
        const previous = select.value;

        select.replaceChildren();

        const first = document.createElement("option");
        first.value = firstValue;
        first.textContent = firstLabel;
        select.appendChild(first);

        members
            .map(member => ({
                id: member.id,
                name: memberName(member.id)
            }))
            .sort((a, b) => a.name.localeCompare(b.name))
            .forEach(member => {
                const option = document.createElement("option");
                option.value = member.id;
                option.textContent = member.name;
                select.appendChild(option);
            });

        if ([...select.options].some(
            option => option.value === previous
        )) {
            select.value = previous;
        }
    }
}


function renderOccurrences() {
    const body = document.getElementById("calendar-table-body");
    const empty = document.getElementById("calendar-empty-state");

    if (!body || !empty) {
        return;
    }

    body.replaceChildren();

    const memberFilter =
        document.getElementById("calendar-member-filter")?.value || "all";

    const visible = occurrences.filter(occurrence => (
        memberFilter === "all" ||
        occurrence.memberId === memberFilter
    ));

    empty.hidden = visible.length !== 0;

    for (const occurrence of visible) {
        const row = document.createElement("tr");

        const when = document.createElement("td");
        when.textContent = occurrence.startDate
            ? "All day"
            : `${formatTime(occurrence.startAt)} – ${formatTime(
                occurrence.endAt
            )}`;

        const entry = document.createElement("td");
        const title = document.createElement("strong");
        title.className = "resource-record-name";
        title.textContent = occurrence.title;
        entry.appendChild(title);

        if (occurrence.notes) {
            const note = document.createElement("span");
            note.className = "resource-record-note";
            note.textContent = occurrence.notes;
            entry.appendChild(note);
        }

        const kind = document.createElement("td");
        kind.textContent = occurrence.kind;

        const member = document.createElement("td");
        member.textContent = memberName(occurrence.memberId);

        const location = document.createElement("td");
        location.textContent = occurrence.location || "—";

        const actions = document.createElement("td");
        actions.className = "resource-row-actions";

        if (occurrence.sourceType === "entry") {
            const edit = document.createElement("button");
            edit.type = "button";
            edit.className = "secondary-button";
            edit.textContent = "Edit";
            edit.addEventListener("click", () => {
                openEntryDialog(occurrence);
            });

            const remove = document.createElement("button");
            remove.type = "button";
            remove.className =
                "secondary-button resource-delete-button";
            remove.textContent = "Delete";
            remove.addEventListener("click", async () => {
                if (!window.confirm(
                    `Delete "${occurrence.title}" from Calendar?`
                )) {
                    return;
                }

                try {
                    await deleteCalendarEntry(occurrence.sourceId);
                    await loadOccurrences();
                    setMessage("Calendar entry deleted.");
                } catch (error) {
                    setMessage(error.message, true);
                }
            });

            actions.append(edit, remove);
        } else {
            actions.textContent = "Recurring";
        }

        row.append(
            when,
            entry,
            kind,
            member,
            location,
            actions
        );
        body.appendChild(row);
    }
}


async function loadOccurrences() {
    occurrences = await listCalendarOccurrences(
        selectedDate,
        addDays(selectedDate, 1)
    );
    renderOccurrences();
}


function toggleTimeFields(allDay) {
    const timed = document.getElementById(
        "calendar-entry-timed-fields"
    );
    const dates = document.getElementById(
        "calendar-entry-all-day-fields"
    );

    if (timed) {
        timed.hidden = allDay;
    }

    if (dates) {
        dates.hidden = !allDay;
    }
}


function closeEntryDialog() {
    const backdrop = document.getElementById(
        "calendar-entry-dialog-backdrop"
    );

    if (backdrop) {
        backdrop.hidden = true;
    }

    editingEntryId = null;
}


function openEntryDialog(occurrence = null) {
    const form = document.getElementById("calendar-entry-form");
    const backdrop = document.getElementById(
        "calendar-entry-dialog-backdrop"
    );

    if (!form || !backdrop) {
        return;
    }

    form.reset();
    editingEntryId = occurrence?.sourceType === "entry"
        ? occurrence.sourceId
        : null;

    document.getElementById("calendar-entry-dialog-title").textContent =
        editingEntryId ? "Edit Calendar Entry" : "Add Calendar Entry";

    document.getElementById("calendar-entry-title").value =
        occurrence?.title || "";
    document.getElementById("calendar-entry-kind").value =
        occurrence?.kind || "commitment";
    document.getElementById("calendar-entry-member").value =
        occurrence?.memberId || "";
    document.getElementById("calendar-entry-location").value =
        occurrence?.location || "";
    document.getElementById("calendar-entry-notes").value =
        occurrence?.notes || "";

    const allDay = Boolean(occurrence?.startDate);
    document.getElementById("calendar-entry-all-day").checked = allDay;

    if (allDay) {
        document.getElementById("calendar-entry-start-date").value =
            occurrence.startDate;
        document.getElementById("calendar-entry-end-date").value =
            occurrence.endDate;
    } else {
        document.getElementById("calendar-entry-start-at").value =
            occurrence
                ? localInputValue(occurrence.startAt)
                : `${selectedDate}T09:00`;
        document.getElementById("calendar-entry-end-at").value =
            occurrence
                ? localInputValue(occurrence.endAt)
                : `${selectedDate}T10:00`;
        document.getElementById("calendar-entry-start-date").value =
            selectedDate;
        document.getElementById("calendar-entry-end-date").value =
            addDays(selectedDate, 1);
    }

    toggleTimeFields(allDay);

    document.getElementById("calendar-entry-form-error").textContent = "";
    backdrop.hidden = false;
}


async function saveEntry(event) {
    event.preventDefault();

    const form = event.currentTarget;
    const data = new FormData(form);
    const allDay = data.get("allDay") === "on";

    const payload = {
        memberId: clean(data.get("memberId")) || null,
        kind: clean(data.get("kind")),
        title: clean(data.get("title")),
        allDay,
        location: clean(data.get("location")),
        notes: clean(data.get("notes"))
    };

    if (allDay) {
        payload.startDate = clean(data.get("startDate"));
        payload.endDate = clean(data.get("endDate"));
    } else {
        payload.startAt = clean(data.get("startAt"));
        payload.endAt = clean(data.get("endAt"));
    }

    try {
        if (editingEntryId) {
            await updateCalendarEntry(editingEntryId, payload);
        } else {
            await createCalendarEntry(payload);
        }

        closeEntryDialog();
        await loadOccurrences();
        setMessage("Calendar entry saved.");
    } catch (error) {
        document.getElementById(
            "calendar-entry-form-error"
        ).textContent = error.message;
    }
}


function setSelectedDate(value) {
    selectedDate = value;
    document.getElementById("calendar-date").value = value;

    loadOccurrences().catch(error => {
        setMessage(error.message, true);
    });
}


export async function initializeCalendarPage() {
    if (calendarInitialized) {
        return;
    }

    calendarInitialized = true;

    try {
        const [settings, memberRecords, personRecords] =
            await Promise.all([
                getCalendarSettings(),
                listMembers(),
                listPeople()
            ]);

        calendarTimezone = settings.timezoneName;
        members = memberRecords;
        people = personRecords;
        selectedDate = todayInTimezone(calendarTimezone);

        document.getElementById("calendar-timezone").textContent =
            `Timezone: ${calendarTimezone}`;
        document.getElementById("calendar-date").value = selectedDate;

        updateMemberOptions();

        document.getElementById("calendar-member-filter")
            ?.addEventListener("change", renderOccurrences);

        document.getElementById("calendar-date")
            ?.addEventListener("change", event => {
                if (event.target.value) {
                    setSelectedDate(event.target.value);
                }
            });

        document.getElementById("calendar-previous")
            ?.addEventListener("click", () => {
                setSelectedDate(addDays(selectedDate, -1));
            });

        document.getElementById("calendar-next")
            ?.addEventListener("click", () => {
                setSelectedDate(addDays(selectedDate, 1));
            });

        document.getElementById("calendar-today")
            ?.addEventListener("click", () => {
                setSelectedDate(todayInTimezone(calendarTimezone));
            });

        document.getElementById("add-calendar-entry")
            ?.addEventListener("click", () => openEntryDialog());

        document.getElementById("calendar-entry-all-day")
            ?.addEventListener("change", event => {
                toggleTimeFields(event.target.checked);
            });

        document.getElementById("calendar-entry-form")
            ?.addEventListener("submit", saveEntry);

        for (const id of [
            "close-calendar-entry-dialog",
            "cancel-calendar-entry"
        ]) {
            document.getElementById(id)
                ?.addEventListener("click", closeEntryDialog);
        }

        await loadOccurrences();
    } catch (error) {
        setMessage(error.message, true);
    }
}
