# Foreman Browser E2E Harness

The v0.7.5 browser harness runs Firefox through geckodriver against a
disposable Docker Compose deployment.

It does not use the household deployment, the persistent `foreman-data`
volume, Caddy state, certificates, private keys, or the live port at
`127.0.0.1:3000`.

## Bootstrap

Create the local development-only Python environment:

```bash
./scripts/bootstrap_browser_e2e.sh
```

The environment is stored in `.venv-e2e/` and is ignored by Git.

## Run

Run the complete current browser-harness suite:

```bash
./scripts/run_browser_e2e.sh
```

The runner:

1. Chooses an unused loopback port.
2. Creates a unique Docker Compose project name.
3. renders and validates the resolved Compose contract.
4. Rejects live volumes, Caddy, live database paths, unsafe bindings, and
   elevated container access.
5. Builds and starts only disposable backend and frontend services.
6. Waits for `/api/health`.
7. Starts Firefox with a fresh WebDriver session.
8. Runs the E2E test suite.
9. Removes the disposable containers, network, and locally built images.

## Focused safety tests

The contract and configuration tests do not require a running deployment:

```bash
PYTHONPATH=e2e python3 -m unittest discover \
  -s e2e/tests -p 'test_harness_contract.py'
```

## Diagnostics

Failed browser tests retain bounded diagnostics under `artifacts/e2e/`.
Successful runs remove their directory unless
`FOREMAN_E2E_KEEP_ARTIFACTS=1` is enabled.

Retained evidence is allowlisted: a redacted overlay screenshot, route-only
location, application-state counts, browser-log severity counts, sanitized
test metadata, and an aggregate geckodriver summary.

Raw application text, assertion values, console messages, driver logs, page
source, secrets, payloads, identifiers, and household records are excluded.

Focused diagnostics safety tests:

```bash
PYTHONPATH=e2e python3 -m unittest discover \
  -s e2e/tests -p 'test_harness_diagnostics.py'
```

The complete disposable browser suite also proves this lifecycle through a
controlled failing Firefox fixture whose safe artifacts are inspected and
removed by a passing parent test.
