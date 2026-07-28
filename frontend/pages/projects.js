import {
    getProjects,
    saveProjects
} from "../utils/projectStorage.js";

let projects = [];

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

function openProjectDialog() {
    const backdrop = document.getElementById(
        "project-dialog-backdrop"
    );
    const form = document.getElementById("project-form");

    if (!backdrop) {
        return;
    }

    form?.reset();
    backdrop.hidden = false;
    document.body.classList.add("dialog-open");

    window.setTimeout(() => {
        document.getElementById("project-name")?.focus();
    }, 0);
}

function closeProjectDialog() {
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

function refreshProjects() {
    projects = getProjects();
    renderProjects();
}

function handleProjectSubmit(event) {
    event.preventDefault();

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

    if (!Number.isFinite(progress) || progress < 0 || progress > 100) {
        if (errorElement) {
            errorElement.textContent =
                "Progress must be between 0 and 100.";
        }
        return;
    }

    const project = {
        id: crypto.randomUUID(),
        name,
        type: formData.get("type"),
        status: formData.get("status"),
        priority: formData.get("priority"),
        progress,
        startDate: formData.get("startDate"),
        targetDate: formData.get("targetDate"),
        estimatedCost: Number(
            formData.get("estimatedCost") || 0
        ),
        description: formData.get("description").trim(),
        notes: formData.get("notes").trim(),
        createdAt: new Date().toISOString()
    };

    const updatedProjects = [...getProjects(), project];

    if (!saveProjects(updatedProjects)) {
        if (errorElement) {
            errorElement.textContent =
                "The project could not be saved in this browser.";
        }
        return;
    }

    projects = updatedProjects;
    closeProjectDialog();
    renderProjects();
    setProjectsMessage("Project created.");
}

function handleBackdropClick(event) {
    if (event.target.id === "project-dialog-backdrop") {
        closeProjectDialog();
    }
}

function handleEscapeKey(event) {
    if (event.key === "Escape") {
        closeProjectDialog();
    }
}

export function initializeProjectsPage() {
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
    const search = document.getElementById("projects-search");
    const statusFilter = document.getElementById(
        "projects-status-filter"
    );
    const sort = document.getElementById("projects-sort");

    addButton?.addEventListener("click", openProjectDialog);
    emptyStateButton?.addEventListener(
        "click",
        openProjectDialog
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
    search?.addEventListener("input", renderProjects);
    statusFilter?.addEventListener("change", renderProjects);
    sort?.addEventListener("change", renderProjects);
    document.addEventListener("keydown", handleEscapeKey);

    refreshProjects();
}
