import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const frontendDirectory = path.resolve(
    path.dirname(fileURLToPath(import.meta.url)),
    ".."
);

async function readFrontendFile(fileName) {
    return readFile(path.join(frontendDirectory, fileName), "utf8");
}

test("index includes approved PWA and Apple metadata", async () => {
    const html = await readFrontendFile("index.html");

    assert.match(
        html,
        /<link rel="manifest" href="\/manifest\.webmanifest">/
    );
    assert.match(html, /name="theme-color" content="#1d2024"/);
    assert.match(html, /name="application-name" content="The Foreman"/);
    assert.match(
        html,
        /name="apple-mobile-web-app-capable" content="yes"/
    );
    assert.match(
        html,
        /name="apple-mobile-web-app-status-bar-style"\s+content="black-translucent"/
    );
    assert.match(
        html,
        /name="apple-mobile-web-app-title" content="The Foreman"/
    );
    assert.match(
        html,
        /rel="apple-touch-icon"[\s\S]*href="\/assets\/icons\/apple-touch-icon\.png"[\s\S]*sizes="180x180"/
    );
    assert.match(
        html,
        /rel="icon"[\s\S]*href="\/assets\/icons\/favicon\.ico"/
    );
    assert.match(
        html,
        /name="viewport"[\s\S]*content="[^"]*viewport-fit=cover[^"]*"/
    );
    assert.match(html, /<title>The Foreman \| HardHead Works<\/title>/);
    assert.match(html, /0\.7\.3/);
});

test("application shell respects dynamic safe areas without changing widths", async () => {
    const styles = await readFrontendFile("styles.css");

    assert.match(
        styles,
        /body \{[\s\S]*min-height: 100dvh;[\s\S]*padding-top: env\(safe-area-inset-top\);[\s\S]*padding-bottom: env\(safe-area-inset-bottom\);/
    );
    assert.match(
        styles,
        /\.app \{[\s\S]*min-height: calc\([\s\S]*100dvh[\s\S]*- env\(safe-area-inset-top\)[\s\S]*- env\(safe-area-inset-bottom\)[\s\S]*\);[\s\S]*grid-template-columns: 240px 1fr;/
    );
    assert.match(
        styles,
        /\.dialog-backdrop \{[\s\S]*padding: max\(24px, env\(safe-area-inset-top\)\)[\s\S]*max\(24px, env\(safe-area-inset-bottom\)\)[\s\S]*max\(24px, env\(safe-area-inset-left\)\);/
    );
    assert.match(
        styles,
        /@media \(max-width: 850px\) \{[\s\S]*\.app \{[\s\S]*grid-template-columns: 1fr;/
    );
    assert.doesNotMatch(
        styles,
        /padding-(?:top|bottom):\s*(?:44|47|59)px/
    );
});

test("Docker image includes PWA metadata, icons, and service worker", async () => {
    const dockerfile = await readFrontendFile("Dockerfile");

    assert.match(
        dockerfile,
        /COPY manifest\.webmanifest \/usr\/share\/nginx\/html\/manifest\.webmanifest/
    );
    assert.match(
        dockerfile,
        /COPY assets \/usr\/share\/nginx\/html\/assets/
    );
    assert.match(
        dockerfile,
        /COPY service-worker\.js \/usr\/share\/nginx\/html\/service-worker\.js/
    );
});

test("Nginx delivers PWA files exactly and preserves SPA and API routing", async () => {
    const configuration = await readFrontendFile("default.conf");

    assert.match(
        configuration,
        /location = \/manifest\.webmanifest[\s\S]*default_type application\/manifest\+json;[\s\S]*try_files \$uri =404;/
    );
    assert.match(
        configuration,
        /location = \/service-worker\.js[\s\S]*default_type application\/javascript;[\s\S]*Cache-Control "no-cache, no-store, must-revalidate" always;[\s\S]*try_files \$uri =404;/
    );
    assert.match(
        configuration,
        /location ~\* \\\.\(\?:js\|css\|webmanifest\|png\|svg\|ico\)\$[\s\S]*try_files \$uri =404;/
    );
    assert.match(
        configuration,
        /location \/ \{[\s\S]*try_files \$uri \$uri\/ \/index\.html;/
    );
    assert.match(
        configuration,
        /location \/api\/ \{[\s\S]*proxy_pass http:\/\/backend:5000;[\s\S]*proxy_set_header Host \$host;[\s\S]*proxy_set_header X-Real-IP \$remote_addr;/
    );
    assert.match(
        configuration,
        /location = \/api\/recovery\/backups\/verify \{[\s\S]*client_max_body_size 2065m;[\s\S]*proxy_http_version 1\.1;[\s\S]*proxy_request_buffering off;[\s\S]*proxy_pass http:\/\/backend:5000;/
    );
    assert.match(
        configuration,
        /location = \/api\/recovery\/restores\/preflight \{[\s\S]*client_max_body_size 2065m;[\s\S]*proxy_http_version 1\.1;[\s\S]*proxy_request_buffering off;[\s\S]*proxy_pass http:\/\/backend:5000;/
    );
});

test("application startup gates operations behind PWA and health initialization", async () => {
    const app = await readFrontendFile("app.js");

    assert.match(
        app,
        /import \{ initializePwa \} from "\.\/utils\/pwa\.js";/
    );
    assert.match(
        app,
        /import \{[\s\S]*createConnectionController,[\s\S]*setActiveConnectionController[\s\S]*\} from "\.\/utils\/connectionState\.js";/
    );
    assert.match(app, /await initializePwa\(\)\.catch/);
    assert.match(app, /await connectionController\.initialize\(\);/);
    assert.match(app, /void initializeApplication\(\)\.catch/);
    assert.match(app, /initializeRouter\(\);/);
    assert.match(app, /initializeDashboard\(\),/);
    assert.match(app, /migrateLegacyInventory\(\);/);
    assert.match(app, /migrateProjectsAfterInventory\(/);
    assert.match(app, /migrateLegacyTasks\(/);
    assert.match(app, /initializeInventoryPage\(/);
    assert.match(app, /initializeTasksPage\(/);
    assert.match(app, /initializeProjectsPage\(/);
    assert.match(app, /initializeRecoveryPage\(\)/);
    assert.match(app, /initializeSystemStatus\(\)/);

    const pwa = app.indexOf("await initializePwa()");
    const controller = app.indexOf("createConnectionController({");
    const health = app.indexOf("await connectionController.initialize()");
    const inventoryMigration = app.indexOf(
        "const inventoryMigrationResult = await migrateLegacyInventory()"
    );
    const projectMigration = app.indexOf(
        "const projectMigrationResult = await migrateProjectsAfterInventory"
    );
    const taskMigration = app.indexOf(
        "const taskMigrationResult = await migrateLegacyTasks"
    );
    const router = app.indexOf("initializeRouter();");

    assert.ok(pwa < controller);
    assert.ok(controller < health);
    assert.ok(inventoryMigration < projectMigration);
    assert.ok(projectMigration < taskMigration);
    assert.ok(taskMigration < router);
});
