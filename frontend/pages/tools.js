import {
    createTool,
    createToolMaintenance,
    deleteTool,
    deleteToolMaintenance,
    listToolMaintenance,
    listTools,
    updateTool,
    updateToolMaintenance
} from "../utils/toolsApi.js";


let tools = [];
let editingToolId = null;
let maintenanceToolId = null;
let maintenanceRecords = [];
let editingMaintenanceId = null;
let toolsInitialized = false;


function setText(id, value) {
    const element = document.getElementById(id);

    if (element) {
        element.textContent = value;
    }
}


function setToolsMessage(message, isError = false) {
    const element = document.getElementById("tools-page-message");

    if (!element) {
        return;
    }

    element.textContent = message;
    element.classList.toggle("error", isError);
}


function setMaintenanceMessage(message, isError = false) {
    const element = document.getElementById("maintenance-message");

    if (!element) {
        return;
    }

    element.textContent = message;
    element.classList.toggle("error", isError);
}


function getTool(toolId) {
    return tools.find(tool => tool.id === toolId) || null;
}


function clean(value) {
    return String(value ?? "").trim();
}


function toolPayload(formData) {
    return {
        name: clean(formData.get("name")),
        category: clean(formData.get("category")),
        condition: clean(formData.get("condition")),
        location: clean(formData.get("location")),
        availability: clean(formData.get("availability")),
        notes: clean(formData.get("notes"))
    };
}


export function maintenanceTimestampFromLocal(value) {
    if (!value) {
        return null;
    }

    const parsed = new Date(value);

    if (Number.isNaN(parsed.getTime())) {
        return null;
    }

    return parsed.toISOString();
}


function maintenanceInputValue(value) {
    const parsed = new Date(value);

    if (Number.isNaN(parsed.getTime())) {
        return "";
    }

    const local = new Date(
        parsed.getTime() - parsed.getTimezoneOffset() * 60000
    );

    return local.toISOString().slice(0, 16);
}


function formatTimestamp(value) {
    const parsed = new Date(value);

    if (Number.isNaN(parsed.getTime())) {
        return "Timestamp unavailable";
    }

    return parsed.toLocaleString();
}


function updateSelectOptions(id, values, allLabel) {
    const select = document.getElementById(id);

    if (!select) {
        return;
    }

    const previous = select.value;
    select.replaceChildren();

    const all = document.createElement("option");
    all.value = "all";
    all.textContent = allLabel;
    select.appendChild(all);

    [...new Set(values.filter(Boolean))]
        .sort((a, b) => a.localeCompare(b))
        .forEach(value => {
            const option = document.createElement("option");
            option.value = value;
            option.textContent = value;
            select.appendChild(option);
        });

    select.value = [...select.options].some(
        option => option.value === previous
    )
        ? previous
        : "all";
}


function updateToolFilters() {
    updateSelectOptions(
        "tools-category-filter",
        tools.map(tool => tool.category),
        "All Categories"
    );
    updateSelectOptions(
        "tools-condition-filter",
        tools.map(tool => tool.condition),
        "All Conditions"
    );
    updateSelectOptions(
        "tools-availability-filter",
        tools.map(tool => tool.availability),
        "All Availability"
    );
}


function filteredTools() {
    const search = clean(
        document.getElementById("tools-search")?.value
    ).toLowerCase();
    const category =
        document.getElementById("tools-category-filter")?.value || "all";
    const condition =
        document.getElementById("tools-condition-filter")?.value || "all";
    const availability =
        document.getElementById("tools-availability-filter")?.value || "all";

    return tools.filter(tool => {
        const matchesSearch = !search || [
            tool.name,
            tool.category,
            tool.condition,
            tool.location,
            tool.availability,
            tool.notes
        ].some(value => (
            String(value ?? "").toLowerCase().includes(search)
        ));

        return (
            matchesSearch &&
            (category === "all" || tool.category === category) &&
            (condition === "all" || tool.condition === condition) &&
            (
                availability === "all" ||
                tool.availability === availability
            )
        );
    });
}


