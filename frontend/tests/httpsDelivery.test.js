import assert from "node:assert/strict";
import { readFile, readdir } from "node:fs/promises";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";
const repositoryDirectory = path.resolve(
    path.dirname(fileURLToPath(import.meta.url)),
    "..",
    ".."
);

async function readRepositoryFile(fileName) {
    return readFile(path.join(repositoryDirectory, fileName), "utf8");
}

const composeSource = await readRepositoryFile("compose.yaml");
const caddySource = await readRepositoryFile("docker/Caddyfile");
const ignoreSource = await readRepositoryFile(".gitignore");
const environmentExample = await readRepositoryFile(".env.example");

test("Compose defines an immutable Caddy gateway without elevated access", () => {
    assert.match(
        composeSource,
        /caddy:\s*\n\s+image: caddy:2\.11\.4-alpine@sha256:[a-f0-9]{64}/
    );
    assert.match(
        composeSource,
        /\.\/docker\/Caddyfile:\/etc\/caddy\/Caddyfile:ro/
    );
    assert.match(composeSource, /caddy-data:\/data/);
    assert.match(composeSource, /caddy-config:\/config/);
    assert.doesNotMatch(composeSource, /docker\.sock/);
    assert.doesNotMatch(composeSource, /\bprivileged:\s*true\b/);
    assert.doesNotMatch(composeSource, /\bnetwork_mode:\s*host\b/);
});

test("Compose publishes only the approved LAN and loopback bindings", () => {
    assert.match(composeSource, /"127\.0\.0\.1:3000:80"/);
    assert.match(
        composeSource,
        /"\$\{FOREMAN_LAN_IP:\?[^}]+\}:80:80"/
    );
    assert.match(
        composeSource,
        /"\$\{FOREMAN_LAN_IP:\?[^}]+\}:443:443"/
    );
    assert.doesNotMatch(composeSource, /"\s*3000:80"/);
    assert.doesNotMatch(composeSource, /0\.0\.0\.0:/);
    assert.doesNotMatch(composeSource, /\[::\]:/);
});

test("missing FOREMAN_LAN_IP cannot silently create a binding", () => {
    assert.match(
        composeSource,
        /FOREMAN_LAN_IP: \$\{FOREMAN_LAN_IP:\?FOREMAN_LAN_IP is required\}/
    );
    assert.doesNotMatch(
        composeSource,
        /\$\{FOREMAN_LAN_IP(?::-|:-)[^}]*\}/
    );
    assert.equal(
        environmentExample,
        "FOREMAN_LAN_IP=192.168.1.184\n"
    );
});

test("the backend stays private while Caddy reaches only the frontend", () => {
    const backendSection = composeSource.match(
        /services:\s*\n\s+backend:([\s\S]*?)\n\s+frontend:/
    )?.[1] ?? "";
    const caddySection = composeSource.match(
        /\n\s+caddy:([\s\S]*?)\nvolumes:/
    )?.[1] ?? "";

    assert.doesNotMatch(backendSection, /\n\s+ports:/);
    assert.match(caddySection, /depends_on:\s*\n\s+- frontend/);
    assert.match(caddySource, /reverse_proxy frontend:80/);
    assert.doesNotMatch(caddySource, /backend:5000/);
});

test("Caddy uses only its internal issuer for the approved IP origin", () => {
    assert.match(caddySource, /https:\/\/\{\$FOREMAN_LAN_IP\}/);
    assert.match(caddySource, /\btls internal\b/);
    assert.match(caddySource, /default_sni \{\$FOREMAN_LAN_IP\}/);
    assert.doesNotMatch(
        caddySource,
        /acme|letsencrypt|zerossl|hardhead\.(?:home\.arpa|local)/i
    );
});

test("HTTP permanently redirects the complete URI to HTTPS", () => {
    assert.match(
        caddySource,
        /http:\/\/\{\$FOREMAN_LAN_IP\}[\s\S]*redir https:\/\/\{\$FOREMAN_LAN_IP\}\{uri\} permanent/
    );
    assert.match(caddySource, /auto_https disable_redirects/);
});

