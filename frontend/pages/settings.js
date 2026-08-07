import {
    getModules
} from "../utils/moduleContext.js";
import {
    setModuleEnabled
} from "../utils/modulesApi.js";


let settingsInitialized = false;


function formatLocation(location) {
    return location.charAt(0).toUpperCase() + location.slice(1);
}


function setMessage(element, message, state = "") {
    if (!element) {
        return;
    }

    element.textContent = message;

    if (state) {
        element.dataset.state = state;
    } else {
        delete element.dataset.state;
    }
}


function createMetadataRow(label, value) {
    const row = document.createElement("div");
    row.className = "module-setting-metadata-row";

    const term = document.createElement("span");
    term.className = "module-setting-label";
    term.textContent = label;

    const detail = document.createElement("span");
    detail.textContent = value;

    row.append(term, detail);
    return row;
}


function renderModuleCard(
    module,
    messageElement,
    {
        updateModule = setModuleEnabled,
        reload = () => window.location.reload()
    } = {}
) {
    const card = document.createElement("article");
    card.className = "module-setting-card";
    card.dataset.moduleId = module.moduleId;

    const heading = document.createElement("div");
    heading.className = "module-setting-heading";

    const title = document.createElement("h4");
    title.textContent = module.name;

    const status = document.createElement("span");
    status.className = "module-setting-state";
    status.dataset.state = module.enabled
        ? "enabled"
        : "disabled";
    status.textContent = module.enabled
        ? "ENABLED"
        : "DISABLED";

    heading.append(title, status);

    const description = document.createElement("p");
    description.textContent = module.description || "";

    const metadata = document.createElement("div");
    metadata.className = "module-setting-metadata";

    const contributions = module.contributionLocations.length
        ? module.contributionLocations
            .map(formatLocation)
            .join(", ")
        : "None";

    const dependencies = module.dependencies.length
        ? module.dependencies.join(", ")
        : "None";

    metadata.append(
        createMetadataRow("Appears in", contributions),
        createMetadataRow("Dependencies", dependencies),
        createMetadataRow("When disabled", "Data retained")
    );

    const action = document.createElement("button");
    action.type = "button";
    action.className = "module-setting-action";
    action.dataset.moduleId = module.moduleId;
    action.textContent = module.enabled
        ? "Disable"
        : "Enable";

    action.addEventListener("click", async () => {
        const nextEnabled = !module.enabled;
        action.disabled = true;

        setMessage(
            messageElement,
            `${nextEnabled ? "Enabling" : "Disabling"} ${module.name}…`,
            "working"
        );

        try {
            const updated = await updateModule(
                module.moduleId,
                nextEnabled
            );

            if (
                !updated ||
                updated.moduleId !== module.moduleId ||
                updated.enabled !== nextEnabled
            ) {
                throw new TypeError(
                    "Backend returned an invalid module-state response."
                );
            }

            setMessage(
                messageElement,
                `${module.name} ${
                    nextEnabled ? "enabled" : "disabled"
                }. Reloading…`,
                "success"
            );

            reload();
        } catch (error) {
            action.disabled = false;

            setMessage(
                messageElement,
                error?.message || "Unable to update module state.",
                "error"
            );
        }
    });

    card.append(
        heading,
        description,
        metadata,
        action
    );

    return card;
}


export function renderModuleSettings(
    modules = getModules(),
    actions = {}
) {
    const container = document.getElementById(
        "module-settings-list"
    );
    const message = document.getElementById(
        "module-settings-message"
    );

    if (!container) {
        return;
    }

    container.replaceChildren();

    if (!modules.length) {
        setMessage(
            message,
            "No registered modules are available.",
            "error"
        );
        return;
    }

    modules.forEach(module => {
        container.appendChild(
            renderModuleCard(module, message, actions)
        );
    });

    setMessage(message, "");
}


export function initializeModuleSettings() {
    if (settingsInitialized) {
        return;
    }

    settingsInitialized = true;
    renderModuleSettings();
}