function sortedTools(items) {
    const sort =
        document.getElementById("tools-sort")?.value || "name-asc";
    const result = [...items];

    if (sort === "name-desc") {
        return result.sort(
            (a, b) => b.name.localeCompare(a.name)
        );
    }

    if (sort === "category-asc") {
        return result.sort(
            (a, b) => (
                a.category.localeCompare(b.category) ||
                a.name.localeCompare(b.name)
            )
        );
    }

    if (sort === "location-asc") {
        return result.sort(
            (a, b) => (
                a.location.localeCompare(b.location) ||
                a.name.localeCompare(b.name)
            )
        );
    }

    return result.sort(
        (a, b) => a.name.localeCompare(b.name)
    );
}


function renderToolRows(items) {
    const body = document.getElementById("tools-table-body");
    const empty = document.getElementById("tools-empty-state");

    if (!body || !empty) {
        return;
    }

    body.replaceChildren();
    empty.hidden = items.length > 0;

    for (const tool of items) {
        const row = document.createElement("tr");

        row.innerHTML = `
            <td>
                <strong class="resource-record-name"></strong>
                <span class="resource-record-note"></span>
            </td>
            <td class="tool-category"></td>
            <td class="tool-condition"></td>
            <td class="tool-location"></td>
            <td class="tool-availability"></td>
            <td>
                <button
                    class="table-action-button"
                    type="button"
                    data-action="maintenance"
                >
                    History
                </button>
            </td>
            <td>
                <div class="resource-row-actions">
                    <button
                        class="table-action-button"
                        type="button"
                        data-action="edit"
                    >
                        Edit
                    </button>

                    <button
                        class="table-action-button resource-delete-button"
                        type="button"
                        data-action="delete"
                    >
                        Delete
                    </button>
                </div>
            </td>
        `;

        row.querySelector(".resource-record-name").textContent =
            tool.name;
        row.querySelector(".resource-record-note").textContent =
            tool.notes || "";
        row.querySelector(".tool-category").textContent =
            tool.category;
        row.querySelector(".tool-condition").textContent =
            tool.condition;
        row.querySelector(".tool-location").textContent =
            tool.location;
        row.querySelector(".tool-availability").textContent =
            tool.availability;

        row.querySelectorAll("[data-action]").forEach(button => {
            button.dataset.id = tool.id;
        });

        body.appendChild(row);
    }
}


function renderTools() {
    updateToolFilters();
    renderToolRows(sortedTools(filteredTools()));
}


function populateToolForm(tool) {
    document.getElementById("tool-name").value = tool.name;
    document.getElementById("tool-category").value = tool.category;
    document.getElementById("tool-condition").value = tool.condition;
    document.getElementById("tool-location").value = tool.location;
    document.getElementById("tool-availability").value =
        tool.availability;
    document.getElementById("tool-notes").value = tool.notes || "";
}


function openToolDialog(tool = null) {
    const backdrop = document.getElementById("tool-dialog-backdrop");
    const form = document.getElementById("tool-form");

    if (!backdrop || !form) {
        return;
    }

    form.reset();
    editingToolId = tool?.id || null;

    setText(
        "tool-dialog-title",
        tool ? "Edit Tool" : "Add Tool"
    );
    setText("tool-form-error", "");

    if (tool) {
        populateToolForm(tool);
    }

    backdrop.hidden = false;
    document.body.classList.add("dialog-open");

    window.setTimeout(
        () => document.getElementById("tool-name")?.focus(),
        0
    );
}


function closeToolDialog() {
    const backdrop = document.getElementById("tool-dialog-backdrop");

    if (!backdrop) {
        return;
    }

    backdrop.hidden = true;
    editingToolId = null;
    document.getElementById("tool-form")?.reset();
    setText("tool-dialog-title", "Add Tool");
    setText("tool-form-error", "");
    document.body.classList.remove("dialog-open");
}


