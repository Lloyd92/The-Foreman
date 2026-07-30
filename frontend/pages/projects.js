import {
    getOperationalFacts,
    getProjectMaterialReadinessFact
} from "../utils/operationsApi.js";
import {
    listInventoryItems
} from "../utils/inventoryApi.js";
import { BackendApiError } from "../utils/api.js";
import {
    addProjectMaterial,
    createProject,
    deleteProject,
    deleteProjectMaterial,
    listProjects,
    updateProject,
    updateProjectMaterial
} from "../utils/projectsApi.js";
import {
    loadBackendProjects,
    mergePersistedProject,
    removePersistedProject
} from "../utils/projectRuntime.js";

let editingProjectId = null;
let materialsProjectId = null;
let editingMaterialInventoryId = null;
let inventoryItems = [];
let inventoryRevision = 0;
let projects = [];
let projectOperationalFacts = null;
let projectRequestPending = false;
let materialRequestPending = false;
let projectsInitialized = false;

function getProjectMaterials(project) {
    return Array.isArray(project?.materials)
        ? project.materials
        : [];
}

function notifyProjectsUpdated() {
    document.dispatchEvent(
        new CustomEvent("projects:updated", {
            detail: { projects: [...projects] }
        })
    );
}

function formatApiError(error, subject) {
    if (!(error instanceof BackendApiError)) {
        return error instanceof TypeError
            ? `The backend is unavailable. Retry ${subject} when the connection is restored.`
            : `The backend returned an unexpected response while ${subject}.`;
    }

    if (error.status === 404) {
        return `The requested ${subject} no longer exists.`;
    }

    if (error.status === 409) {
        return `The ${subject} conflicts with persisted data. Refresh and try again.`;
    }

    if (error.status === 422) {
        return `The ${subject} contains invalid data. Check the fields and try again.`;
    }

    return error.status >= 500 || error.status === 0
        ? `The backend could not complete ${subject}. Please retry.`
        : `The ${subject} could not be completed.`;
}

function replaceProject(project) {
    projects = mergePersistedProject(projects, project);
}

function setProjectsMessage(message, isError = false) {
    const messageElement = document.getElementById(
        "projects-page-message"
    );

    if (!messageElement) {
        return;
    }

    messageElement.textContent = message;
    messageElement.classList.toggle("error", isError);
}

function setProjectDialogMode(isEditing) {
    const title = document.getElementById(
        "project-dialog-title"
    );
    const submitButton = document.getElementById(
        "save-project"
    );

    if (title) {
        title.textContent = isEditing
            ? "Edit Project"
            : "Add Project";
    }

    if (submitButton) {
        submitButton.textContent = isEditing
            ? "Save Changes"
            : "Save Project";
    }
}

function populateProjectForm(project) {
    document.getElementById("project-name").value =
        project.name || "";
    document.getElementById("project-type").value =
        project.type || "build";
    document.getElementById("project-status").value =
        project.status || "planning";
    document.getElementById("project-priority").value =
        project.priority || "medium";
    document.getElementById("project-progress").value =
        project.progress ?? 0;
    document.getElementById("project-start-date").value =
        project.startDate || "";
    document.getElementById("project-target-date").value =
        project.targetDate || "";
    document.getElementById("project-estimated-cost").value =
        project.estimatedCost ?? 0;
    document.getElementById("project-description").value =
        project.description || "";
    document.getElementById("project-notes").value =
        project.notes || "";
}

function openProjectDialog(project = null) {
    const backdrop = document.getElementById(
        "project-dialog-backdrop"
    );
    const form = document.getElementById("project-form");

    if (!backdrop) {
        return;
    }

    form?.reset();
    editingProjectId = project?.id || null;
    setProjectDialogMode(Boolean(project));

    if (project) {
        populateProjectForm(project);
    }

    backdrop.hidden = false;
    document.body.classList.add("dialog-open");

    window.setTimeout(() => {
        document.getElementById("project-name")?.focus();
    }, 0);
}

