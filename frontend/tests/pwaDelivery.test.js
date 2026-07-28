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
    assert.match(html, /0\.7\.1/);
});

test("Docker image includes the manifest and icon assets", async () => {
    const dockerfile = await readFrontendFile("Dockerfile");

    assert.match(
        dockerfile,
        /COPY manifest\.webmanifest \/usr\/share\/nginx\/html\/manifest\.webmanifest/
    );
    assert.match(
        dockerfile,
        /COPY assets \/usr\/share\/nginx\/html\/assets/
    );
    assert.doesNotMatch(dockerfile, /service-worker/);
});

test("Nginx delivers PWA files exactly and preserves SPA and API routing", async () => {
    const configuration = await readFrontendFile("default.conf");

    assert.match(
        configuration,
        /location = \/manifest\.webmanifest[\s\S]*default_type application\/manifest\+json;[\s\S]*try_files \$uri =404;/
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
});

test("Commit 1 does not implement or register a service worker", async () => {
    const app = await readFrontendFile("app.js");
    const html = await readFrontendFile("index.html");
    const dockerfile = await readFrontendFile("Dockerfile");

    [app, html, dockerfile].forEach(contents => {
        assert.doesNotMatch(contents, /serviceWorker|service-worker/);
    });
});