async function handleToolSubmit(event) {
    event.preventDefault();

    const data = toolPayload(new FormData(event.currentTarget));
    const submit = document.getElementById("save-tool");

    if (
        !data.name ||
        !data.category ||
        !data.condition ||
        !data.location ||
        !data.availability
    ) {
        setText(
            "tool-form-error",
            "Complete all required Tool fields."
        );
        return;
    }

    if (submit) {
        submit.disabled = true;
    }

    try {
        const saved = editingToolId
            ? await updateTool(editingToolId, data)
            : await createTool(data);

        tools = editingToolId
            ? tools.map(tool => (
                tool.id === saved.id ? saved : tool
            ))
            : [...tools, saved];

        const wasEditing = Boolean(editingToolId);

        closeToolDialog();
        renderTools();

        setToolsMessage(
            wasEditing ? "Tool updated." : "Tool added."
        );
    } catch (error) {
        console.error("Unable to save Tool:", error);
        setText(
            "tool-form-error",
            error.message || "The Tool could not be saved."
        );
    } finally {
        if (submit) {
            submit.disabled = false;
        }
    }
}


async function removeTool(toolId) {
    const tool = getTool(toolId);

    if (
        !tool ||
        !window.confirm(`Delete "${tool.name}" permanently?`)
    ) {
        return;
    }

    try {
        await deleteTool(tool.id);
        tools = tools.filter(current => current.id !== tool.id);
        renderTools();
        setToolsMessage("Tool deleted.");
    } catch (error) {
        console.error("Unable to delete Tool:", error);
        setToolsMessage(
            error.message ||
                "The Tool could not be deleted.",
            true
        );
    }
}


function setMaintenanceFormMode(record = null) {
    editingMaintenanceId = record?.id || null;

    const form = document.getElementById("maintenance-form");
    const cancel = document.getElementById(
        "cancel-maintenance-edit"
    );
    const save = document.getElementById("save-maintenance");

    form?.reset();
    setText("maintenance-form-error", "");
    setText(
        "maintenance-editor-heading",
        record ? "Edit Maintenance Record" : "Add Maintenance Record"
    );

    if (cancel) {
        cancel.hidden = !record;
    }

    if (save) {
        save.textContent = record ? "Save Changes" : "Add Record";
    }

    if (!record) {
        return;
    }

    document.getElementById("maintenance-type").value =
        record.maintenanceType;
    document.getElementById("maintenance-performed-at").value =
        maintenanceInputValue(record.performedAt);
    document.getElementById("maintenance-notes").value =
        record.notes || "";
}


function renderMaintenance() {
    const list = document.getElementById("maintenance-list");
    const empty = document.getElementById(
        "maintenance-empty-state"
    );

    if (!list || !empty) {
        return;
    }

    list.replaceChildren();

    const sorted = [...maintenanceRecords].sort(
        (a, b) => (
            new Date(b.performedAt).getTime() -
            new Date(a.performedAt).getTime()
        )
    );

    empty.hidden = sorted.length > 0;

    for (const record of sorted) {
        const article = document.createElement("article");
        article.className = "maintenance-record";

        const header = document.createElement("div");
        header.className = "maintenance-record-header";

        const details = document.createElement("div");
        const type = document.createElement("strong");
        const timestamp = document.createElement("span");

        type.textContent = record.maintenanceType;
        timestamp.textContent = formatTimestamp(
            record.performedAt
        );

        details.append(type, timestamp);

        const actions = document.createElement("div");
        actions.className = "resource-row-actions";

        const edit = document.createElement("button");
        edit.className = "table-action-button";
        edit.type = "button";
        edit.dataset.action = "edit-maintenance";
        edit.dataset.id = record.id;
        edit.textContent = "Edit";

        const remove = document.createElement("button");
        remove.className =
            "table-action-button resource-delete-button";
        remove.type = "button";
        remove.dataset.action = "delete-maintenance";
        remove.dataset.id = record.id;
        remove.textContent = "Delete";

        actions.append(edit, remove);
        header.append(details, actions);
        article.appendChild(header);

        if (record.notes) {
            const notes = document.createElement("p");
            notes.textContent = record.notes;
            article.appendChild(notes);
        }

        list.appendChild(article);
    }
}