function closeProjectDialog() {
    if (projectRequestPending) {
        return;
    }

    const backdrop = document.getElementById(
        "project-dialog-backdrop"
    );
    const errorElement = document.getElementById(
        "project-form-error"
    );

    if (!backdrop) {
        return;
    }

    backdrop.hidden = true;
    document.body.classList.remove("dialog-open");
    editingProjectId = null;
    document.getElementById("project-form")?.reset();
    setProjectDialogMode(false);

    if (errorElement) {
        errorElement.textContent = "";
    }
}

function getVisibleProjects() {
    const searchValue = document
        .getElementById("projects-search")
        ?.value.trim()
        .toLowerCase() || "";

    const statusValue = document
        .getElementById("projects-status-filter")
        ?.value || "all";

    const sortValue = document
        .getElementById("projects-sort")
        ?.value || "name-asc";

    const filtered = projects.filter(project => {
        const searchableText = [
            project.name,
            project.type,
            project.description,
            project.notes
        ].join(" ").toLowerCase();
        const matchesSearch =
            !searchValue ||
            searchableText.includes(searchValue);

        const matchesStatus =
            statusValue === "all" ||
            project.status === statusValue;

        return matchesSearch && matchesStatus;
    });

    return [...filtered].sort((a, b) => {
        switch (sortValue) {
            case "name-desc":
                return b.name.localeCompare(a.name);
            case "progress-desc":
                return b.progress - a.progress;
            case "progress-asc":
                return a.progress - b.progress;
            case "newest":
                return (
                    new Date(b.createdAt) -
                    new Date(a.createdAt)
                );
            case "name-asc":
            default:
                return a.name.localeCompare(b.name);
        }
    });
}

function formatLabel(value) {
    return (value || "not set")
        .replaceAll("-", " ")
        .replace(/\b\w/g, letter => letter.toUpperCase());
}

function formatDate(value) {
    if (!value) {
        return "Not set";
    }

    return new Intl.DateTimeFormat(undefined, {
        year: "numeric",
        month: "short",
        day: "numeric",
        timeZone: "UTC"
    }).format(new Date(`${value}T00:00:00Z`));
}

function formatCost(value) {
    return new Intl.NumberFormat(undefined, {
        style: "currency",
        currency: "USD"
    }).format(Number(value) || 0);
}

function formatQuantity(value) {
    return new Intl.NumberFormat(undefined, {
        maximumFractionDigits: 6
    }).format(Number(value) || 0);
}

function formatOperationalQuantity(value) {
    if (value === null) {
        return "Unknown";
    }
    if (typeof value === "string") {
        return value;
    }

    return new Intl.NumberFormat(undefined, {
        maximumFractionDigits: 6
    }).format(value);
}

export function getProjectReadinessPresentation(fact) {
    if (!fact) {
        return {
            state: "unknown",
            label: "READINESS UNAVAILABLE"
        };
    }

    const labels = {
        ready: "READY",
        "needs-materials": "NEEDS MATERIALS",
        "not-applicable": "NOT APPLICABLE",
        invalid: "INVALID MATERIAL DATA"
    };

    return {
        state: fact.state,
        label: labels[fact.state] ?? "READINESS UNAVAILABLE"
    };
}

export function getMaterialEvidencePresentation(evidence) {
    const labels = {
        PROJECT_MATERIALS_SUFFICIENT: "SUFFICIENT",
        PROJECT_MATERIAL_QUANTITY_INSUFFICIENT: "INSUFFICIENT",
        PROJECT_MATERIAL_INVENTORY_MISSING: "MISSING INVENTORY",
        PROJECT_MATERIAL_DATA_INVALID: "INVALID DATA"
    };

    return {
        status: labels[evidence.reasonCode] ??
            "EVIDENCE UNAVAILABLE",
        itemName: evidence.itemName ?? "Missing inventory item",
        unit: evidence.unit ?? "unit unavailable",
        available: formatOperationalQuantity(
            evidence.availableQuantity
        ),
        required: formatOperationalQuantity(
            evidence.requiredQuantity
        ),
        shortage: formatOperationalQuantity(
            evidence.shortageQuantity
        ),
        isSufficient:
            evidence.reasonCode === "PROJECT_MATERIALS_SUFFICIENT"
    };
}

