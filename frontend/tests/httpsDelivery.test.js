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

function normalizeWhitespace(source) {
    return source.replace(/\s+/g, " ").trim();
}

function assertOrderedText(source, values, sourceName) {
    let previousIndex = -1;

    for (const value of values) {
        const currentIndex = source.indexOf(value);

        assert.notEqual(
            currentIndex,
            -1,
            `${sourceName} must contain: ${value}`
        );
        assert.ok(
            currentIndex > previousIndex,
            `${sourceName} must place "${value}" in the approved order`
        );
        previousIndex = currentIndex;
    }
}

function extractBetween(source, startMarker, endMarker, sourceName) {
    const startIndex = source.indexOf(startMarker);

    assert.notEqual(
        startIndex,
        -1,
        `${sourceName} must contain section start: ${startMarker}`
    );

    const contentStart = startIndex + startMarker.length;
    const endIndex = source.indexOf(endMarker, contentStart);

    assert.notEqual(
        endIndex,
        -1,
        `${sourceName} must contain section end: ${endMarker}`
    );
    assert.ok(
        endIndex > contentStart,
        `${sourceName} section markers must be in document order`
    );

    return source.slice(contentStart, endIndex);
}

function extractTableRow(source, rowName, sourceName) {
    const rowPrefix = `| ${rowName} |`;
    const row = source.split(/\r?\n/).find(line => line.startsWith(rowPrefix));

    assert.ok(row, `${sourceName} must contain the ${rowName} ownership row`);
    return row;
}

function extractSentenceStartingWith(source, startMarker, sourceName) {
    const startIndex = source.indexOf(startMarker);

    assert.notEqual(
        startIndex,
        -1,
        `${sourceName} must contain sentence start: ${startMarker}`
    );

    const endIndex = source.indexOf(".", startIndex);

    assert.notEqual(
        endIndex,
        -1,
        `${sourceName} must terminate the ${startMarker} sentence`
    );
    return source.slice(startIndex, endIndex + 1);
}

function assertScopeIncludes(scope, requiredValues, scopeName) {
    const normalizedScope = normalizeWhitespace(scope).toLowerCase();

    for (const value of requiredValues) {
        assert.ok(
            normalizedScope.includes(value.toLowerCase()),
            `${scopeName} must contain: ${value}`
        );
    }
}

function assertScopeExcludes(scope, prohibitedPattern, scopeName) {
    assert.doesNotMatch(
        normalizeWhitespace(scope),
        prohibitedPattern,
        `${scopeName} contains prohibited ownership`
    );
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
    const backupVerificationRoute = [
        "location = \\/api\\/recovery\\/backups\\/verify \\{",
        "[\\s\\S]*client_max_body_size 2065m;",
        "[\\s\\S]*proxy_http_version 1\\.1;",
        "[\\s\\S]*proxy_request_buffering off;",
        "[\\s\\S]*proxy_pass http:\\/\\/backend:5000;"
    ].join("");
    const restorePreflightRoute = [
        "location = \\/api\\/recovery\\/restores\\/preflight \\{",
        "[\\s\\S]*client_max_body_size 2065m;",
        "[\\s\\S]*proxy_http_version 1\\.1;",
        "[\\s\\S]*proxy_request_buffering off;",
        "[\\s\\S]*proxy_pass http:\\/\\/backend:5000;"
    ].join("");

    assert.match(nginxSource, /root \/usr\/share\/nginx\/html;/);
    assert.match(
        nginxSource,
        /location \/api\/[\s\S]*proxy_pass http:\/\/backend:5000;/
    );
    assert.match(
        nginxSource,
        new RegExp(backupVerificationRoute)
    );
    assert.match(
        nginxSource,
        new RegExp(restorePreflightRoute)
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
        /id="footer-version">\s*0\.8\.4\s*<\/span>/
    );
    assert.match(backendSource, /APPLICATION_VERSION = "0\.8\.4"/);
    assert.match(
        workerSource,
        /SHELL_CACHE_NAME = "foreman-shell-v0\.8\.4-c1"/
    );
});

