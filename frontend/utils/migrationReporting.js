const RETENTION_STATEMENT =
    "Browser records were retained only as migration and recovery evidence.";


function count(value) {
    return Number.isInteger(value) && value >= 0 ? value : 0;
}


function attentionPhrase(value) {
    return value === 1
        ? "1 record needs attention"
        : `${value} records need attention`;
}


function buildMigrationReport(moduleName, values) {
    const sourceCount = count(values.sourceCount);
    const importedCount = count(values.importedCount);
    const confirmedCount = count(values.confirmedCount);
    const attentionCount = count(values.attentionCount);
    const retryableCount = count(values.retryableCount);
    const warningCount = count(values.warningCount);

    const hasMigrationEvidence =
        sourceCount > 0 ||
        importedCount > 0 ||
        confirmedCount > 0 ||
        attentionCount > 0 ||
        retryableCount > 0 ||
        warningCount > 0;

    if (!hasMigrationEvidence) {
        return null;
    }

    const successfulCount = importedCount + confirmedCount;
    const severity = attentionCount > 0 && successfulCount === 0
        ? "error"
        : attentionCount > 0 || warningCount > 0
            ? "warning"
            : "info";

    const headline = severity === "info"
        ? `${moduleName} browser migration complete`
        : severity === "warning"
            ? `${moduleName} browser migration needs review`
            : `${moduleName} browser migration requires attention`;

    const summaryParts = [
        `${importedCount} imported`,
        `${confirmedCount} already confirmed`,
        attentionPhrase(attentionCount)
    ];

    if (retryableCount > 0) {
        summaryParts.push(`${retryableCount} retryable`);
    }

    if (warningCount > 0) {
        summaryParts.push(
            warningCount === 1
                ? "1 warning"
                : `${warningCount} warnings`
        );
    }

    const summary = summaryParts.join(", ");

    return Object.freeze({
        moduleName,
        severity,
        headline,
        summary,
        retentionStatement: RETENTION_STATEMENT,
        sourceCount,
        importedCount,
        confirmedCount,
        attentionCount,
        retryableCount,
        warningCount,
        message: `${headline}. ${summary}. ${RETENTION_STATEMENT}`
    });
}


export function inventoryMigrationReport({
    browserRecordCount = 0,
    migration = null
} = {}) {
    const sourceCount = count(browserRecordCount);

    if (!migration) {
        return sourceCount > 0
            ? buildMigrationReport("Inventory", {
                sourceCount,
                attentionCount: sourceCount
            })
            : null;
    }

    return buildMigrationReport("Inventory", {
        sourceCount,
        importedCount: migration.migrated,
        confirmedCount: migration.alreadyMigrated,
        attentionCount: Math.max(
            count(migration.duplicates) + count(migration.malformed),
            Array.isArray(migration.errors)
                ? migration.errors.length
                : 0
        )
    });
}


export function taskMigrationReport({
    browserRecordCount = 0,
    migration = null
} = {}) {
    const sourceCount = count(browserRecordCount);

    if (!migration) {
        return sourceCount > 0
            ? buildMigrationReport("Task", {
                sourceCount,
                attentionCount: sourceCount
            })
            : null;
    }

    return buildMigrationReport("Task", {
        sourceCount,
        importedCount: migration.migrated,
        confirmedCount: migration.alreadyMigrated,
        attentionCount: Math.max(
            count(migration.skipped),
            Array.isArray(migration.errors)
                ? migration.errors.length
                : 0
        )
    });
}


export function projectMigrationReport(migration = null) {
    if (!migration) {
        return null;
    }

    return buildMigrationReport("Project", {
        sourceCount: migration.discovered,
        importedCount: migration.newlyMigrated,
        confirmedCount:
            count(migration.previouslyMigrated) +
            count(migration.skippedMigrated),
        attentionCount: migration.failed,
        retryableCount: migration.retryableFailures,
        warningCount: migration.warningCount
    });
}
