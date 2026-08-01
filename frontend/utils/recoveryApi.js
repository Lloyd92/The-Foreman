import {
    apiRequest,
    apiResponse
} from "./api.js";


export const RESTORE_CONFIRMATION_PHRASE = "RESTORE THE FOREMAN";


export class RecoveryApiContractError extends Error {
    constructor(message) {
        super(message);
        this.name = "RecoveryApiContractError";
        this.code = "RECOVERY_API_CONTRACT_INVALID";
    }
}


function isObject(value) {
    return (
        value !== null &&
        typeof value === "object" &&
        !Array.isArray(value)
    );
}


function requireNonemptyString(value, field) {
    if (typeof value !== "string" || !value.trim()) {
        throw new RecoveryApiContractError(
            `${field} must be a nonempty string.`
        );
    }

    return value;
}


function validateRecordCounts(value, field = "recordCounts") {
    if (!isObject(value) || Object.keys(value).length === 0) {
        throw new RecoveryApiContractError(
            `${field} must be a nonempty object.`
        );
    }

    for (const [table, count] of Object.entries(value)) {
        requireNonemptyString(table, `${field} table name`);

        if (!Number.isSafeInteger(count) || count < 0) {
            throw new RecoveryApiContractError(
                `${field}.${table} must be a nonnegative integer.`
            );
        }
    }

    return value;
}


function requireValidExpiration(value) {
    requireNonemptyString(value, "expiresAt");

    if (Number.isNaN(Date.parse(value))) {
        throw new RecoveryApiContractError(
            "expiresAt must be a valid timestamp."
        );
    }

    return value;
}


function validatePreflightSummary(value) {
    if (!isObject(value)) {
        throw new RecoveryApiContractError(
            "Restore preflight response must be an object."
        );
    }

    requireNonemptyString(value.token, "token");
    requireValidExpiration(value.expiresAt);

    if (value.confirmationPhrase !== RESTORE_CONFIRMATION_PHRASE) {
        throw new RecoveryApiContractError(
            "Restore confirmation phrase is invalid."
        );
    }

    if (!isObject(value.manifest)) {
        throw new RecoveryApiContractError(
            "Restore manifest must be an object."
        );
    }

    if (!isObject(value.candidateDatabase)) {
        throw new RecoveryApiContractError(
            "Candidate database summary must be an object."
        );
    }

    validateRecordCounts(value.recordCounts);

    if (typeof value.wasUpgraded !== "boolean") {
        throw new RecoveryApiContractError(
            "wasUpgraded must be boolean."
        );
    }

    const tables = value.candidateDatabase.tables;
    const recordCountKeys = Object.keys(value.recordCounts);

    if (
        !Array.isArray(tables) ||
        tables.length !== recordCountKeys.length ||
        !tables.every(
            (table, index) => table === recordCountKeys[index]
        )
    ) {
        throw new RecoveryApiContractError(
            "Candidate tables must match recordCounts exactly."
        );
    }

    return value;
}


function validateActivationResponse(value) {
    if (!isObject(value) || value.status !== "restored") {
        throw new RecoveryApiContractError(
            "Restore activation status is invalid."
        );
    }

    validateRecordCounts(value.recordCounts);

    if (
        !Number.isSafeInteger(value.operationalFactCount) ||
        value.operationalFactCount < 0
    ) {
        throw new RecoveryApiContractError(
            "operationalFactCount must be a nonnegative integer."
        );
    }

    if (
        value.safetyBackupRetained !== true ||
        value.reloadRequired !== true
    ) {
        throw new RecoveryApiContractError(
            "Restore activation safety flags are invalid."
        );
    }

    return value;
}


function safeAttachmentFilename(value, fallback) {
    if (typeof value !== "string") {
        return fallback;
    }

    const leaf = value
        .replace(/[\u0000-\u001f\u007f]/g, "")
        .split(/[\\/]/)
        .pop()
        .trim();

    if (!leaf || leaf === "." || leaf === "..") {
        return fallback;
    }

    return leaf.slice(0, 255);
}


function contentDispositionFilename(header, fallback) {
    if (typeof header !== "string") {
        return fallback;
    }

    const encoded = header.match(
        /filename\*\s*=\s*UTF-8''([^;]+)/i
    );

    if (encoded) {
        try {
            return safeAttachmentFilename(
                decodeURIComponent(encoded[1].trim()),
                fallback
            );
        } catch {
            return fallback;
        }
    }

    const quoted = header.match(/filename\s*=\s*"([^"]*)"/i);

    if (quoted) {
        return safeAttachmentFilename(quoted[1], fallback);
    }

    const unquoted = header.match(/filename\s*=\s*([^;]+)/i);

    return safeAttachmentFilename(unquoted?.[1], fallback);
}


async function downloadAttachment(
    path,
    {
        method = "GET",
        accept,
        expectedContentType,
        fallbackFilename
    }
) {
    const response = await apiResponse(path, {
        method,
        headers: { Accept: accept }
    });
    const contentType = (
        response.headers.get("content-type") || ""
    ).split(";", 1)[0].trim().toLowerCase();

    if (contentType !== expectedContentType) {
        throw new RecoveryApiContractError(
            `Unexpected attachment content type: ${contentType || "missing"}.`
        );
    }

    const blob = await response.blob();

    if (blob.size === 0) {
        throw new RecoveryApiContractError(
            "Downloaded attachment is empty."
        );
    }

    return {
        blob,
        filename: contentDispositionFilename(
            response.headers.get("content-disposition"),
            fallbackFilename
        )
    };
}


export function downloadVerifiedBackup() {
    return downloadAttachment(
        "/api/recovery/backups",
        {
            method: "POST",
            accept: "application/zip",
            expectedContentType: "application/zip",
            fallbackFilename: "foreman-backup.zip"
        }
    );
}


export function downloadPortableDataExport() {
    return downloadAttachment(
        "/api/exports/portable-data",
        {
            accept: "application/json",
            expectedContentType: "application/json",
            fallbackFilename: "foreman-data-export.json"
        }
    );
}


export async function prepareRestorePreflight(file) {
    if (!(file instanceof Blob) || file.size === 0) {
        throw new TypeError(
            "Restore preflight requires a nonempty backup file."
        );
    }

    const response = await apiRequest(
        "/api/recovery/restores/preflight",
        {
            method: "POST",
            headers: {
                Accept: "application/json",
                "Content-Type": "application/zip"
            },
            body: file
        }
    );

    return validatePreflightSummary(response);
}


export async function activateRestore(
    token,
    confirmationPhrase
) {
    requireNonemptyString(token, "token");
    requireNonemptyString(
        confirmationPhrase,
        "confirmationPhrase"
    );

    const response = await apiRequest(
        "/api/recovery/restores/activate",
        {
            method: "POST",
            headers: { Accept: "application/json" },
            body: JSON.stringify({
                token,
                confirmationPhrase
            })
        }
    );

    return validateActivationResponse(response);
}