function readinessClass(state) {
    if (state === "ready") {
        return "project-readiness-ready";
    }

    if (state === "needs-materials") {
        return "project-readiness-needs-materials";
    }

    return "project-readiness-empty";
}

function updateProjectSummary() {
    const total = document.getElementById(
        "projects-total-count"
    );
    const active = document.getElementById(
        "projects-active-count"
    );
    const completed = document.getElementById(
        "projects-completed-count"
    );

    if (total) {
        total.textContent = projects.length;
    }

    if (active) {
        active.textContent = projects.filter(
            project => project.status === "active"
        ).length;
    }

    if (completed) {
        completed.textContent = projects.filter(
            project => project.status === "completed"
        ).length;
    }
}

function renderProjects() {
    const list = document.getElementById("projects-list");
    const emptyState = document.getElementById(
        "projects-empty-state"
    );

    if (!list || !emptyState) {
        return;
    }

    const visibleProjects = getVisibleProjects();

    list.innerHTML = "";
    emptyState.hidden = projects.length > 0;

    visibleProjects.forEach(project => {
        const card = document.createElement("article");
        const statusLabel = formatLabel(project.status);
        const priorityLabel = formatLabel(project.priority);
        const readinessFact = projectOperationalFacts
            ? getProjectMaterialReadinessFact(
                projectOperationalFacts,
                project.id
            )
            : null;
        const readiness = getProjectReadinessPresentation(
            readinessFact
        );
        const controls = project.status === "archived"
            ? ""
            : `
                <div class="project-card-actions">
                    <button
                        class="table-action-button"
                        type="button"
                        data-action="materials"
                        data-id="${project.id}"
                    >
                        Materials
                    </button>
                    <button
                        class="table-action-button"
                        type="button"
                        data-action="edit"
                        data-id="${project.id}"
                    >
                        Edit
                    </button>
                    <button
                        class="table-action-button delete-project-button"
                        type="button"
                        data-action="delete"
                        data-id="${project.id}"
                    >
                        Delete
                    </button>
                </div>
            `;

        card.className = "project-card";
        card.innerHTML = `
            <div class="project-card-heading">
                <div>
                    <h3 class="project-name"></h3>
                    <div class="project-card-labels">
                        <span class="project-status"></span>
                        <span class="project-priority"></span>
                    </div>
                </div>
                ${controls}
            </div>

            <div class="project-progress-heading">
                <span>Progress</span>
                <strong>${project.progress}%</strong>
            </div>

            <div
                class="project-progress-track"
                aria-label="${project.progress}% complete"
            >
                <span style="width: ${project.progress}%"></span>
            </div>

            <dl class="project-details">
                <div>
                    <dt>Type</dt>
                    <dd class="project-type"></dd>
                </div>
                <div>
                    <dt>Start Date</dt>
                    <dd class="project-start-date"></dd>
                </div>
                <div>
                    <dt>Target Date</dt>
                    <dd class="project-target-date"></dd>
                </div>
                <div>
                    <dt>Estimated Cost</dt>
                    <dd class="project-cost"></dd>
                </div>
            </dl>

            <p class="project-description"></p>

            <div class="project-readiness-summary">
                <span>Material Readiness</span>
                <strong class="${readinessClass(readiness.state)}">
                    ${readiness.label}
                </strong>
            </div>
        `;

        card.querySelector(".project-name").textContent =
            project.name;
        card.querySelector(".project-status").textContent =
            statusLabel;
        card.querySelector(".project-priority").textContent =
            `${priorityLabel} Priority`;
        card.querySelector(".project-type").textContent =
            formatLabel(project.type);
        card.querySelector(".project-start-date").textContent =
            formatDate(project.startDate);
        card.querySelector(".project-target-date").textContent =
            formatDate(project.targetDate);
        card.querySelector(".project-cost").textContent =
            formatCost(project.estimatedCost);
        card.querySelector(".project-description").textContent =
            project.description || "No project description.";

        list.appendChild(card);
    });

    if (projects.length > 0 && visibleProjects.length === 0) {
        const message = document.createElement("p");
        message.className = "empty-message";
        message.textContent =
            "No projects match the current search and filters.";
        list.appendChild(message);
    }

    updateProjectSummary();
}

