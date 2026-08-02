import {
    activateRestore,
    downloadPortableDataExport,
    downloadVerifiedBackup,
    prepareRestorePreflight,
    RESTORE_CONFIRMATION_PHRASE
} from "../utils/recoveryApi.js";


let recoveryPageInitialized = false;


function setStatus(element, message, state = "") {
    element.textContent = message;
    element.dataset.state = state;
}


function errorMessage(error, fallback) {
    if (typeof error?.message === "string" && error.message.trim()) {
        return error.message;
    }

    return fallback;
}


export function saveRecoveryAttachment(
    attachment,
    {
        documentRef = document,
        urlRef = URL
    } = {}
) {
    const objectUrl = urlRef.createObjectURL(attachment.blob);
    const anchor = documentRef.createElement("a");

    anchor.href = objectUrl;
    anchor.download = attachment.filename;
    anchor.hidden = true;
    documentRef.body.appendChild(anchor);

    try {
        anchor.click();
    } finally {
        anchor.remove();
        urlRef.revokeObjectURL(objectUrl);
    }
}


function renderPreflight(elements, preflight) {
    elements.preflightVersion.textContent = (
        preflight.manifest.applicationVersion
    );
    elements.preflightSchema.textContent = String(
        preflight.candidateDatabase.userVersion
    );
    elements.preflightExpiration.textContent = new Date(
        preflight.expiresAt
    ).toLocaleString();
    elements.preflightUpgrade.textContent = preflight.wasUpgraded
        ? "Yes — a compatible schema upgrade was prepared."
        : "No — the backup already matches the current schema.";
    elements.preflightCounts.textContent = Object.entries(
        preflight.recordCounts
    )
        .map(([table, count]) => `${table}: ${count}`)
        .join(" · ");
}


function requiredElements(documentRef) {
    const ids = [
        "recovery-download-backup",
        "recovery-backup-status",
        "recovery-download-export",
        "recovery-export-status",
        "recovery-restore-form",
        "recovery-backup-file",
        "recovery-prepare-status",
        "recovery-prepare-submit",
        "recovery-preflight-review",
        "recovery-preflight-version",
        "recovery-preflight-schema",
        "recovery-preflight-expiration",
        "recovery-preflight-upgrade",
        "recovery-preflight-counts",
        "recovery-confirmation-form",
        "recovery-confirmation",
        "recovery-activate-submit",
        "recovery-activation-status"
    ];
    const byId = Object.fromEntries(
        ids.map(id => [
            id.replace(/^recovery-/, "").replaceAll("-", "_"),
            documentRef.getElementById(id)
        ])
    );
    const missing = ids.filter(id => !documentRef.getElementById(id));

    if (missing.length > 0) {
        throw new Error(
            `Recovery page is missing required elements: ${missing.join(", ")}`
        );
    }

    return {
        backupButton: byId.download_backup,
        backupStatus: byId.backup_status,
        exportButton: byId.download_export,
        exportStatus: byId.export_status,
        restoreForm: byId.restore_form,
        fileInput: byId.backup_file,
        prepareStatus: byId.prepare_status,
        prepareButton: byId.prepare_submit,
        review: byId.preflight_review,
        preflightVersion: byId.preflight_version,
        preflightSchema: byId.preflight_schema,
        preflightExpiration: byId.preflight_expiration,
        preflightUpgrade: byId.preflight_upgrade,
        preflightCounts: byId.preflight_counts,
        confirmationForm: byId.confirmation_form,
        confirmationInput: byId.confirmation,
        activateButton: byId.activate_submit,
        activationStatus: byId.activation_status
    };
}


