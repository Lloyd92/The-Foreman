import {
    createCarePlan,
    deleteCarePlan,
    listCarePlans,
    updateCarePlan
} from "../utils/careApi.js";
import {
    listTools
} from "../utils/toolsApi.js";


let carePlans = [];
let careTools = [];
let editingCarePlanId = null;
let toolLookupState = "disabled";
let careInitialized = false;


function clean(value) {
    return String(value ?? "").trim();
}


function setText(id, value) {
    const element = document.getElementById(id);

    if (element) {
        element.textContent = value;
    }
}


function setCareMessage(message, isError = false) {
    const element = document.getElementById("care-page-message");

    if (!element) {
        return;
    }

    element.textContent = message;
    element.classList.toggle("error", isError);
}


function getCarePlan(carePlanId) {
    return carePlans.find(
        carePlan => carePlan.id === carePlanId
    ) || null;
}


function getCareTool(toolId) {
    return careTools.find(tool => tool.id === toolId) || null;
}


export function buildCarePayload({
    name,
    careType,
    toolId = "",
    description = "",
    frequencyValue = "",
    frequencyUnit = "",
    notes = ""
}) {
    const normalizedName = clean(name);
    const normalizedType = clean(careType);
    const normalizedToolId = clean(toolId) || null;
    const normalizedDescription = clean(description);
    const normalizedFrequencyValue = clean(frequencyValue);
    const normalizedFrequencyUnit = clean(frequencyUnit);
    const normalizedNotes = clean(notes);

    if (!normalizedName || !normalizedType) {
        throw new Error(
            "Care Plan name and care type are required."
        );
    }

    if (
        Boolean(normalizedFrequencyValue) !==
        Boolean(normalizedFrequencyUnit)
    ) {
        throw new Error(
            "Frequency value and unit must be provided together."
        );
    }

    let parsedFrequencyValue = null;
    let parsedFrequencyUnit = null;

    if (normalizedFrequencyValue) {
        parsedFrequencyValue = Number(normalizedFrequencyValue);

        if (
            !Number.isInteger(parsedFrequencyValue) ||
            parsedFrequencyValue <= 0
        ) {
            throw new Error(
                "Frequency value must be a positive whole number."
            );
        }

        parsedFrequencyUnit = normalizedFrequencyUnit;
    }

    return {
        name: normalizedName,
        careType: normalizedType,
        toolId: normalizedToolId,
        description: normalizedDescription,
        frequencyValue: parsedFrequencyValue,
        frequencyUnit: parsedFrequencyUnit,
        notes: normalizedNotes
    };
}


export function formatCareFrequency(carePlan) {
    if (
        carePlan.frequencyValue == null ||
        !carePlan.frequencyUnit
    ) {
        return "Not specified";
    }

    return (
        `${carePlan.frequencyValue} ` +
        `${carePlan.frequencyUnit}`
    );
}


function carePayloadFromForm(form) {
    const formData = new FormData(form);

    return buildCarePayload({
        name: formData.get("name"),
        careType: formData.get("careType"),
        toolId: formData.get("toolId"),
        description: formData.get("description"),
        frequencyValue: formData.get("frequencyValue"),
        frequencyUnit: formData.get("frequencyUnit"),
        notes: formData.get("notes")
    });
}