async function openMaintenanceDialog(toolId) {
    const tool = getTool(toolId);
    const backdrop = document.getElementById(
        "maintenance-dialog-backdrop"
    );

    if (!tool || !backdrop) {
        return;
    }

    maintenanceToolId = tool.id;
    maintenanceRecords = [];
    setMaintenanceFormMode();

    setText(
        "maintenance-dialog-title",
        `Maintenance — ${tool.name}`
    );
    setMaintenanceMessage("Loading maintenance history...");
    renderMaintenance();

    backdrop.hidden = false;
    document.body.classList.add("dialog-open");

    try {
        maintenanceRecords = await listToolMaintenance(tool.id);
        renderMaintenance();
        setMaintenanceMessage("");
    } catch (error) {
        console.error(
            "Unable to load Tool maintenance:",
            error
        );
        setMaintenanceMessage(
            error.message ||
                "Maintenance history could not be loaded.",
            true
        );
    }
}


function closeMaintenanceDialog() {
    const backdrop = document.getElementById(
        "maintenance-dialog-backdrop"
    );

    if (!backdrop) {
        return;
    }

    backdrop.hidden = true;
    maintenanceToolId = null;
    maintenanceRecords = [];
    setMaintenanceFormMode();
    setMaintenanceMessage("");
    document.body.classList.remove("dialog-open");
}


async function handleMaintenanceSubmit(event) {
    event.preventDefault();

    if (!maintenanceToolId) {
        return;
    }

    const formData = new FormData(event.currentTarget);
    const maintenanceType = clean(
        formData.get("maintenanceType")
    );
    const performedAt = maintenanceTimestampFromLocal(
        formData.get("performedAt")
    );
    const notes = clean(formData.get("notes"));
    const submit = document.getElementById("save-maintenance");

    if (!maintenanceType || !performedAt) {
        setText(
            "maintenance-form-error",
            "Provide a maintenance type and valid performed-at time."
        );
        return;
    }

    const payload = {
        maintenanceType,
        performedAt,
        notes
    };

    if (submit) {
        submit.disabled = true;
    }

    try {
        const saved = editingMaintenanceId
            ? await updateToolMaintenance(
                maintenanceToolId,
                editingMaintenanceId,
                payload
            )
            : await createToolMaintenance(
                maintenanceToolId,
                payload
            );

        maintenanceRecords = editingMaintenanceId
            ? maintenanceRecords.map(record => (
                record.id === saved.id ? saved : record
            ))
            : [...maintenanceRecords, saved];

        const wasEditing = Boolean(editingMaintenanceId);

        setMaintenanceFormMode();
        renderMaintenance();
        setMaintenanceMessage(
            wasEditing
                ? "Maintenance record updated."
                : "Maintenance record added."
        );
    } catch (error) {
        console.error(
            "Unable to save maintenance record:",
            error
        );
        setText(
            "maintenance-form-error",
            error.message ||
                "The maintenance record could not be saved."
        );
    } finally {
        if (submit) {
            submit.disabled = false;
        }
    }
}


async function removeMaintenanceRecord(recordId) {
    const record = maintenanceRecords.find(
        current => current.id === recordId
    );

    if (
        !record ||
        !maintenanceToolId ||
        !window.confirm(
            "Delete this maintenance-history record?"
        )
    ) {
        return;
    }

    try {
        await deleteToolMaintenance(
            maintenanceToolId,
            record.id
        );

        maintenanceRecords = maintenanceRecords.filter(
            current => current.id !== record.id
        );

        if (editingMaintenanceId === record.id) {
            setMaintenanceFormMode();
        }

        renderMaintenance();
        setMaintenanceMessage("Maintenance record deleted.");
    } catch (error) {
        console.error(
            "Unable to delete maintenance record:",
            error
        );
        setMaintenanceMessage(
            error.message ||
                "The maintenance record could not be deleted.",
            true
        );
    }
}


