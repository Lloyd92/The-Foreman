import { migrateLegacyProjects } from "./projectMigration.js";


export async function migrateProjectsAfterInventory(
    inventoryMigration,
    migrateProjects = migrateLegacyProjects
) {
    try {
        await inventoryMigration;
    } catch (error) {
        console.error(
            "Inventory migration did not complete normally:",
            error
        );
    }

    try {
        return await migrateProjects();
    } catch (error) {
        console.error("Project migration failed unexpectedly:", error);
        return {
            status: "complete_failure",
            discovered: 0,
            attempted: 0,
            newlyMigrated: 0,
            previouslyMigrated: 0,
            skipped: 0,
            failed: 1,
            retryableFailures: 1,
            warningCount: 0,
            outcomes: [],
            projectIdMappings: {}
        };
    }
}


export function translateTaskProjectReferences(
    tasks,
    projectMigrationResult
) {
    const mappings = projectMigrationResult?.projectIdMappings || {};

    return tasks.map(task => {
        const sourceProjectId = task.projectId ?? task.project_id;
        const backendProjectId = mappings[sourceProjectId];

        if (!sourceProjectId || !backendProjectId) {
            return task;
        }

        if ("project_id" in task && !("projectId" in task)) {
            return {
                ...task,
                project_id: backendProjectId
            };
        }

        return {
            ...task,
            projectId: backendProjectId
        };
    });
}


export async function migrateTasksAfterProjects(
    projectMigration,
    tasks,
    migrateTasks
) {
    let projectResult;

    try {
        projectResult = await projectMigration;
    } catch (error) {
        console.error(
            "Project migration prerequisite failed:",
            error
        );
        projectResult = { projectIdMappings: {} };
    }

    return migrateTasks(
        translateTaskProjectReferences(tasks, projectResult)
    );
}