function setProjectsLoading() {
    const list = document.getElementById("projects-list");
    const empty = document.getElementById("projects-empty-state");

    if (list) {
        list.innerHTML = "";
    }
    if (empty) {
        empty.hidden = true;
    }
    const retry = document.getElementById("retry-projects");
    if (retry) {
        retry.hidden = true;
    }
    setProjectsMessage("Loading projects…");
}

async function refreshProjects() {
    setProjectsLoading();

    try {
        projects = await loadBackendProjects(listProjects);
        renderProjects();
        notifyProjectsUpdated();
        setProjectsMessage("");
        return true;
    } catch (error) {
        projects = [];
        renderProjects();
        document.getElementById(
            "projects-empty-state"
        )?.setAttribute("hidden", "");
        setProjectsMessage(
            formatApiError(error, "loading Projects"),
            true
        );
        const retry = document.getElementById("retry-projects");
        if (retry) {
            retry.hidden = false;
        }
        return false;
    }
}

async function refreshProjectOperationalFacts() {
    projectOperationalFacts = null;
    renderProjects();

    if (materialsProjectId) {
        renderMaterialsDialog();
    }

    try {
        projectOperationalFacts = await getOperationalFacts();
    } catch (error) {
        console.error(
            "Unable to load backend operational facts for Projects:",
            error
        );
        return false;
    }

    renderProjects();

    if (materialsProjectId) {
        renderMaterialsDialog();
    }

    return true;
}

function getMaterialsProject() {
    return projects.find(
        project => project.id === materialsProjectId
    ) || null;
}

function updateMaterialSelector(project) {
    const selector = document.getElementById(
        "material-inventory-item"
    );
    const emptyMessage = document.getElementById(
        "materials-inventory-message"
    );
    const addButton = document.getElementById(
        "add-material-requirement"
    );

    if (!selector || !emptyMessage || !addButton) {
        return;
    }

    const existingIds = new Set(
        getProjectMaterials(project).map(
            requirement => requirement.inventoryItemId
        )
    );
    const availableItems = inventoryItems
        .filter(item =>
            !existingIds.has(item.id) ||
            item.id === editingMaterialInventoryId
        )
        .sort((a, b) => a.name.localeCompare(b.name));

    selector.innerHTML = "";

    availableItems.forEach(item => {
        const option = document.createElement("option");
        option.value = item.id;
        option.textContent =
            `${item.name} — ${formatQuantity(item.quantity)} ${item.unit}`;
        selector.appendChild(option);
    });

    if (
        editingMaterialInventoryId &&
        !inventoryItems.some(
            item => item.id === editingMaterialInventoryId
        )
    ) {
        const option = document.createElement("option");
        option.value = editingMaterialInventoryId;
        option.textContent =
            `Missing inventory item — ${editingMaterialInventoryId}`;
        selector.appendChild(option);
    }

    if (editingMaterialInventoryId) {
        selector.value = editingMaterialInventoryId;
    }

    const noInventory = inventoryItems.length === 0;
    const allAlreadyRequired =
        !noInventory && availableItems.length === 0;

    selector.disabled = editingMaterialInventoryId
        ? true
        : availableItems.length === 0;
    addButton.disabled = materialRequestPending ||
        (!editingMaterialInventoryId && availableItems.length === 0);
    emptyMessage.textContent = noInventory
        ? "No inventory is available. Add an inventory item before adding a material requirement."
        : allAlreadyRequired
            ? "Every available inventory item is already required by this project."
            : "";
}

function setMaterialFormMode(requirement = null) {
    editingMaterialInventoryId =
        requirement?.inventoryItemId || null;
    const heading = document.getElementById(
        "add-material-heading"
    );
    const submit = document.getElementById(
        "add-material-requirement"
    );
    const cancel = document.getElementById(
        "cancel-material-edit"
    );
    const form = document.getElementById(
        "material-requirement-form"
    );

    form?.reset();
    if (heading) {
        heading.textContent = requirement
            ? "Edit Material"
            : "Add Material";
    }
    if (submit) {
        submit.textContent = requirement
            ? "Save Material"
            : "Add Material";
    }
    if (cancel) {
        cancel.hidden = !requirement;
    }
    if (requirement) {
        document.getElementById(
            "material-required-quantity"
        ).value = requirement.requiredQuantity;
        document.getElementById("material-note").value =
            requirement.note || "";
    }

    const project = getMaterialsProject();
    if (project) {
        updateMaterialSelector(project);
    }
}

