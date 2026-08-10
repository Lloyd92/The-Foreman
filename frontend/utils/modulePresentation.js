import { isModuleEnabled } from "./moduleContext.js";


export const MODULE_ROUTE_OWNERS = Object.freeze({
    tasks: "work",
    projects: "work",
    tools: "tools",
    inventory: "inventory",
    care: "care"
});


export function isModuleRouteAvailable(route) {
    const owner = MODULE_ROUTE_OWNERS[route];

    if (!owner) {
        return true;
    }

    return isModuleEnabled(owner);
}


export function applyModuleContributions(root = document) {
    const contributions = root.querySelectorAll(
        "[data-module-contribution]"
    );

    contributions.forEach(element => {
        const moduleId = element.dataset.moduleContribution;
        element.hidden = !isModuleEnabled(moduleId);
    });
}