test("release documentation preserves history and v0.8.4 continuity", async () => {
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

    assert.match(
        changelog,
        /# v0\.8\.4 — 2026-08-14/
    );
    assert.match(
        changelog,
        /# v0\.8\.3 — 2026-08-13/
    );
    assert.match(
        changelog,
        /# v0\.8\.2 — 2026-08-10/
    );
    assert.match(
        changelog,
        /# v0\.8\.1 — 2026-08-08/
    );
    assert.match(
        changelog,
        /# v0\.8\.0 — 2026-08-07/
    );
    assert.match(
        readme,
        /v0\.8\.4 — Money/
    );
    assert.match(
        readme,
        /external working\s+memory and continuity system/
    );
    assert.match(readme, /AI is not part of v0\.8\.4/);
    assert.match(architecture, /continuity system/i);
    assert.match(
        architecture,
        /AI interpretation must remain[\s\S]*authoritative records/
    );
    assert.match(
        roadmap,
        /v0\.7\.4 — Backup, Export, Restore, and Verification ✅[\s\S]*Status: Complete/
    );
    assert.match(
        roadmap,
        /v0\.7\.5 — Frontend Hardening and Browser E2E ✅[\s\S]*Status: Complete/
    );
    assert.ok(
        roadmap.indexOf("v0.7.4 — Backup, Export, Restore, and Verification") <
        roadmap.indexOf("v0.7.5 — Frontend Hardening and Browser E2E")
    );
    assert.match(changelog, /# v0\.7\.5 — 2026-08-03/);
    assert.match(changelog, /# v0\.7\.4 — 2026-08-01/);
    assert.match(changelog, /# v0\.7\.2/);
    assert.match(
        tasks,
        /- \[x\] Reconcile v0\.7\.5 documentation and release metadata\./
    );
    assert.match(
        tasks,
        /- \[x\] Complete v0\.7\.5 release validation\./
    );
    assert.match(tasks, /- \[x\] Complete v0\.7\.4 release validation\./);
    assert.match(foundersLetter, /external working memory and continuity system/);
    assert.match(foundersLetter, /continue rather than restart/);
});

test("approved v0.8 and v0.9 architecture boundaries are documented", async () => {
    const documentPaths = {
        architecture: "ARCHITECTURE.md",
        readme: "README.md",
        roadmap: "ROADMAP.md",
        tasks: "docs/TASKS.md",
        universal: "docs/V0_8_UNIVERSAL_ARCHITECTURE.md",
        changelog: "CHANGELOG.md",
        contributing: "CONTRIBUTING.md",
        vision: "docs/PROJECT_VISION.md",
        design: "docs/DESIGN_PRINCIPLES.md",
        agents: "docs/AGENTS.md"
    };
    const documents = Object.fromEntries(await Promise.all(
        Object.entries(documentPaths).map(async ([name, fileName]) => [
            name,
            await readRepositoryFile(fileName)
        ])
    ));
    const milestones = [
        "v0.8.0 — Universal Navigation & Spaces",
        "v0.8.1 — Universal Work System",
        "v0.8.2 — Tools, Inventory & Care",
        "v0.8.3 — Calendar & Scheduling",
        "v0.8.4 — Money",
        "v0.8.5 — Library, Records & Search",
        "v0.8.6 — Today Workspace & Household Proving Ground",
        "v0.8.7 — Operational Refinement & UX Convergence",
        "v0.9.0 — Capacity Engine",
        "v0.9.1 — Priority Engine",
        "v0.9.2 — Morning Briefing"
    ];
    const dependencyFlow = [
        "Modules provide authoritative facts",
        "Calendar records commitments and availability",
        "Capacity determines realistic eligibility",
        "Priority ranks eligible Work",
        "Morning Briefing presents explainable recommendations"
    ];
    const normalized = Object.fromEntries(
        Object.entries(documents).map(([name, source]) => [
            name,
            normalizeWhitespace(source)
        ])
    );

    for (const name of ["roadmap", "tasks", "universal"]) {
        assertOrderedText(documents[name], milestones, documentPaths[name]);
    }
    for (const name of ["architecture", "tasks", "universal", "vision", "agents"]) {
        assertOrderedText(
            normalized[name],
            dependencyFlow,
            documentPaths[name]
        );
    }

    assertOrderedText(documents.universal, [
        "- Today",
        "- Calendar",
        "- Work",
        "- Resources",
        "- Money",
        "- Library"
    ], documentPaths.universal);
    assert.ok(normalized.universal.includes(
        "Settings and Account remain separate below the primary navigation."
    ));
    assert.ok(normalized.universal.includes(
        "Modules are managed under Settings. Enabled modules contribute " +
        "functionality inside the six stable categories rather than adding " +
        "top-level sidebar entries by default."
    ));

    assert.ok(normalized.universal.includes(
        "Normal operational workflows begin with one clearly selected active Space."
    ));
    assert.ok(normalized.universal.includes(
        "Projects operate within the active Space."
    ));
    assert.ok(normalized.universal.includes(
        "Tasks operate within the active Space."
    ));
    assert.ok(normalized.universal.includes(
        "Inventory operates within the active Space."
    ));
    assert.ok(normalized.universal.includes(
        "Backend APIs enforce Space context authoritatively."
    ));
    assert.ok(normalized.universal.includes(
        "Frontend filtering alone is never sufficient for Space isolation."
    ));
    assert.ok(normalized.universal.includes(
        "Broad multi-Space aggregation is not part of normal v0.8.0 operation."
    ));

    const peopleSection = extractBetween(
        documents.universal,
        "# 4. People",
        "# 5. Organizations",
        documentPaths.universal
    );
    const organizationSection = extractBetween(
        documents.universal,
        "# 5. Organizations",
        "# 6. Members, Authentication, and Authorization",
        documentPaths.universal
    );
    const memberSection = extractBetween(
        documents.universal,
        "# 6. Members, Authentication, and Authorization",
        "# 7. Universal Work",
        documentPaths.universal
    );

    assertScopeIncludes(peopleSection, [
        "The v0.8.0 Person foundation includes only:",
        "Stable identity",
        "Basic descriptive fields",
        "Space relationships",
        "Role or relationship classifications",
        "Basic CRUD",
        "Stable references for future records",
        "v0.8.0 does not implement:",
        "CRM pipelines",
        "Sales processes",
        "Communication histories"
    ], "People section");
    assertScopeIncludes(organizationSection, [
        "The v0.8.0 Organization foundation includes only:",
        "Stable identity",
        "Basic descriptive fields",
        "Space relationships",
        "Role classifications",
        "Basic CRUD",
        "Stable references for future records",
        "v0.8.0 does not implement:",
        "Supplier-management workflows",
        "Purchasing behavior",
        "Sales processes",
        "Complex organization hierarchies",
        "Communication histories"
    ], "Organizations section");
    assertScopeIncludes(memberSection, [
        "A Person and a Member are not the same record.",
        "Member — that Person’s participation in a Space",
        "Role or responsibility — what the Member does operationally",
        "v0.8.0 Members are operational participation records.",
        "User accounts",
        "Login credentials",
        "Complete permission systems"
    ], "Members section");

    const registrySection = extractBetween(
        documents.universal,
        "# 13. Module Registry",
        "# 14. Data Ownership",
        documentPaths.universal
    );
    const permittedRegistryScope = extractBetween(
        registrySection,
        "Permitted concepts include:",
        "Contribution locations are limited",
        "Module Registry section"
    );
    const prohibitedRegistryScope = extractBetween(
        registrySection,
        "The following concepts are prohibited",
        "---",
        "Module Registry section"
    );

    assertScopeIncludes(registrySection, [
        "The module registry under Settings supports local product configuration.",
        "Module enablement is configuration, not monetization."
    ], "Module Registry section");
    assertScopeIncludes(permittedRegistryScope, [
        "Module identifier",
        "Module name",
        "Description",
        "Enabled or disabled state",
        "Required dependencies",
        "Contribution locations",
        "Safe-enable rules",
        "Safe-disable rules",
        "Data-retention behavior when disabled",
        "Module health or compatibility state"
    ], "permitted Module Registry scope");
    assertScopeIncludes(prohibitedRegistryScope, [
        "Subscription plans",
        "Billing",
        "Paid tiers",
        "Licensing checks",
        "Commercial entitlements",
        "SaaS tenants",
        "Customer provisioning"
    ], "prohibited Module Registry scope");

    assert.ok(normalized.readme.includes(
        "Today is the implemented default primary workspace. Through v0.8.7, " +
        "Today presents authoritative factual current state only."
    ));
    assert.ok(normalized.readme.includes(
        "The v0.9.2 Morning Briefing becomes the capacity-aware primary daily " +
        "experience presented through Today."
    ));

    assert.ok(normalized.architecture.includes(
        "Calendar may record fixed commitments, events, routines, recurrence, " +
        "and availability before the Capacity Engine exists."
    ));
    assert.ok(normalized.architecture.includes(
        "Capacity evaluation must precede automatic placement of optional Work, " +
        "feasibility claims, prioritization, recommendations, and " +
        "capacity-aware scheduling decisions."
    ));

    const workScopes = {
        roadmap: extractBetween(
            normalized.roadmap,
            "## v0.8.1 — Universal Work System",
            "Work may reference Calendar routines",
            documentPaths.roadmap
        ),
        universal: extractBetween(
            normalized.universal,
            "# 7. Universal Work",
            "# 8. Resources",
            documentPaths.universal
        ),
        design: extractSentenceStartingWith(
            normalized.design,
            "Work owns",
            documentPaths.design
        ),
        agents: extractSentenceStartingWith(
            normalized.agents,
            "Work owns",
            documentPaths.agents
        )
    };
    const requiredWorkOwnership = [
        "Tasks",
        "Projects",
        "requirements",
        "dependencies",
        "progress"
    ];

    for (const [name, scope] of Object.entries(workScopes)) {
    assertScopeIncludes(
        scope,
        requiredWorkOwnership,
        `${documentPaths[name]} Work scope`
    );
}

/*
 * Design Principles and AGENTS use terse "Work owns..." statements,
 * so those ownership statements must not claim Calendar concepts.
 *
 * Roadmap and Universal Architecture intentionally mention routines and
 * recurrence while defining the boundary that Calendar owns them.
 */
for (const name of ["design", "agents"]) {
    assertScopeExcludes(
        workScopes[name],
        /\b(?:routines?|recurrence)\b/i,
        `${documentPaths[name]} Work ownership statement`
    );
}

for (const name of ["roadmap", "universal"]) {
    assertScopeIncludes(normalized[name], [
        "Calendar routines or scheduled occurrences",
        "does not own routine definitions"
    ], `${documentPaths[name]} routine-reference boundary`);
}

assertScopeIncludes(normalized.universal, [
    "Calendar remains authoritative for commitments, events, routines, recurrence, and availability.",
    "A dependency does not determine Capacity, feasibility, scheduling, Priority, recommendations, or Morning Briefing behavior."
], `${documentPaths.universal} Work boundary`);

    const roadmapResourcesSection = extractBetween(
        normalized.roadmap,
        "## v0.8.2 — Tools, Inventory & Care",
        "## v0.8.3 — Calendar & Scheduling",
        documentPaths.roadmap
    );
    const roadmapInventoryScope = extractBetween(
        roadmapResourcesSection,
        "Scope:",
        "Explicitly excluded:",
        documentPaths.roadmap
    );
    const inventoryScopes = {
        readme: extractBetween(
            normalized.readme,
            "## Inventory",
            "Purchasing and supplier-management workflows remain deferred",
            documentPaths.readme
        ),
        roadmap: roadmapInventoryScope,
        universal: extractTableRow(
            documents.universal,
            "Inventory",
            documentPaths.universal
        ),
        design: extractSentenceStartingWith(
            normalized.design,
            "Inventory owns",
            documentPaths.design
        )
    };

    for (const [name, scope] of Object.entries(inventoryScopes)) {
        assertScopeIncludes(
            scope,
            ["consumable stock", "usage"],
            `${documentPaths[name]} Inventory scope`
        );
        assertScopeExcludes(
            scope,
            /\b(?:purchase tracking|purchasing workflows?|supplier management|supplier workflows?)\b/i,
            `${documentPaths[name]} Inventory scope`
        );
    }
    assertScopeIncludes(normalized.readme, [
        "Purchasing and supplier-management workflows remain deferred " +
        "specialized concerns.",
        "without becoming Inventory authority."
    ], "README deferred purchasing boundary");
    assertScopeIncludes(roadmapResourcesSection, [
        "Explicitly excluded:",
        "Purchasing workflows"
    ], "ROADMAP deferred purchasing boundary");

    const ownershipSection = extractBetween(
        documents.universal,
        "# 14. Data Ownership",
        "# 15. Backend Authority",
        documentPaths.universal
    );
    const resourcesSection = extractBetween(
        documents.universal,
        "# 8. Resources",
        "# 9. Money",
        documentPaths.universal
    );
    const ownershipRows = {
        Work: extractTableRow(ownershipSection, "Work", "Data Ownership section"),
        Calendar: extractTableRow(
            ownershipSection,
            "Calendar",
            "Data Ownership section"
        ),
        Inventory: extractTableRow(
            ownershipSection,
            "Inventory",
            "Data Ownership section"
        ),
        Money: extractTableRow(ownershipSection, "Money", "Data Ownership section"),
        Library: extractTableRow(
            ownershipSection,
            "Library",
            "Data Ownership section"
        )
    };

    assertScopeIncludes(ownershipRows.Work, requiredWorkOwnership, "Work ownership row");
    assertScopeIncludes(ownershipRows.Calendar, [
        "commitments",
        "events",
        "routines",
        "recurrence",
        "availability"
    ], "Calendar ownership row");
    assertScopeIncludes(ownershipRows.Inventory, [
        "consumable stock",
        "quantities",
        "thresholds",
        "locations",
        "usage"
    ], "Inventory ownership row");
    assertScopeIncludes(resourcesSection, [
        "Tools owns durable equipment",
        "condition",
        "availability",
        "maintenance history",
        "Care Plans owns",
        "maintenance",
        "care definitions"
    ], "Resources ownership section");
    assertScopeIncludes(ownershipRows.Money, [
        "financial records"
    ], "Money ownership row");
    assertScopeIncludes(ownershipRows.Library, [
        "stored records",
        "document references"
    ], "Library ownership row");

    const prohibitedOwnershipScope = extractBetween(
        ownershipSection,
        "Modules must not:",
        "---",
        "Data Ownership section"
    );
    assertScopeIncludes(prohibitedOwnershipScope, [
        "Directly manipulate another module’s private tables",
        "Duplicate authoritative data",
        "Maintain competing browser-side sources of truth",
        "Create circular ownership",
        "Require unrelated modules to initialize before functioning"
    ], "prohibited module ownership scope");

    assert.ok(normalized.tasks.includes(
        "HardHead remains local and LAN-only through Version 1.0."
    ));
    assert.ok(normalized.tasks.includes(
        "Secure persistent remote access begins no earlier than Version 1.1."
    ));
    assert.ok(normalized.roadmap.includes(
        "Gregg receives no persistent remote access before v1.1."
    ));
    assert.ok(normalized.roadmap.includes(
        "AI remains optional and is never required for core operation."
    ));
    assert.ok(normalized.tasks.includes(
        "Commercial SaaS and subscription infrastructure remain deferred until " +
        "after Version 3.0 unless the founder explicitly reopens that direction."
    ));
    assert.ok(normalized.universal.includes(
        "Subscription features, billing, commercial entitlements, managed-hosting " +
        "plans, public SaaS infrastructure, and other commercialization systems " +
        "remain deferred until after v3.0."
    ));
    assert.ok(normalized.tasks.includes(
        "Commit 1 was documentation-only. It did not change schema, APIs, " +
        "frontend navigation, migration behavior, runtime version metadata, " +
        "cache identity, Docker deployment, or live data."
    ));

    assert.ok(normalized.changelog.includes(
        "Kept the first v0.8.0 reconciliation change documentation-only"
    ));
    assert.ok(normalized.changelog.includes(
        "# v0.8.0 — 2026-08-07"
    ));
    assert.ok(normalized.roadmap.includes(
        "v0.8.0 — Universal Navigation & Spaces ✅ Status: Complete"
    ));
    assert.ok(normalized.tasks.includes(
        "## Completed v0.8.0 — Universal Navigation & Spaces"
    ));

    const stalePatterns = [
        /Morning Briefing (?:is|remains) the Dashboard(?:'s|’s) default workspace/i,
        /Dashboard[^.]{0,240}Morning Briefing (?:is|remains) its default workspace/i,
        /Dashboard (?:is|remains) the (?:(?:permanent|target) )?application shell/i,
        /Capacity always precedes scheduling/i,
        /Capacity must be evaluated before scheduling/i,
        /Capacity must precede scheduling/i,
        /Scheduling cannot occur before Capacity/i,
        /Capacity must evaluate[^.\n]*before (?:it|work) is scheduled/i,
        /Work owns[^.\n]*routines/i,
        /\| Work \|[^|\n]*routine/i,
        /Inventory owns[^.\n]*(?:supplier management|purchasing workflows)/i
    ];

    for (const [name, source] of Object.entries(normalized)) {
        for (const pattern of stalePatterns) {
            assert.doesNotMatch(
                source,
                pattern,
                `${documentPaths[name]} contains stale architecture wording`
            );
        }
    }
});