function renderMaterialsDialog() {
    const project = getMaterialsProject();
    const title = document.getElementById(
        "materials-dialog-project-name"
    );
    const readinessElement = document.getElementById(
        "materials-dialog-readiness"
    );
    const list = document.getElementById(
        "materials-requirements-list"
    );
    const empty = document.getElementById(
        "materials-requirements-empty"
    );

    if (
        !project ||
        !title ||
        !readinessElement ||
        !list ||
        !empty
    ) {
        return;
    }

    const readinessFact = projectOperationalFacts
        ? getProjectMaterialReadinessFact(
            projectOperationalFacts,
            project.id
        )
        : null;
    const readiness = getProjectReadinessPresentation(
        readinessFact
    );
    const evidenceRequirements =
        readinessFact?.evidence.requirements ?? [];
    const projectMaterials = getProjectMaterials(project);
    const displayedRequirements = readinessFact
        ? evidenceRequirements
        : projectMaterials.map(requirement => {
            const inventoryItem = inventoryItems.find(
                item => (
                    item.id === requirement.inventoryItemId
                )
            ) ?? null;

            return {
                inventoryItemId: requirement.inventoryItemId,
                itemName: inventoryItem?.name ?? null,
                unit: inventoryItem?.unit ?? null,
                requiredQuantity: requirement.requiredQuantity,
                availableQuantity: null,
                shortageQuantity: null,
                reasonCode: null
            };
        });

    title.textContent = project.name;
    readinessElement.textContent = readiness.label;
    readinessElement.className =
        `project-readiness-badge ${readinessClass(readiness.state)}`;
    list.innerHTML = "";
    empty.hidden = displayedRequirements.length > 0;
    empty.textContent = readinessFact
        ? "No materials are listed for this project."
        : (
            "Operational material evidence is unavailable for " +
            "this Project state."
        );

    displayedRequirements.forEach(evidence => {
        const row = document.createElement("article");
        const requirement = getProjectMaterials(project).find(
            item => (
                item.inventoryItemId ===
                evidence.inventoryItemId
            )
        );
        const presentation = getMaterialEvidencePresentation(
            evidence
        );
        const inventoryItem = inventoryItems.find(
            item => item.id === evidence.inventoryItemId
        ) ?? null;

        row.className = "material-requirement";
        row.innerHTML = `
            <div class="material-requirement-heading">
                <div>
                    <strong class="material-requirement-name"></strong>
                    <span class="material-requirement-reference"></span>
                </div>
                <span class="material-requirement-status"></span>
            </div>
            <dl class="material-quantities">
                <div>
                    <dt>Available</dt>
                    <dd>${presentation.available} ${presentation.unit}</dd>
                </div>
                <div>
                    <dt>Required</dt>
                    <dd>${presentation.required} ${presentation.unit}</dd>
                </div>
                <div>
                    <dt>Shortage</dt>
                    <dd>${presentation.shortage} ${presentation.unit}</dd>
                </div>
            </dl>
            <p class="material-requirement-note"></p>
            <div class="project-card-actions">
                <button
                    class="table-action-button"
                    type="button"
                    data-action="edit-material"
                    data-inventory-id="${evidence.inventoryItemId}"
                >
                    Edit Material
                </button>
                <button
                    class="table-action-button delete-project-button"
                    type="button"
                    data-action="remove-material"
                    data-inventory-id="${evidence.inventoryItemId}"
                >
                    Remove Material
                </button>
            </div>
        `;

        row.querySelector(".material-requirement-name").textContent =
            presentation.itemName;
        row.querySelector(".material-requirement-reference").textContent =
            evidence.itemName === null
                ? `Inventory reference: ${evidence.inventoryItemId}`
                : inventoryItem?.category ?? (
                    `Inventory reference: ${evidence.inventoryItemId}`
                );
        const statusElement = row.querySelector(
            ".material-requirement-status"
        );
        statusElement.textContent = presentation.status;
        statusElement.classList.add(
            presentation.isSufficient
                ? "material-status-sufficient"
                : "material-status-insufficient"
        );
        row.querySelector(".material-requirement-note").textContent =
            requirement?.note || "No note.";
        list.appendChild(row);
    });

    updateMaterialSelector(project);
}