test("unknown hosts have no proxy route and the admin API is disabled", () => {
    assert.equal(
        (caddySource.match(/reverse_proxy/g) ?? []).length,
        1
    );
    assert.match(caddySource, /\badmin off\b/);
    assert.doesNotMatch(composeSource, /2019(?::|")/);
    assert.doesNotMatch(caddySource, /:\d+\s*\{[\s\S]*reverse_proxy/);
});

test("Caddy preserves host and HTTPS forwarding information", () => {
    assert.match(
        caddySource,
        /header_up Host \{http\.request\.host\}/
    );
    assert.match(
        caddySource,
        /header_up X-Forwarded-Host \{http\.request\.host\}/
    );
    assert.match(
        caddySource,
        /header_up X-Forwarded-Proto \{http\.request\.scheme\}/
    );
});

test("only the approved edge security headers are configured", () => {
    assert.match(caddySource, /X-Content-Type-Options "nosniff"/);
    assert.match(caddySource, /Referrer-Policy "same-origin"/);
    assert.match(caddySource, /X-Frame-Options "DENY"/);
    assert.match(
        caddySource,
        /Content-Security-Policy "frame-ancestors 'none'"/
    );
    assert.doesNotMatch(
        caddySource,
        /Strict-Transport-Security|includeSubDomains|preload/i
    );
});

test("Caddy does not configure response caching", () => {
    assert.doesNotMatch(
        caddySource,
        /\bcache\b|Cache-Control|header_down\s+Age/i
    );
});

test("deployment secrets and local trust artifacts are ignored safely", () => {
    for (const pattern of [
        ".env",
        ".env.*",
        "!.env.example",
        "/local/",
        "/secrets/",
        "/certificates/",
        "/docker/tls/",
        "*.key",
        "*.pem",
        "*.crt",
        "*.cer",
        "*.p12",
        "*.pfx"
    ]) {
        assert.equal(ignoreSource.split("\n").includes(pattern), true);
    }
});

test(".env is ignored while .env.example is explicitly excepted", () => {
    assert.match(ignoreSource, /^\.env$/m);
    assert.match(ignoreSource, /^\.env\.\*$/m);
    assert.match(ignoreSource, /^!\.env\.example$/m);
});

test("repository source contains no certificate or private-key artifact", async () => {
    const excludedDirectories = new Set([
        ".agents",
        ".codex",
        ".git",
        ".venv-e2e",
        "certificates",
        "local",
        "secrets"
    ]);
    const textFileNames = new Set([
        ".env.example",
        ".gitignore",
        "Caddyfile",
        "Dockerfile"
    ]);
    const textExtensions = new Set([
        ".conf",
        ".css",
        ".html",
        ".js",
        ".json",
        ".md",
        ".py",
        ".txt",
        ".webmanifest",
        ".yaml",
        ".yml"
    ]);
    const repositoryFiles = [];

    async function collectFiles(directory, relativeDirectory = "") {
        const entries = await readdir(directory, { withFileTypes: true });

        for (const entry of entries) {
            const relativePath = path.join(relativeDirectory, entry.name);

            if (entry.isDirectory()) {
                if (
                    excludedDirectories.has(entry.name)
                    || relativePath === path.join("docker", "tls")
                ) {
                    continue;
                }

                await collectFiles(
                    path.join(directory, entry.name),
                    relativePath
                );
                continue;
            }

            repositoryFiles.push(relativePath);
        }
    }

    await collectFiles(repositoryDirectory);

    assert.equal(
        repositoryFiles.some(fileName =>
            /\.(?:key|pem|crt|cer|p12|pfx)$/i.test(fileName)
        ),
        false
    );

    for (const fileName of repositoryFiles) {
        if (
            !textFileNames.has(path.basename(fileName))
            && !textExtensions.has(path.extname(fileName))
        ) {
            continue;
        }

        const filePath = path.join(repositoryDirectory, fileName);
        const source = await readFile(filePath, "utf8");

        assert.doesNotMatch(source, /-----BEGIN [^-]*PRIVATE KEY-----/);
    }
});

test("existing Nginx remains the static and API authority", async () => {
    const nginxSource = await readRepositoryFile("frontend/default.conf");

    assert.match(nginxSource, /root \/usr\/share\/nginx\/html;/);
    assert.match(
        nginxSource,
        /location \/api\/[\s\S]*proxy_pass http:\/\/backend:5000;/
    );
    assert.match(
        nginxSource,
        /location = \/api\/recovery\/backups\/verify \{[\s\S]*client_max_body_size 2065m;[\s\S]*proxy_http_version 1\.1;[\s\S]*proxy_request_buffering off;[\s\S]*proxy_pass http:\/\/backend:5000;/
    );
    assert.match(
        nginxSource,
        /location = \/api\/recovery\/restores\/preflight \{[\s\S]*client_max_body_size 2065m;[\s\S]*proxy_http_version 1\.1;[\s\S]*proxy_request_buffering off;[\s\S]*proxy_pass http:\/\/backend:5000;/
    );
    assert.match(
        nginxSource,
        /location \/\s*\{[\s\S]*try_files \$uri \$uri\/ \/index\.html;/
    );
});

test("release version and shell cache are finalized", async () => {
    const indexSource = await readRepositoryFile("frontend/index.html");
    const backendSource = await readRepositoryFile(
        "backend/app/core/config.py"
    );
    const workerSource = await readRepositoryFile(
        "frontend/service-worker.js"
    );

    assert.match(
        indexSource,
        /id="footer-version">\s*0\.7\.4\s*<\/span>/
    );
    assert.match(backendSource, /APPLICATION_VERSION = "0\.7\.4"/);
    assert.match(
        workerSource,
        /SHELL_CACHE_NAME = "foreman-shell-v0\.7\.4-c1"/
    );
});

test("v0.7.4 release documentation preserves continuity and boundaries", async () => {
    const [
        readme,
        architecture,
        roadmap,
        changelog,
        tasks,
        foundersLetter
    ] = await Promise.all([
        readRepositoryFile("README.md"),
        readRepositoryFile("ARCHITECTURE.md"),
        readRepositoryFile("ROADMAP.md"),
        readRepositoryFile("CHANGELOG.md"),
        readRepositoryFile("docs/TASKS.md"),
        readRepositoryFile("docs/FOUNDERS_LETTER.md")
    ]);

    assert.match(readme, /v0\.7\.4 — Backup, Export, Restore, and Verification/);
    assert.match(
        readme,
        /external working\s+memory and continuity system/
    );
    assert.match(readme, /AI is not part of v0\.7\.4/);
    assert.match(architecture, /continuity system/i);
    assert.match(architecture, /AI interpretation must remain[\s\S]*authoritative records/);
    assert.match(
        roadmap,
        /v0\.7\.4 — Backup, Export, Restore, and Verification ✅[\s\S]*Status: Complete/
    );
    assert.ok(
        roadmap.indexOf("v0.7.4 — Backup, Export, Restore, and Verification") <
        roadmap.indexOf("v0.7.5 — Frontend Hardening and Browser E2E")
    );
    assert.match(
        roadmap,
        /v0\.7\.4 — Backup, Export, Restore, and Verification ✅[\s\S]*Status: Complete/
    );
    assert.match(changelog, /# v0\.7\.4 — 2026-08-01/);
    assert.match(changelog, /# v0\.7\.2/);
    assert.match(tasks, /- \[x\] Complete v0\.7\.4 release validation\./);
    assert.match(tasks, /- \[x\] Add verified manual backup packages\./);
    assert.match(foundersLetter, /external working memory and continuity system/);
    assert.match(foundersLetter, /continue rather than restart/);
});
