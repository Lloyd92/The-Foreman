export function validateProjectRecord(project) {
    if (
        !project ||
        typeof project !== "object" ||
        typeof project.id !== "string" ||
        !project.id ||
        typeof project.name !== "string" ||
        !Array.isArray(project.materials)
    ) {
        throw new Error("Backend returned a malformed Project record.");
    }

    return project;
}


export async function loadBackendProjects(loadProjects) {
    const loaded = await loadProjects();

    if (!Array.isArray(loaded)) {
        throw new Error("Backend returned a malformed Project list.");
    }

    return loaded.map(validateProjectRecord);
}


export function mergePersistedProject(projects, persistedProject) {
    const project = validateProjectRecord(persistedProject);
    const existing = projects.some(item => item.id === project.id);

    return existing
        ? projects.map(item => item.id === project.id ? project : item)
        : [...projects, project];
}


export function removePersistedProject(projects, projectId) {
    return projects.filter(project => project.id !== projectId);
}