function openMaterialsDialog(project) {
    const backdrop = document.getElementById(
        "materials-dialog-backdrop"
    );

    if (!backdrop || project.status === "archived") {
        return;
    }

    materialsProjectId = project.id;
    setMaterialFormMode();
    renderMaterialsDialog();
    backdrop.hidden = false;
    document.body.classList.add("dialog-open");
}

function closeMaterialsDialog() {
    if (materialRequestPending) {
        return;
    }

    const backdrop = document.getElementById(
        "materials-dialog-backdrop"
    );

    if (!backdrop) {
        return;
    }

    backdrop.hidden = true;
    document.body.classList.remove("dialog-open");
    materialsProjectId = null;
    editingMaterialInventoryId = null;
    document.getElementById("material-requirement-form")?.reset();

    const error = document.getElementById(
        "material-requirement-error"
    );

    if (error) {
        error.textContent = "";
    }
}

async function handleMaterialSubmit(event) {
    event.preventDefault();
    if (materialRequestPending) {
        return;
    }
    const project = getMaterialsProject();
    const formData = new FormData(event.currentTarget);
    const inventoryItemId = editingMaterialInventoryId ||
        formData.get("inventoryItemId");
    const requiredQuantity = Number(
        formData.get("requiredQuantity")
    );
    const error = document.getElementById(
        "material-requirement-error"
    );

    if (!project || (
        !editingMaterialInventoryId &&
        !inventoryItems.some(item => item.id === inventoryItemId)
    )) {
        if (error) {
            error.textContent =
                "Select an available inventory item.";
        }
        return;
    }

    if (
        !Number.isFinite(requiredQuantity) ||
        requiredQuantity <= 0
    ) {
        if (error) {
            error.textContent =
                "Required quantity must be greater than zero.";
        }
        return;
    }

    const materials = getProjectMaterials(project);

    if (!editingMaterialInventoryId && materials.some(
        requirement =>
            requirement.inventoryItemId === inventoryItemId
    )) {
        if (error) {
            error.textContent =
                "That inventory item is already required.";
        }
        return;
    }

    const requirement = {
        inventoryItemId,
        requiredQuantity,
        note: formData.get("note").trim()
    };
    const submit = document.getElementById(
        "add-material-requirement"
    );
    materialRequestPending = true;
    if (submit) {
        submit.disabled = true;
    }

    try {
        const persistedProject = editingMaterialInventoryId
            ? await updateProjectMaterial(
                project.id,
                editingMaterialInventoryId,
                {
                    requiredQuantity,
                    note: requirement.note
                }
            )
            : await addProjectMaterial(project.id, requirement);
        replaceProject(persistedProject);
        await refreshProjectOperationalFacts();
    } catch (requestError) {
        if (error) {
            error.textContent =
                formatApiError(
                    requestError,
                    "material requirement"
                );
        }
        materialRequestPending = false;
        if (submit) {
            submit.disabled = false;
        }
        return;
    }

    materialRequestPending = false;
    setMaterialFormMode();
    renderProjects();
    notifyProjectsUpdated();
    renderMaterialsDialog();

    if (error) {
        error.textContent = "";
    }
}

