import { getWork } from "../utils/workApi.js";


let workInitialized = false;


function formatLabel(value) {
    return value
        .split("-")
        .map(part => (
            part.charAt(0).toUpperCase() + part.slice(1)
        ))
        .join(" ");
}


function setWorkMessage(message, isError = false) {
    const element = document.getElementById("work-page-message");

    if (!element) {
        return;
    }

    element.textContent = message;
    element.classList.toggle("error", isError);
}


function itemDateText(item) {
    if (item.recordType === "task") {
        return item.dueDate
            ? `Due ${item.dueDate}`
            : "No due date";
    }

    if (item.targetDate) {
        return `Target ${item.targetDate}`;
    }

    if (item.startDate) {
        return `Starts ${item.startDate}`;
    }

    return "No project date";
}


function renderWork(work) {
    const items = document.getElementById("work-overview-items");
    const dependencies = document.getElementById(
        "work-overview-dependencies"
    );
    const empty = document.getElementById("work-overview-empty");

    if (!items || !dependencies || !empty) {
        return;
    }

    const taskItems = work.items.filter(
        item => item.recordType === "task"
    );
    const projectItems = work.items.filter(
        item => item.recordType === "project"
    );
    const openTasks = taskItems.filter(
        item => item.lifecycleState === "open"
    );

    document.getElementById("work-total-count").textContent =
        work.items.length;
    document.getElementById("work-open-task-count").textContent =
        openTasks.length;
    document.getElementById("work-project-count").textContent =
        projectItems.length;
    document.getElementById("work-dependency-count").textContent =
        work.dependencies.length;

    const itemIndex = new Map(
        work.items.map(item => [
            `${item.recordType}:${item.id}`,
            item
        ])
    );

    items.innerHTML = "";
    empty.hidden = work.items.length > 0;

    work.items.forEach(item => {
        const card = document.createElement("article");

        card.className = "work-overview-item";
        card.innerHTML = `
            <div class="work-item-heading">
                <div>
                    <p class="work-item-type"></p>
                    <h3 class="work-item-title"></h3>
                </div>
                <span class="work-item-state"></span>
            </div>

            <dl class="work-item-details">
                <div>
                    <dt>Priority</dt>
                    <dd class="work-item-priority"></dd>
                </div>
                <div>
                    <dt>Progress</dt>
                    <dd class="work-item-progress"></dd>
                </div>
                <div>
                    <dt>Date</dt>
                    <dd class="work-item-date"></dd>
                </div>
                <div>
                    <dt>Relationship</dt>
                    <dd class="work-item-relationship"></dd>
                </div>
            </dl>
        `;

        card.querySelector(".work-item-type").textContent =
            formatLabel(item.recordType);
        card.querySelector(".work-item-title").textContent =
            item.title;
        card.querySelector(".work-item-state").textContent =
            formatLabel(item.lifecycleState);
        card.querySelector(".work-item-priority").textContent =
            formatLabel(item.priority);
        card.querySelector(".work-item-progress").textContent =
            `${item.progress}%`;
        card.querySelector(".work-item-date").textContent =
            itemDateText(item);

        let relationship = "Independent record";

        if (item.recordType === "task" && item.projectId) {
            const project = itemIndex.get(
                `project:${item.projectId}`
            );

            relationship = project
                ? `Project: ${project.title}`
                : "Linked Project unavailable";
        }

        card.querySelector(
            ".work-item-relationship"
        ).textContent = relationship;

        items.appendChild(card);
    });

    dependencies.innerHTML = "";

    if (work.dependencies.length === 0) {
        dependencies.innerHTML = `
            <p class="empty-message">
                No Work dependencies are recorded.
            </p>
        `;
        return;
    }

    work.dependencies.forEach(dependency => {
        const row = document.createElement("div");
        const dependent = itemIndex.get(
            `${dependency.dependentType}:${dependency.dependentId}`
        );
        const prerequisite = itemIndex.get(
            `${dependency.prerequisiteType}:${dependency.prerequisiteId}`
        );

        row.className = "work-dependency-row";
        row.textContent = (
            `${dependent?.title ?? dependency.dependentId} requires ` +
            `${prerequisite?.title ?? dependency.prerequisiteId}`
        );
        dependencies.appendChild(row);
    });
}


async function refreshWork() {
    const retry = document.getElementById("retry-work");

    if (retry) {
        retry.hidden = true;
    }

    setWorkMessage("Loading Work overview…");

    try {
        const work = await getWork();

        renderWork(work);
        setWorkMessage("");
        return true;
    } catch (error) {
        setWorkMessage(
            "The Work overview is unavailable. Retry when the " +
            "backend connection is restored.",
            true
        );

        if (retry) {
            retry.hidden = false;
        }

        console.error("Unable to load normalized Work:", error);
        return false;
    }
}


export function initializeWorkPage() {
    if (workInitialized) {
        return;
    }

    workInitialized = true;

    document.getElementById("retry-work")?.addEventListener(
        "click",
        () => void refreshWork()
    );
    document.addEventListener(
        "tasks:updated",
        () => void refreshWork()
    );
    document.addEventListener(
        "projects:updated",
        () => void refreshWork()
    );

    return refreshWork();
}
