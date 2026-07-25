import { getTasks, saveTasks } from "../utils/storage.js";

function createTask(title, priority) {
    return {
        id: crypto.randomUUID(),
        title,
        priority,
        completed: false,
        createdAt: new Date().toISOString()
    };
}

function priorityRank(priority) {
    const ranks = {
        high: 1,
        medium: 2,
        low: 3
    };

    return ranks[priority] || 4;
}

function renderTasks() {
    const taskList = document.getElementById("task-list");
    const taskCount = document.getElementById("task-count");

    if (!taskList || !taskCount) {
        return;
    }

    const tasks = getTasks();

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
            taskList.appendChild(row);
        });
    }

    const openCount = tasks.filter(task => !task.completed).length;
    taskCount.textContent = `${openCount} OPEN`;
}

function addTask(event) {
    event.preventDefault();

    const titleInput = document.getElementById("task-title");
    const priorityInput = document.getElementById("task-priority");

    if (!titleInput || !priorityInput) {
        return;
    }

    const title = titleInput.value.trim();

    if (!title) {
        titleInput.focus();
        return;
    }

    const tasks = getTasks();

    tasks.push(createTask(title, priorityInput.value));
    saveTasks(tasks);

    titleInput.value = "";
    priorityInput.value = "medium";

    renderTasks();
    titleInput.focus();
}

function handleTaskAction(event) {
    const action = event.target.dataset.action;
    const taskId = event.target.dataset.id;

    if (!action || !taskId) {
        return;
    }

    let tasks = getTasks();

    if (action === "toggle") {
        tasks = tasks.map(task =>
            task.id === taskId
                ? { ...task, completed: !task.completed }
                : task
        );
    }

    if (action === "delete") {
        tasks = tasks.filter(task => task.id !== taskId);
    }

    saveTasks(tasks);
    renderTasks();
}

export function initializeTasksPage() {
    const taskForm = document.getElementById("task-form");
    const taskList = document.getElementById("task-list");

    if (!taskForm || !taskList) {
        console.warn("Task page elements were not found.");
        return;
    }

    taskForm.addEventListener("submit", addTask);
    taskList.addEventListener("click", handleTaskAction);

    renderTasks();
}