function handleToolAction(event) {
    const button = event.target.closest("[data-action][data-id]");

    if (!button) {
        return;
    }

    const tool = getTool(button.dataset.id);

    if (!tool) {
        return;
    }

    if (button.dataset.action === "edit") {
        openToolDialog(tool);
    } else if (button.dataset.action === "delete") {
        void removeTool(tool.id);
    } else if (button.dataset.action === "maintenance") {
        void openMaintenanceDialog(tool.id);
    }
}


function handleMaintenanceAction(event) {
    const button = event.target.closest("[data-action][data-id]");

    if (!button) {
        return;
    }

    const record = maintenanceRecords.find(
        current => current.id === button.dataset.id
    );

    if (!record) {
        return;
    }

    if (button.dataset.action === "edit-maintenance") {
        setMaintenanceFormMode(record);
    } else if (
        button.dataset.action === "delete-maintenance"
    ) {
        void removeMaintenanceRecord(record.id);
    }
}


async function initializeToolPersistence() {
    try {
        tools = await listTools();
        renderTools();
        setToolsMessage("");

        return {
            status: "complete",
            tools
        };
    } catch (error) {
        console.error("Tools backend unavailable:", error);
        setToolsMessage(
            "Tools are unavailable from the backend.",
            true
        );

        return {
            status: "unavailable",
            error
        };
    }
}


export function initializeToolsPage() {
    if (toolsInitialized) {
        return Promise.resolve({
            status: "already-initialized",
            tools
        });
    }

    toolsInitialized = true;

    document.getElementById("add-tool")?.addEventListener(
        "click",
        () => openToolDialog()
    );
    document.getElementById(
        "empty-state-add-tool"
    )?.addEventListener(
        "click",
        () => openToolDialog()
    );
    document.getElementById(
        "close-tool-dialog"
    )?.addEventListener(
        "click",
        closeToolDialog
    );
    document.getElementById("cancel-tool")?.addEventListener(
        "click",
        closeToolDialog
    );
    document.getElementById("tool-form")?.addEventListener(
        "submit",
        event => void handleToolSubmit(event)
    );
    document.getElementById(
        "tool-dialog-backdrop"
    )?.addEventListener(
        "click",
        event => {
            if (event.target.id === "tool-dialog-backdrop") {
                closeToolDialog();
            }
        }
    );

    document.getElementById(
        "tools-table-body"
    )?.addEventListener(
        "click",
        handleToolAction
    );

    document.getElementById(
        "close-maintenance-dialog"
    )?.addEventListener(
        "click",
        closeMaintenanceDialog
    );
    document.getElementById(
        "done-maintenance"
    )?.addEventListener(
        "click",
        closeMaintenanceDialog
    );
    document.getElementById(
        "cancel-maintenance-edit"
    )?.addEventListener(
        "click",
        () => setMaintenanceFormMode()
    );
    document.getElementById(
        "maintenance-form"
    )?.addEventListener(
        "submit",
        event => void handleMaintenanceSubmit(event)
    );
    document.getElementById(
        "maintenance-list"
    )?.addEventListener(
        "click",
        handleMaintenanceAction
    );
    document.getElementById(
        "maintenance-dialog-backdrop"
    )?.addEventListener(
        "click",
        event => {
            if (
                event.target.id ===
                "maintenance-dialog-backdrop"
            ) {
                closeMaintenanceDialog();
            }
        }
    );

    document.getElementById("tools-search")?.addEventListener(
        "input",
        renderTools
    );

    [
        "tools-category-filter",
        "tools-condition-filter",
        "tools-availability-filter",
        "tools-sort"
    ].forEach(id => {
        document.getElementById(id)?.addEventListener(
            "change",
            renderTools
        );
    });

    document.addEventListener("keydown", event => {
        if (event.key === "Escape") {
            closeToolDialog();
            closeMaintenanceDialog();
        }
    });

    return initializeToolPersistence();
}
