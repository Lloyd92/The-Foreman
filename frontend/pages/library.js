import {
    createLibraryRecord,
    deleteLibraryRecord,
    listLibraryRecords,
    updateLibraryRecord
} from "../utils/libraryApi.js";


let libraryInitialized = false;
let records = [];


function clean(value) {
    return String(value ?? "").trim();
}


function setMessage(message, isError = false) {
    const element = document.getElementById("library-page-message");

    if (!element) {
        return;
    }

    element.textContent = message;
    element.classList.toggle("error", isError);
}


function formatKind(kind) {
    return String(kind ?? "")
        .replaceAll("_", " ")
        .replace(/\b\w/g, value => value.toUpperCase());
}


export function buildLibraryPayload(values) {
    return {
        kind: clean(values.kind),
        title: clean(values.title),
        content: clean(values.content),
        referenceLocation: clean(values.referenceLocation)
    };
}


function resetForm(form) {
    form.reset();
    form.dataset.recordId = "";

    const submit = form.querySelector('button[type="submit"]');

    if (submit) {
        submit.textContent = "Add Record";
    }

    const cancel = document.getElementById("library-cancel-edit");
    if (cancel) {
        cancel.hidden = true;
    }
}


function beginEdit(record) {
    const form = document.getElementById("library-record-form");

    if (!form) {
        return;
    }

    form.dataset.recordId = record.id;
    form.elements.kind.value = record.kind;
    form.elements.title.value = record.title;
    form.elements.content.value = record.content;
    form.elements.referenceLocation.value =
        record.referenceLocation;

    const submit = form.querySelector('button[type="submit"]');
    if (submit) {
        submit.textContent = "Save Changes";
    }

    const cancel = document.getElementById("library-cancel-edit");
    if (cancel) {
        cancel.hidden = false;
    }

    form.elements.title.focus();
}


function actionButton(action, recordId, label) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "table-action-button";
    button.dataset.libraryAction = action;
    button.dataset.recordId = recordId;
    button.textContent = label;

    if (action === "delete") {
        button.classList.add("resource-delete-button");
    }

    return button;
}


function renderRecords() {
    const body = document.getElementById("library-records-body");
    const empty = document.getElementById("library-empty-state");

    if (!body || !empty) {
        return;
    }

    body.replaceChildren();

    for (const record of records) {
        const row = document.createElement("tr");
        row.innerHTML = `
            <td></td>
            <td></td>
            <td></td>
            <td></td>
            <td></td>
        `;

        row.children[0].textContent = record.title;
        row.children[1].textContent = formatKind(record.kind);
        row.children[2].textContent = record.referenceLocation || "—";

        const preview = record.content
            ? (
                record.content.length > 160
                    ? `${record.content.slice(0, 157)}...`
                    : record.content
            )
            : "—";
        row.children[3].textContent = preview;

        const actions = document.createElement("div");
        actions.className = "resource-row-actions";
        actions.append(
            actionButton("edit", record.id, "Edit"),
            actionButton("delete", record.id, "Delete")
        );
        row.children[4].appendChild(actions);

        body.appendChild(row);
    }

    empty.hidden = records.length > 0;
}


async function loadLibrary() {
    const search = clean(
        document.getElementById("library-search")?.value
    );
    const kind = clean(
        document.getElementById("library-kind-filter")?.value
    );

    records = await listLibraryRecords({
        search,
        kind,
        sortBy: "title",
        sortDirection: "asc"
    });

    renderRecords();
}


async function submitRecord(form) {
    const data = new FormData(form);
    const payload = buildLibraryPayload({
        kind: data.get("kind"),
        title: data.get("title"),
        content: data.get("content"),
        referenceLocation: data.get("referenceLocation")
    });

    const recordId = clean(form.dataset.recordId);

    if (recordId) {
        await updateLibraryRecord(recordId, payload);
        return "Library record updated.";
    }

    await createLibraryRecord(payload);
    return "Library record saved.";
}


function bindForm() {
    const form = document.getElementById("library-record-form");

    form?.addEventListener("submit", async event => {
        event.preventDefault();

        try {
            const message = await submitRecord(form);
            resetForm(form);
            await loadLibrary();
            setMessage(message);
        } catch (error) {
            console.error("Library record save failed:", error);
            setMessage("Unable to save Library record.", true);
        }
    });

    document
        .getElementById("library-cancel-edit")
        ?.addEventListener("click", () => {
            resetForm(form);
            setMessage("");
        });
}


function bindFilters() {
    const search = document.getElementById("library-search");
    const kind = document.getElementById("library-kind-filter");

    search?.addEventListener("input", () => {
        loadLibrary().catch(error => {
            console.error("Library search failed:", error);
            setMessage("Unable to search Library records.", true);
        });
    });

    kind?.addEventListener("change", () => {
        loadLibrary().catch(error => {
            console.error("Library filter failed:", error);
            setMessage("Unable to filter Library records.", true);
        });
    });
}


function bindActions() {
    document.addEventListener("click", async event => {
        const button = event.target.closest("[data-library-action]");

        if (!button) {
            return;
        }

        const record = records.find(
            item => item.id === button.dataset.recordId
        );

        if (!record) {
            return;
        }

        if (button.dataset.libraryAction === "edit") {
            beginEdit(record);
            return;
        }

        if (button.dataset.libraryAction !== "delete") {
            return;
        }

        try {
            await deleteLibraryRecord(record.id);
            await loadLibrary();
            setMessage("Library record deleted.");
        } catch (error) {
            console.error("Library record delete failed:", error);
            setMessage("Unable to delete Library record.", true);
        }
    });
}


export async function initializeLibraryPage() {
    if (libraryInitialized) {
        return {
            status: "already-initialized"
        };
    }

    libraryInitialized = true;
    bindForm();
    bindFilters();
    bindActions();

    try {
        await loadLibrary();

        return {
            status: "complete"
        };
    } catch (error) {
        console.error("Library initialization failed:", error);
        setMessage("Library records are currently unavailable.", true);

        return {
            status: "unavailable",
            error
        };
    }
}
