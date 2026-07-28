const PROJECT_STORAGE_KEY = "foreman-projects";

export function getProjects() {
    try {
        const storedProjects = localStorage.getItem(
            PROJECT_STORAGE_KEY
        );
        const parsedProjects = storedProjects
            ? JSON.parse(storedProjects)
            : [];

        if (!Array.isArray(parsedProjects)) {
            console.error(
                "Browser-local projects are malformed and were retained."
            );
            return [];
        }

        return parsedProjects;
    } catch (error) {
        console.error("Unable to read projects:", error);
        return [];
    }
}

export function saveProjects(projects) {
    try {
        localStorage.setItem(
            PROJECT_STORAGE_KEY,
            JSON.stringify(projects)
        );
        return true;
    } catch (error) {
        console.error("Unable to save projects:", error);
        return false;
    }
}

export function updateProjectRecord(projectId, changes) {
    const projects = getProjects();
    const project = projects.find(item => item.id === projectId);

    if (!project || project.status === "archived") {
        return false;
    }

    const updatedProjects = projects.map(item =>
        item.id === projectId
            ? {
                ...item,
                ...changes,
                id: item.id,
                createdAt: item.createdAt,
                updatedAt: new Date().toISOString()
            }
            : item
    );

    return saveProjects(updatedProjects);
}

export function deleteProjectRecord(projectId) {
    const projects = getProjects();
    const project = projects.find(item => item.id === projectId);

    if (!project || project.status === "archived") {
        return false;
    }

    return saveProjects(
        projects.filter(item => item.id !== projectId)
    );
}