export function createRecoveryPageController({
    elements,
    windowRef = window,
    downloadAttachment = saveRecoveryAttachment,
    api = {
        activateRestore,
        downloadPortableDataExport,
        downloadVerifiedBackup,
        prepareRestorePreflight
    }
}) {
    let preflight = null;
    let activating = false;

    function updateActivationAvailability() {
        elements.activateButton.disabled = (
            activating ||
            !preflight ||
            elements.confirmationInput.value !== (
                RESTORE_CONFIRMATION_PHRASE
            )
        );
    }

    function clearPreflight() {
        preflight = null;
        elements.review.hidden = true;
        elements.confirmationInput.value = "";
        elements.confirmationInput.disabled = true;
        elements.preflightVersion.textContent = "—";
        elements.preflightSchema.textContent = "—";
        elements.preflightExpiration.textContent = "—";
        elements.preflightUpgrade.textContent = "—";
        elements.preflightCounts.textContent = "—";
        setStatus(elements.activationStatus, "", "");
        updateActivationAvailability();
    }

    async function runDownload({
        button,
        status,
        request,
        pendingMessage,
        successMessage,
        failureMessage
    }) {
        button.disabled = true;
        setStatus(status, pendingMessage, "working");

        try {
            const attachment = await request();
            downloadAttachment(attachment);
            setStatus(status, successMessage, "success");
        } catch (error) {
            setStatus(
                status,
                errorMessage(error, failureMessage),
                "error"
            );
        } finally {
            button.disabled = false;
        }
    }

    async function handlePreflight(event) {
        event.preventDefault();

        const file = elements.fileInput.files?.[0];

        if (!file) {
            setStatus(
                elements.prepareStatus,
                "Choose a Foreman backup ZIP before continuing.",
                "error"
            );
            return;
        }

        clearPreflight();
        elements.fileInput.disabled = true;
        elements.prepareButton.disabled = true;
        setStatus(
            elements.prepareStatus,
            "Inspecting and verifying the selected backup…",
            "working"
        );

        try {
            const result = await api.prepareRestorePreflight(file);
            preflight = result;
            renderPreflight(elements, result);
            elements.review.hidden = false;
            elements.confirmationInput.disabled = false;
            setStatus(
                elements.prepareStatus,
                "Backup verified. Review the prepared restore below.",
                "success"
            );
        } catch (error) {
            setStatus(
                elements.prepareStatus,
                errorMessage(
                    error,
                    "The selected backup could not be prepared."
                ),
                "error"
            );
        } finally {
            elements.fileInput.disabled = false;
            elements.prepareButton.disabled = false;
            updateActivationAvailability();
        }
    }

    async function handleActivation(event) {
        event.preventDefault();

        if (
            !preflight ||
            elements.confirmationInput.value !== (
                RESTORE_CONFIRMATION_PHRASE
            )
        ) {
            setStatus(
                elements.activationStatus,
                "Type the complete confirmation phrase exactly.",
                "error"
            );
            updateActivationAvailability();
            return;
        }

        activating = true;
        elements.confirmationInput.disabled = true;
        updateActivationAvailability();
        setStatus(
            elements.activationStatus,
            "Activating the verified restore…",
            "working"
        );

        try {
            await api.activateRestore(
                preflight.token,
                elements.confirmationInput.value
            );
            setStatus(
                elements.activationStatus,
                "Restore completed. Reloading The Foreman…",
                "success"
            );
            windowRef.location.reload();
        } catch (error) {
            activating = false;
            elements.confirmationInput.disabled = false;
            setStatus(
                elements.activationStatus,
                errorMessage(
                    error,
                    "The verified restore could not be activated."
                ),
                "error"
            );
            updateActivationAvailability();
        }
    }

    function bind() {
        clearPreflight();

        elements.backupButton.addEventListener("click", () => {
            void runDownload({
                button: elements.backupButton,
                status: elements.backupStatus,
                request: api.downloadVerifiedBackup,
                pendingMessage: "Creating a verified backup…",
                successMessage: "Verified backup downloaded.",
                failureMessage: "The verified backup could not be created."
            });
        });

        elements.exportButton.addEventListener("click", () => {
            void runDownload({
                button: elements.exportButton,
                status: elements.exportStatus,
                request: api.downloadPortableDataExport,
                pendingMessage: "Preparing portable data export…",
                successMessage: "Portable data export downloaded.",
                failureMessage: "The portable export could not be created."
            });
        });

        elements.fileInput.addEventListener("change", () => {
            clearPreflight();
            setStatus(
                elements.prepareStatus,
                elements.fileInput.files?.[0]
                    ? "Selected backup is ready for verification."
                    : "Choose a verified Foreman backup ZIP.",
                ""
            );
        });

        elements.restoreForm.addEventListener(
            "submit",
            event => void handlePreflight(event)
        );
        elements.confirmationInput.addEventListener(
            "input",
            updateActivationAvailability
        );
        elements.confirmationForm.addEventListener(
            "submit",
            event => void handleActivation(event)
        );
    }

    return {
        bind,
        clearPreflight,
        getPreparedRestore: () => preflight
    };
}


export function initializeRecoveryPage(options = {}) {
    if (recoveryPageInitialized) {
        return { status: "already-initialized" };
    }

    const documentRef = options.documentRef ?? document;
    const page = documentRef.querySelector(
        '[data-page="recovery"]'
    );

    if (!page) {
        return { status: "skipped" };
    }

    const controller = createRecoveryPageController({
        elements: requiredElements(documentRef),
        windowRef: options.windowRef ?? window,
        downloadAttachment: options.downloadAttachment,
        api: options.api
    });

    controller.bind();
    recoveryPageInitialized = true;

    return { status: "initialized", controller };
}
