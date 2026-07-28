export const PROJECT_READINESS = {
    ready: "READY TO START",
    needsMaterials: "NEEDS MATERIALS",
    noMaterials: "NO MATERIALS LISTED"
};

export function getProjectMaterials(project) {
    return Array.isArray(project?.materials)
        ? project.materials
        : [];
}

export function evaluateMaterialRequirement(
    requirement,
    inventoryItems
) {
    const inventoryItem = inventoryItems.find(
        item => item.id === requirement.inventoryItemId
    ) || null;
    const requiredQuantity = Number(
        requirement.requiredQuantity
    );
    const availableQuantity = inventoryItem &&
        Number.isFinite(Number(inventoryItem.quantity))
        ? Number(inventoryItem.quantity)
        : 0;
    const hasValidQuantity =
        Number.isFinite(requiredQuantity) &&
        requiredQuantity > 0;
    const isSufficient = Boolean(
        inventoryItem &&
        hasValidQuantity &&
        availableQuantity >= requiredQuantity
    );

    return {
        inventoryItemId: requirement.inventoryItemId,
        inventoryItem,
        availableQuantity,
        requiredQuantity,
        shortageQuantity: hasValidQuantity
            ? Math.max(0, requiredQuantity - availableQuantity)
            : 0,
        isSufficient,
        isMissingReference: !inventoryItem,
        note: requirement.note || ""
    };
}

export function evaluateProjectReadiness(project, inventoryItems) {
    const materials = getProjectMaterials(project);

    if (materials.length === 0) {
        return {
            status: PROJECT_READINESS.noMaterials,
            requirements: []
        };
    }

    const requirements = materials.map(requirement =>
        evaluateMaterialRequirement(requirement, inventoryItems)
    );
    const isReady = requirements.every(
        requirement => requirement.isSufficient
    );

    return {
        status: isReady
            ? PROJECT_READINESS.ready
            : PROJECT_READINESS.needsMaterials,
        requirements
    };
}
