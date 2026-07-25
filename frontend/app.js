const STORAGE_KEY = "foreman-tasks";

function getTasks() {
    try {
        return JSON.parse(localStorage.getItem(STORAGE_KEY)) || [];
    } catch {
        return [];
    }
}

function saveTasks(tasks) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(tasks));
}

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
    return {
        high: 1,
        medium: 2,
        low: 3
    }[priority] || 4;
}

function renderTasks() {
    const taskList = document.getElementById("task-list");
    const taskCount = document.getElementById("task-count");
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
            row.className = `task-row ${task.completed ? "completed" : ""}`;

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
                        aria-label="Delete task"
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

function updateGreeting() {
    const hour = new Date().getHours();
    let greeting = "Welcome back";

    if (hour < 12) {
        greeting = "Good morning";
    } else if (hour < 18) {
        greeting = "Good afternoon";
    } else {
        greeting = "Good evening";
    }

    document.getElementById("greeting").textContent =
        `${greeting}, Tyler.`;

    document.getElementById("current-date").textContent =
        new Intl.DateTimeFormat("en-US", {
            weekday: "long",
            month: "long",
            day: "numeric",
            year: "numeric"
        }).format(new Date());
}

async function loadSystemStatus() {
    const statusDot = document.getElementById("status-dot");
    const systemStatus = document.getElementById("system-status");
    const appStatus = document.getElementById("app-status");
    const apiStatus = document.getElementById("api-status");
    const version = document.getElementById("version");
    const footerVersion = document.getElementById("footer-version");

    try {
        const response = await fetch("/api/status");

        if (!response.ok) {
            throw new Error(`Backend returned ${response.status}`);
        }

        const data = await response.json();

        statusDot.classList.add("online");
        systemStatus.textContent = "System online";
        appStatus.textContent = data.status.toUpperCase();
        apiStatus.textContent = "ONLINE";
        version.textContent = data.version;
        footerVersion.textContent = data.version;
    } catch (error) {
        console.error(error);

        systemStatus.textContent = "System offline";
        appStatus.textContent = "OFFLINE";
        apiStatus.textContent = "OFFLINE";
    }
}

document
    .getElementById("task-form")
    .addEventListener("submit", addTask);

document
    .getElementById("task-list")
    .addEventListener("click", handleTaskAction);

updateGreeting();
renderTasks();
loadSystemStatus();