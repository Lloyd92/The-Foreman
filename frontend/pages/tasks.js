import {
    getBrowserTasks
} from "../utils/storage.js";

import {
    completeBackendTask,
    createBackendTask,
    deleteBackendTask,
    getBackendTasks,
    migrateBrowserTasks,
    reopenBackendTask
} from "../utils/tasksApi.js";
import {
    migrateTasksAfterProjects
} from "../utils/migrationOrchestrator.js";
import {
    taskMigrationReport
} from "../utils/migrationReporting.js";

let currentTasks = [];
let backendAvailable = false;
let tasksInitialized = false;

export function buildTaskCreatePayload({
    title,
    priority,
    dueDate
}) {
    return {
        title,
        priority,
        dueDate: dueDate || null
    };
}

export function formatTaskDueDate(dueDate) {
    return dueDate ? `Due ${dueDate}` : "No due date";
}

function notifyTasksUpdated() {
    document.dispatchEvent(
        new CustomEvent("tasks:updated", {
            detail: { tasks: [...currentTasks] }
        })
    );
}

function priorityRank(priority) {
    const ranks = {
        high: 1,
        medium: 2,
        low: 3
    };

    return ranks[priority] || 4;
}

function setTaskMessage(message, isError = false) {
    const messageElement = document.getElementById(
        "task-migration-status"
    );

    if (!messageElement) {
        return;
    }

    messageElement.textContent = message;
    messageElement.classList.toggle("error", isError);
}

function renderTasks(tasks = currentTasks) {
    const taskList = document.getElementById("task-list");
    const taskCount = document.getElementById("task-count");

    if (!taskList || !taskCount) {
        return;
    }

    const sortedTasks = [...tasks].sort((a, b) => {
        if (a.completed !== b.completed) {
            return Number(a.completed) - Number(b.completed);
        }

        return priorityRank(a.priority) - priorityRank(b.priority);
    });

    taskList.innerHTML = "";

    if (sortedTasks.length === 0) {
        taskList.innerHTML = `
            <p class="empty-message">
                No tasks have been added yet.
            </p>
        `;
    } else {
        sortedTasks.forEach(task => {
            const row = document.createElement("div");

            row.className =
                `task-row ${task.completed ? "completed" : ""}`;

            row.innerHTML = `
                <label class="task-main">
                    <input
                        type="checkbox"
                        data-action="toggle"
                        data-id="${task.id}"
                        ${task.completed ? "checked" : ""}
                    >

                    <span class="task-title"></span>
                </label>

                <div class="task-actions">
                    <span class="task-due-date"></span>

                    <span class="priority priority-${task.priority}">
                        ${task.priority.toUpperCase()}
                    </span>

                    <button
                        class="delete-task"
                        data-action="delete"
                        data-id="${task.id}"
                        type="button"
                    >
                        Delete
                    </button>
                </div>
            `;

            row.querySelector(".task-title").textContent = task.title;
            row.querySelector(".task-due-date").textContent =
                formatTaskDueDate(task.dueDate);
            taskList.appendChild(row);
        });
    }

    const openCount = tasks.filter(task => !task.completed).length;
    taskCount.textContent = `${openCount} OPEN`;
}

async function refreshBackendTasks() {
    currentTasks = await getBackendTasks();
    renderTasks();
    notifyTasksUpdated();
}

export async function migrateLegacyTasks(projectMigration) {
    const browserTasks = getBrowserTasks();

    if (browserTasks.length === 0) {
        return {
            browserRecordCount: 0,
            migration: null
        };
    }

    const migration = await migrateTasksAfterProjects(
        projectMigration,
        browserTasks,
        migrateBrowserTasks
    );

    return {
        browserRecordCount: browserTasks.length,
        migration
    };
}

async function initializeTaskPersistence(taskMigration) {
    try {
        const migrationResult = await taskMigration;
        const report = taskMigrationReport(migrationResult);

        if (report) {
            setTaskMessage(
                report.message,
                report.severity === "error"
            );

            if (report.attentionCount > 0) {
                console.warn(
                    "Task browser migration completed with records " +
                    "requiring attention."
                );
            }
        }

        backendAvailable = true;
        await refreshBackendTasks();
    } catch (error) {
        backendAvailable = false;
        setTaskMessage(
            "HardHead Tasks are unavailable. Browser-local tasks were " +
            "not loaded as operational data.",
            true
        );
        console.error("Unable to initialize task persistence:", error);
    }
}

async function addTask(event) {
    event.preventDefault();

    const titleInput = document.getElementById("task-title");
    const priorityInput = document.getElementById("task-priority");
    const dueDateInput = document.getElementById("task-due-date");

    if (!titleInput || !priorityInput || !dueDateInput) {
        return;
    }

    const title = titleInput.value.trim();

    if (!title) {
        titleInput.focus();
        return;
    }

    try {
        if (!backendAvailable) {
            throw new Error("HardHead Tasks are unavailable.");
        }

        await createBackendTask(
            buildTaskCreatePayload({
                title,
                priority: priorityInput.value,
                dueDate: dueDateInput.value
            })
        );
        await refreshBackendTasks();

        titleInput.value = "";
        priorityInput.value = "medium";
        dueDateInput.value = "";
        titleInput.focus();
    } catch (error) {
        setTaskMessage(error.message, true);
    }
}

async function handleTaskAction(event) {
    const action = event.target.dataset.action;
    const taskId = event.target.dataset.id;

    if (!action || !taskId) {
        return;
    }

    const task = currentTasks.find(item => item.id === taskId);

    if (!task) {
        return;
    }

    try {
        if (!backendAvailable) {
            throw new Error("HardHead Tasks are unavailable.");
        }

        if (action === "toggle") {
            if (task.completed) {
                await reopenBackendTask(taskId);
            } else {
                await completeBackendTask(taskId);
            }
        }

        if (action === "delete") {
            await deleteBackendTask(taskId);
        }

        await refreshBackendTasks();
    } catch (error) {
        renderTasks();
        setTaskMessage(error.message, true);
    }
}

export function initializeTasksPage(
    taskMigration = Promise.resolve({
        browserRecordCount: 0,
        migration: null
    })
) {
    if (tasksInitialized) {
        return;
    }
    tasksInitialized = true;

    const taskForm = document.getElementById("task-form");
    const taskList = document.getElementById("task-list");

    if (!taskForm || !taskList) {
        console.warn("Task page elements were not found.");
        return;
    }

    taskForm.addEventListener("submit", addTask);
    taskList.addEventListener("click", handleTaskAction);

    return initializeTaskPersistence(taskMigration);
}