async function handleMaterialListAction(event) {
    const button = event.target.closest(
        '[data-action][data-inventory-id]'
    );
    const project = getMaterialsProject();

    if (!button || !project || materialRequestPending) {
        return;
    }

    const materials = getProjectMaterials(project);
    const requirement = materials.find(
        item =>
            item.inventoryItemId === button.dataset.inventoryId
    );

    if (!requirement) {
        return;
    }

    if (button.dataset.action === "edit-material") {
        setMaterialFormMode(requirement);
        return;
    }

    if (
        button.dataset.action !== "remove-material" ||
        !window.confirm(
            "Remove this material requirement from the project?"
        )
    ) {
        return;
    }

    materialRequestPending = true;
    button.disabled = true;

    try {
        const persistedProject = await deleteProjectMaterial(
            project.id,
            requirement.inventoryItemId
        );
        replaceProject(persistedProject);
        await refreshProjectOperationalFacts();
    } catch (error) {
        const errorElement = document.getElementById(
            "material-requirement-error"
        );
        if (errorElement) {
            errorElement.textContent = formatApiError(
                error,
                "material requirement"
            );
        }
        materialRequestPending = false;
        button.disabled = false;
        return;
    }

    materialRequestPending = false;
    if (
        editingMaterialInventoryId ===
        requirement.inventoryItemId
    ) {
        setMaterialFormMode();
    }
    renderProjects();
    notifyProjectsUpdated();
    renderMaterialsDialog();
}

async function handleProjectSubmit(event) {
    event.preventDefault();
    if (projectRequestPending) {
        return;
    }

    const form = event.currentTarget;
    const formData = new FormData(form);
    const errorElement = document.getElementById(
        "project-form-error"
    );

    const name = formData.get("name").trim();

    if (!name) {
        if (errorElement) {
            errorElement.textContent = "Project name is required.";
        }
        return;
    }

    const progress = Number(formData.get("progress"));
    const estimatedCost = Number(
        formData.get("estimatedCost") || 0
    );

    if (
        !Number.isFinite(progress) ||
        progress < 0 ||
        progress > 100
    ) {
        if (errorElement) {
            errorElement.textContent =
                "Progress must be between 0 and 100.";
        }
        return;
    }

    if (!Number.isFinite(estimatedCost) || estimatedCost < 0) {
        if (errorElement) {
            errorElement.textContent =
                "Estimated cost must be zero or greater.";
        }
        return;
    }

    const projectChanges = {
        name,
        type: formData.get("type"),
        status: formData.get("status"),
        priority: formData.get("priority"),
        progress,
        startDate: formData.get("startDate") || null,
        targetDate: formData.get("targetDate") || null,
        estimatedCost,
        description: formData.get("description").trim(),
        notes: formData.get("notes").trim()
    };

    const submit = document.getElementById("save-project");
    projectRequestPending = true;
    if (submit) {
        submit.disabled = true;
    }

    try {
        const persistedProject = editingProjectId
            ? await updateProject(
                editingProjectId,
                projectChanges
            )
            : await createProject({
                ...projectChanges,
                materials: []
            });
        replaceProject(persistedProject);
        await refreshProjectOperationalFacts();
    } catch (error) {
        if (errorElement) {
            errorElement.textContent =
                formatApiError(
                    error,
                    editingProjectId
                        ? "updating the Project"
                        : "creating the Project"
                );
        }
        projectRequestPending = false;
        if (submit) {
            submit.disabled = false;
        }
        return;
    }

    const wasEditing = Boolean(editingProjectId);
    projectRequestPending = false;
    if (submit) {
        submit.disabled = false;
    }
    closeProjectDialog();
    renderProjects();
    notifyProjectsUpdated();
    setProjectsMessage(
        wasEditing ? "Project updated." : "Project created."
    );
}

async function handleProjectAction(event) {
    const button = event.target.closest(
        "[data-action][data-id]"
    );

    if (!button || projectRequestPending) {
        return;
    }

    const project = projects.find(
        item => item.id === button.dataset.id
    );

    if (!project || project.status === "archived") {
        return;
    }

    if (button.dataset.action === "edit") {
        openProjectDialog(project);
        return;
    }

    if (button.dataset.action === "materials") {
        openMaterialsDialog(project);
        return;
    }

    if (button.dataset.action !== "delete") {
        return;
    }

    if (!window.confirm(`Delete "${project.name}" permanently?`)) {
        return;
    }

    projectRequestPending = true;
    button.disabled = true;

    try {
        await deleteProject(project.id);
    } catch (error) {
        setProjectsMessage(
            formatApiError(error, "deleting the Project"),
            true
        );
        projectRequestPending = false;
        button.disabled = false;
        return;
    }

    projectRequestPending = false;
    projects = removePersistedProject(projects, project.id);
    await refreshProjectOperationalFacts();
    renderProjects();
    notifyProjectsUpdated();
    setProjectsMessage("Project deleted.");
}

