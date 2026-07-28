import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const frontendDirectory = path.resolve(
    path.dirname(fileURLToPath(import.meta.url)),
    ".."
);

const manifestPath = path.join(
    frontendDirectory,
    "manifest.webmanifest"
);

const expectedManifest = {
    id: "/",
    name: "The Foreman — HardHead Works",
    short_name: "Foreman",
    description: "The local workshop command center for HardHead Works.",
    start_url: "/#dashboard",
    scope: "/",
    display: "standalone",
    orientation: "any",
    theme_color: "#1d2024",
    background_color: "#15171a",
    lang: "en-US",
    prefer_related_applications: false
};

const expectedIcons = [
    {
        src: "/assets/icons/icon-192.png",
        sizes: "192x192",
        type: "image/png",
        purpose: "any"
    },
    {
        src: "/assets/icons/icon-512.png",
        sizes: "512x512",
        type: "image/png",
        purpose: "any"
    },
    {
        src: "/assets/icons/icon-maskable-192.png",
        sizes: "192x192",
        type: "image/png",
        purpose: "maskable"
    },
    {
        src: "/assets/icons/icon-maskable-512.png",
        sizes: "512x512",
        type: "image/png",
        purpose: "maskable"
    }
];

async function readManifest() {
    return JSON.parse(await readFile(manifestPath, "utf8"));
}

async function readPngDimensions(filePath) {
    const contents = await readFile(filePath);
    const signature = Buffer.from([
        0x89, 0x50, 0x4e, 0x47,
        0x0d, 0x0a, 0x1a, 0x0a
    ]);

    assert.deepEqual(
        contents.subarray(0, signature.length),
        signature,
        `${filePath} must have a valid PNG signature`
    );
    assert.equal(
        contents.subarray(12, 16).toString("ascii"),
        "IHDR",
        `${filePath} must begin with a PNG IHDR chunk`
    );

    return {
        width: contents.readUInt32BE(16),
        height: contents.readUInt32BE(20)
    };
}

test("manifest contains the approved Foreman PWA identity", async () => {
    const manifest = await readManifest();

    Object.entries(expectedManifest).forEach(([key, value]) => {
        assert.equal(manifest[key], value);
    });
    assert.equal("shortcuts" in manifest, false);
    assert.equal("screenshots" in manifest, false);
});

test("manifest declares the required any and maskable icons", async () => {
    const manifest = await readManifest();

    assert.deepEqual(manifest.icons, expectedIcons);
});

test("every manifest PNG exists with the declared dimensions", async () => {
    const manifest = await readManifest();

    for (const icon of manifest.icons) {
        const [width, height] = icon.sizes.split("x").map(Number);
        const iconPath = path.join(
            frontendDirectory,
            icon.src.replace(/^\//, "")
        );

        assert.deepEqual(
            await readPngDimensions(iconPath),
            { width, height }
        );
    }
});

test("Apple touch icon is a valid 180 by 180 PNG", async () => {
    const iconPath = path.join(
        frontendDirectory,
        "assets/icons/apple-touch-icon.png"
    );

    assert.deepEqual(
        await readPngDimensions(iconPath),
        { width: 180, height: 180 }
    );
});

test("favicon contains 16, 32, and 48 pixel icon entries", async () => {
    const faviconPath = path.join(
        frontendDirectory,
        "assets/icons/favicon.ico"
    );
    const contents = await readFile(faviconPath);

    assert.equal(contents.readUInt16LE(0), 0);
    assert.equal(contents.readUInt16LE(2), 1);

    const count = contents.readUInt16LE(4);
    const sizes = [];

    for (let index = 0; index < count; index += 1) {
        const offset = 6 + index * 16;
        const width = contents[offset] || 256;
        const height = contents[offset + 1] || 256;

        assert.equal(width, height);
        sizes.push(width);
    }

    assert.deepEqual(sizes.sort((a, b) => a - b), [16, 32, 48]);
});