function updateCareTypeFilter() {
    const select = document.getElementById("care-type-filter");

    if (!select) {
        return;
    }

    const previous = select.value;
    select.replaceChildren();

    const all = document.createElement("option");
    all.value = "all";
    all.textContent = "All Care Types";
    select.appendChild(all);

    [...new Set(
        carePlans
            .map(carePlan => carePlan.careType)
            .filter(Boolean)
    )]
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


function filteredCarePlans() {
    const search = clean(
        document.getElementById("care-search")?.value
    ).toLowerCase();
    const careType =
        document.getElementById("care-type-filter")?.value ||
        "all";

    return carePlans.filter(carePlan => {
        const linkedTool = carePlan.toolId
            ? getCareTool(carePlan.toolId)
            : null;

        const matchesSearch = !search || [
            carePlan.name,
            carePlan.careType,
            carePlan.description,
            carePlan.notes,
            carePlan.toolId,
            linkedTool?.name
        ].some(value => (
            String(value ?? "").toLowerCase().includes(search)
        ));

        return (
            matchesSearch &&
            (
                careType === "all" ||
                carePlan.careType === careType
            )
        );
    });
}


function sortedCarePlans(items) {
    const sort =
        document.getElementById("care-sort")?.value ||
        "name-asc";
    const result = [...items];

    if (sort === "name-desc") {
        return result.sort(
            (a, b) => b.name.localeCompare(a.name)
        );
    }

    if (sort === "type-asc") {
        return result.sort(
            (a, b) => (
                a.careType.localeCompare(b.careType) ||
                a.name.localeCompare(b.name)
            )
        );
    }

    return result.sort(
        (a, b) => a.name.localeCompare(b.name)
    );
}


function careToolPresentation(carePlan) {
    if (!carePlan.toolId) {
        return "Independent";
    }

    const tool = getCareTool(carePlan.toolId);

    if (tool) {
        return tool.name;
    }

    if (toolLookupState === "disabled") {
        return `Linked Tool ID: ${carePlan.toolId}`;
    }

    if (toolLookupState === "unavailable") {
        return `Linked Tool ID: ${carePlan.toolId}`;
    }

    return `Tool reference unavailable: ${carePlan.toolId}`;
}


function renderCareRows(items) {
    const body = document.getElementById("care-table-body");
    const empty = document.getElementById("care-empty-state");

    if (!body || !empty) {
        return;
    }

    body.replaceChildren();
    empty.hidden = items.length > 0;

    for (const carePlan of items) {
        const row = document.createElement("tr");

        row.innerHTML = `
            <td>
                <strong class="resource-record-name"></strong>
                <span class="resource-record-note"></span>
            </td>
            <td class="care-type-value"></td>
            <td class="care-tool-value"></td>
            <td class="care-frequency-value"></td>
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
            carePlan.name;
        row.querySelector(".resource-record-note").textContent =
            carePlan.description || carePlan.notes || "";
        row.querySelector(".care-type-value").textContent =
            carePlan.careType;
        row.querySelector(".care-tool-value").textContent =
            careToolPresentation(carePlan);
        row.querySelector(".care-frequency-value").textContent =
            formatCareFrequency(carePlan);

        row.querySelectorAll("[data-action]").forEach(button => {
            button.dataset.id = carePlan.id;
        });

        body.appendChild(row);
    }
}


function notifyCareUpdated(status = "complete") {
    document.dispatchEvent(
        new CustomEvent(
            "care:updated",
            {
                detail: {
                    status,
                    carePlans: [...carePlans]
                }
            }
        )
    );
}


function renderCarePlans() {
    updateCareTypeFilter();
    renderCareRows(
        sortedCarePlans(filteredCarePlans())
    );
}


function appendToolOption(select, value, label) {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = label;
    select.appendChild(option);
}


function populateCareToolSelector(carePlan = null) {
    const select = document.getElementById("care-tool");
    const help = document.getElementById("care-tool-help");

    if (!select) {
        return;
    }

    select.replaceChildren();
    appendToolOption(select, "", "No linked Tool");

    if (toolLookupState === "available") {
        [...careTools]
            .sort((a, b) => a.name.localeCompare(b.name))
            .forEach(tool => {
                appendToolOption(
                    select,
                    tool.id,
                    `${tool.name} — ${tool.location}`
                );
            });
    }

    const currentToolId = carePlan?.toolId || null;

    if (
        currentToolId &&
        ![...select.options].some(
            option => option.value === currentToolId
        )
    ) {
        const suffix = toolLookupState === "disabled"
            ? "Tools module disabled"
            : toolLookupState === "unavailable"
                ? "Tool names unavailable"
                : "reference unavailable";

        appendToolOption(
            select,
            currentToolId,
            `${currentToolId} — ${suffix}`
        );
    }

    select.value = currentToolId || "";

    if (help) {
        if (toolLookupState === "disabled") {
            help.textContent =
                "Care remains available independently. " +
                "New Tool links are unavailable while the Tools " +
                "module is disabled.";
        } else if (toolLookupState === "unavailable") {
            help.textContent =
                "Tool names could not be loaded. Existing Tool IDs " +
                "are preserved as evidence.";
        } else {
            help.textContent =
                "A Care Plan may remain independent or reference " +
                "one Tool.";
        }
    }
}


function populateCareForm(carePlan) {
    document.getElementById("care-name").value =
        carePlan.name;
    document.getElementById("care-type").value =
        carePlan.careType;
    document.getElementById("care-description").value =
        carePlan.description || "";
    document.getElementById("care-frequency-value").value =
        carePlan.frequencyValue ?? "";
    document.getElementById("care-frequency-unit").value =
        carePlan.frequencyUnit || "";
    document.getElementById("care-notes").value =
        carePlan.notes || "";
}


function openCareDialog(carePlan = null) {
    const backdrop = document.getElementById(
        "care-dialog-backdrop"
    );
    const form = document.getElementById("care-form");

    if (!backdrop || !form) {
        return;
    }

    form.reset();
    editingCarePlanId = carePlan?.id || null;

    setText(
        "care-dialog-title",
        carePlan ? "Edit Care Plan" : "Add Care Plan"
    );
    setText("care-form-error", "");

    populateCareToolSelector(carePlan);

    if (carePlan) {
        populateCareForm(carePlan);
    }

    backdrop.hidden = false;
    document.body.classList.add("dialog-open");

    window.setTimeout(
        () => document.getElementById("care-name")?.focus(),
        0
    );
}


function closeCareDialog() {
    const backdrop = document.getElementById(
        "care-dialog-backdrop"
    );

    if (!backdrop) {
        return;
    }

    backdrop.hidden = true;
    editingCarePlanId = null;
    document.getElementById("care-form")?.reset();
    setText("care-dialog-title", "Add Care Plan");
    setText("care-form-error", "");
    document.body.classList.remove("dialog-open");
}


async function handleCareSubmit(event) {
    event.preventDefault();

    let payload;

    try {
        payload = carePayloadFromForm(event.currentTarget);
    } catch (error) {
        setText("care-form-error", error.message);
        return;
    }

    const submit = document.getElementById("save-care-plan");

    if (submit) {
        submit.disabled = true;
    }

    try {
        const saved = editingCarePlanId
            ? await updateCarePlan(
                editingCarePlanId,
                payload
            )
            : await createCarePlan(payload);

        carePlans = editingCarePlanId
            ? carePlans.map(carePlan => (
                carePlan.id === saved.id
                    ? saved
                    : carePlan
            ))
            : [...carePlans, saved];

        const wasEditing = Boolean(editingCarePlanId);

        closeCareDialog();
        renderCarePlans();
        notifyCareUpdated();

        setCareMessage(
            wasEditing
                ? "Care Plan updated."
                : "Care Plan added."
        );
    } catch (error) {
        console.error("Unable to save Care Plan:", error);
        setText(
            "care-form-error",
            error.message ||
                "The Care Plan could not be saved."
        );
    } finally {
        if (submit) {
            submit.disabled = false;
        }
    }
}


async function removeCarePlan(carePlanId) {
    const carePlan = getCarePlan(carePlanId);

    if (
        !carePlan ||
        !window.confirm(
            `Delete Care Plan "${carePlan.name}" permanently?`
        )
    ) {
        return;
    }

    try {
        await deleteCarePlan(carePlan.id);
        carePlans = carePlans.filter(
            current => current.id !== carePlan.id
        );
        renderCarePlans();
        notifyCareUpdated();
        setCareMessage("Care Plan deleted.");
    } catch (error) {
        console.error("Unable to delete Care Plan:", error);
        setCareMessage(
            error.message ||
                "The Care Plan could not be deleted.",
            true
        );
    }
}


function handleCareAction(event) {
    const button = event.target.closest("[data-action][data-id]");

    if (!button) {
        return;
    }

    const carePlan = getCarePlan(button.dataset.id);

    if (!carePlan) {
        return;
    }

    if (button.dataset.action === "edit") {
        openCareDialog(carePlan);
    } else if (button.dataset.action === "delete") {
        void removeCarePlan(carePlan.id);
    }
}


async function initializeCarePersistence({
    toolsEnabled
}) {
    try {
        carePlans = await listCarePlans();
    } catch (error) {
        console.error("Care backend unavailable:", error);
        setCareMessage(
            "Care Plans are unavailable from the backend.",
            true
        );
        notifyCareUpdated("unavailable");

        return {
            status: "unavailable",
            error
        };
    }

    careTools = [];

    if (toolsEnabled) {
        try {
            careTools = await listTools();
            toolLookupState = "available";
        } catch (error) {
            console.error(
                "Tool names unavailable to Care:",
                error
            );
            toolLookupState = "unavailable";
        }
    } else {
        toolLookupState = "disabled";
    }

    renderCarePlans();
    notifyCareUpdated();

    if (toolLookupState === "unavailable") {
        setCareMessage(
            "Care Plans are available. Tool names could not be " +
            "loaded, so existing Tool IDs are shown as evidence.",
            true
        );
    } else {
        setCareMessage("");
    }

    return {
        status: "complete",
        carePlans,
        toolLookupState
    };
}


export function initializeCarePage({
    toolsEnabled = true
} = {}) {
    if (careInitialized) {
        return Promise.resolve({
            status: "already-initialized",
            carePlans
        });
    }

    careInitialized = true;

    document.getElementById(
        "add-care-plan"
    )?.addEventListener(
        "click",
        () => openCareDialog()
    );
    document.getElementById(
        "empty-state-add-care-plan"
    )?.addEventListener(
        "click",
        () => openCareDialog()
    );
    document.getElementById(
        "close-care-dialog"
    )?.addEventListener(
        "click",
        closeCareDialog
    );
    document.getElementById(
        "cancel-care-plan"
    )?.addEventListener(
        "click",
        closeCareDialog
    );
    document.getElementById(
        "care-form"
    )?.addEventListener(
        "submit",
        event => void handleCareSubmit(event)
    );
    document.getElementById(
        "care-dialog-backdrop"
    )?.addEventListener(
        "click",
        event => {
            if (event.target.id === "care-dialog-backdrop") {
                closeCareDialog();
            }
        }
    );
    document.getElementById(
        "care-table-body"
    )?.addEventListener(
        "click",
        handleCareAction
    );

    document.getElementById("care-search")?.addEventListener(
        "input",
        renderCarePlans
    );

    [
        "care-type-filter",
        "care-sort"
    ].forEach(id => {
        document.getElementById(id)?.addEventListener(
            "change",
            renderCarePlans
        );
    });

    document.addEventListener("keydown", event => {
        if (event.key === "Escape") {
            closeCareDialog();
        }
    });

    return initializeCarePersistence({
        toolsEnabled
    });
}