function openAddProjectDialog() {
    openProjectDialog();
}

function handleBackdropClick(event) {
    if (event.target.id === "project-dialog-backdrop") {
        closeProjectDialog();
    }
}

function handleEscapeKey(event) {
    if (event.key === "Escape") {
        closeProjectDialog();
        closeMaterialsDialog();
    }
}

async function loadProjectInventory() {
    const startingRevision = inventoryRevision;

    try {
        const loadedItems = await listInventoryItems();

        if (inventoryRevision === startingRevision) {
            inventoryItems = loadedItems;
        }
    } catch (error) {
        console.error(
            "Unable to load backend inventory for Projects:",
            error
        );

        if (inventoryRevision === startingRevision) {
            inventoryItems = [];
        }
    }

    renderProjects();

    if (materialsProjectId) {
        renderMaterialsDialog();
    }
}

export async function initializeProjectsPage(
    projectMigration = Promise.resolve()
) {
    if (projectsInitialized) {
        return;
    }
    projectsInitialized = true;
    const addButton = document.getElementById("add-project");
    const emptyStateButton = document.getElementById(
        "empty-state-add-project"
    );
    const closeButton = document.getElementById(
        "close-project-dialog"
    );
    const cancelButton = document.getElementById(
        "cancel-project"
    );
    const form = document.getElementById("project-form");
    const backdrop = document.getElementById(
        "project-dialog-backdrop"
    );
    const list = document.getElementById("projects-list");
    const materialsBackdrop = document.getElementById(
        "materials-dialog-backdrop"
    );
    const search = document.getElementById("projects-search");
    const statusFilter = document.getElementById(
        "projects-status-filter"
    );
    const sort = document.getElementById("projects-sort");

    addButton?.addEventListener("click", openAddProjectDialog);
    emptyStateButton?.addEventListener(
        "click",
        openAddProjectDialog
    );
    closeButton?.addEventListener(
        "click",
        closeProjectDialog
    );
    cancelButton?.addEventListener(
        "click",
        closeProjectDialog
    );
    form?.addEventListener("submit", handleProjectSubmit);
    backdrop?.addEventListener("click", handleBackdropClick);
    list?.addEventListener("click", handleProjectAction);
    document.getElementById(
        "close-materials-dialog"
    )?.addEventListener("click", closeMaterialsDialog);
    document.getElementById(
        "done-materials"
    )?.addEventListener("click", closeMaterialsDialog);
    document.getElementById(
        "material-requirement-form"
    )?.addEventListener("submit", handleMaterialSubmit);
    document.getElementById(
        "cancel-material-edit"
    )?.addEventListener("click", () => setMaterialFormMode());
    document.getElementById(
        "materials-requirements-list"
    )?.addEventListener("click", handleMaterialListAction);
    materialsBackdrop?.addEventListener("click", event => {
        if (event.target.id === "materials-dialog-backdrop") {
            closeMaterialsDialog();
        }
    });
    search?.addEventListener("input", renderProjects);
    statusFilter?.addEventListener("change", renderProjects);
    sort?.addEventListener("change", renderProjects);
    document.getElementById(
        "retry-projects"
    )?.addEventListener("click", () => void refreshProjects());
    document.addEventListener("keydown", handleEscapeKey);
    document.addEventListener("inventory:updated", event => {
        inventoryRevision += 1;
        inventoryItems = event.detail.items;
        void refreshProjectOperationalFacts();
    });

    setProjectsLoading();

    try {
        await projectMigration;
    } catch (error) {
        console.error(
            "Project migration did not complete before page load:",
            error
        );
    }

    const [, , factsLoaded] = await Promise.all([
        refreshProjects(),
        loadProjectInventory(),
        refreshProjectOperationalFacts()
    ]);

    if (!factsLoaded) {
        setProjectsMessage(
            "Project operational facts are unavailable or malformed.",
            true
        );
    }
}
