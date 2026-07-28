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
