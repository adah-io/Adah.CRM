# Frappe Wiki Phase 1 Compatibility Result

**Date:** 2026-08-15

**Scope:** Phase 1 only — version and image compatibility spike

**Result:** **FAIL**
**Meaning:** the required combined runtime proof did not complete. This is not evidence that CRM and Wiki are intrinsically incompatible; it means Phase 1 has not earned a pass and Phase 2 must not start.

## Executive Result

The repository now contains a disposable, exact-pin compatibility harness under [`docker/wiki-phase1/`](./docker/wiki-phase1/) and a manual Linux runner at [`.github/workflows/wiki-phase1.yml`](./.github/workflows/wiki-phase1.yml). It is designed to build Frappe, Adah CRM, and Wiki into one Bench image, create one site, install both apps, run migrations, start normal Bench processes, and perform HTTP/session/content smoke checks.

The local execution host could not complete that harness. Docker was unavailable on Windows. Docker installed inside the existing WSL2 Ubuntu distribution, but extracting the Bench image remounted its ext4 filesystem read-only and hung the daemon. After recovery and disabling Docker, a native Python 3.14/Node 24/MariaDB/Redis attempt reached source checkout setup, then the WSL distribution crashed and subsequently failed to start with `Wsl/Service/CreateInstance/E_FAIL`. No production system or database was contacted.

Because installation, migration, combined assets, routes, workers, realtime, and shared-session checks remain unverified, the honest Phase 1 result is **FAIL**. Run the checked-in manual workflow or `docker/wiki-phase1/run.sh` on a healthy Linux Docker host before reconsidering the result.

## Status Vocabulary

- **VERIFIED** — directly observed in this spike.
- **FAILED** — a command ran and did not meet its expected outcome.
- **WARNING** — a condition matters but does not independently prove incompatibility.
- **UNKNOWN** — the required test did not complete.

## Proven Version Matrix

### Source pins

| Component | Exact pin | Status |
|---|---|---|
| Adah CRM | `4ccd8dfc166c2e7203aba5aca57b1545700c966b` | **VERIFIED** local `develop` HEAD and remote `develop` at spike start |
| Frappe | `ba36d03916ee05391bee0cf0f979ab97d552eede` | **VERIFIED** remote `develop` HEAD selected at spike start; runtime compatibility **UNKNOWN** |
| Frappe Wiki | `2e4e4f215368387c08553c3c59723c7a2e1bf306` | **VERIFIED** requested candidate and inspected checkout |

The image does not pass raw SHAs to Bench's branch-only interface. It fetches each exact commit into a temporary repository, asserts `HEAD`, creates a local `phase1-pin` tag, lets Bench clone that local tag, and asserts all three installed app `HEAD` values again before dependency setup and asset build. No floating app branch is used by the resulting Bench.

### Harness runtime

| Component | Pinned version | Status |
|---|---|---|
| Python base | `python:3.14.2-slim-bookworm@sha256:e87711ef5c86aaeaa7031718a69db79d334d94c545c709583f651b8185870941` | **VERIFIED** registry digest; image build **UNKNOWN** |
| Python | `3.14.2` | **UNKNOWN** in combined image |
| Node | `24.19.0`, tarball SHA-256 `14b342e...b409647` | **VERIFIED** checksum source and host runtime; image build **UNKNOWN** |
| Yarn | `1.22.22` | **VERIFIED** host runtime; image build **UNKNOWN** |
| Bench | `5.31.0` | **VERIFIED** native WSL installation; image build **UNKNOWN** |
| MariaDB | `mariadb:10.11.14@sha256:dbe56e...95790c` | **VERIFIED** registry digest; combined migration **UNKNOWN** |
| Redis | `redis:7.0.15-alpine@sha256:c9d92d...386b2` | **VERIFIED** registry digest; combined connections **UNKNOWN** |
| Docker Engine | `29.1.3` in disposable WSL | **VERIFIED**, then **FAILED** at WSL storage layer |
| Docker Compose | `2.40.3` in disposable WSL | **VERIFIED**, harness run **UNKNOWN** |

The native fallback successfully reported Python `3.14.7`, Node `24.19.0`, Yarn `1.22.22`, Bench `5.31.0`, MariaDB `10.11.14`, and Redis `7.0.15` before WSL failed. Those native versions are diagnostic only; they do not replace the pinned image matrix.

## Current Repository Runtime Assumptions

| Item | Repository evidence | Finding |
|---|---|---|
| CRM Frappe dependency | [`pyproject.toml`](./pyproject.toml) | `>=16.0.0-dev,<=17.0.0-dev` |
| CRM Python metadata | [`pyproject.toml`](./pyproject.toml) | `>=3.10`; effective v16 runtime is Python 3.14 |
| CRM Node engine | [`frontend/package.json`](./frontend/package.json) | `^20.19.0 || >=22.12.0`; Node 24 selected to match Frappe v16 CI |
| Yarn | Repository lock/scripts and CI global install | Yarn Classic `1.22.22` observed |
| Existing local Docker | [`docker/init.sh`](./docker/init.sh) | **WARNING:** initializes `version-15` and fetches floating CRM `main` |
| Existing image workflow | [`.github/workflows/builds.yml`](./.github/workflows/builds.yml) | **WARNING:** builds Frappe `version-15` and upstream CRM `main`, not Adah `develop` |
| Develop CI | [`.github/actions/setup-server-env/action.yml`](./.github/actions/setup-server-env/action.yml) | Python 3.14, Node 24, Frappe `develop` |
| MariaDB | [`docker/docker-compose.yml`](./docker/docker-compose.yml), migration CI | Local Docker uses 10.8; migration CI uses 10.6; harness selects supported 10.11.14 explicitly |
| Redis | [`docker/docker-compose.yml`](./docker/docker-compose.yml) | Floating `redis:alpine`; harness selects 7.0.15 explicitly |

The v15 configuration was not silently rewritten because it may still serve the stable/main lane. The Phase 1 harness is isolated and explicitly v16. If the spike later passes, maintainers must decide whether to replace the old local setup or keep separate stable and develop lanes.

## Harness Behavior

The harness performs this sequence:

1. build a Python 3.14.2/Node 24.19.0 image;
2. fetch and assert the exact Frappe, CRM, and Wiki SHAs;
3. initialize one Bench and build all app assets;
4. start pinned MariaDB and Redis services;
5. create disposable site `wiki-phase1.localhost`;
6. install `crm`, then `wiki`, then migrate;
7. start the normal Bench web, worker, scheduler, and Socket.IO processes;
8. assert the installed apps and Git pins;
9. authenticate once as `Administrator` and use that session across CRM and Wiki;
10. load `/crm`, `/wiki-app`, and `/docs`, and fetch app-specific assets;
11. create, edit, read, and render a Wiki Document;
12. rerun migrate and tear down the containers and volumes.

Run on a Linux Docker host:

```bash
bash docker/wiki-phase1/run.sh
```

Or manually dispatch **Wiki Phase 1 Compatibility** in GitHub Actions. Both are test-only and remove their disposable Compose volumes on exit.

## Commands and Results

| Command/check | Result |
|---|---|
| `git rev-parse HEAD` | **VERIFIED:** CRM `4ccd8dfc...` |
| Remote ref resolution for all three repositories | **VERIFIED:** pins listed above |
| Docker registry manifest resolution | **VERIFIED:** Python, MariaDB, Redis digests recorded above |
| `docker run --rm hello-world` in WSL | **VERIFIED:** Docker initially ran |
| Pull `frappe/bench:latest` | **FAILED:** WSL ext4 remounted read-only during layer extraction; this floating image is not used by the new harness |
| Native WSL runtime installation | **VERIFIED:** versions listed above |
| Native source preparation / Bench initialization | **FAILED:** WSL distribution crashed during Frappe source clone, before `bench init` |
| `cd frontend && yarn test:run` under Node 24.19.0 | **VERIFIED:** 8 files, 142 tests passed; AGENTS.md's 118 count is stale |
| Standalone CRM `yarn build` | **UNKNOWN:** remained CPU-active without output and was stopped; standalone checkout also lacks Bench's sibling `frappe/ui` link |
| Wiki root `yarn build` on Windows | **FAILED:** Windows could not spawn the extensionless `frontend/node_modules/.bin/tailwindcss`; this Linux-oriented step remains untested in the image |
| Wiki frontend-only Vite build | **UNKNOWN:** remained CPU-active without output and was stopped |
| Wiki E2E suite | **UNKNOWN:** requires the site that did not start |
| Compose/Bash/Python source syntax checks | **VERIFIED** for shell and Python parsing; full Compose execution **UNKNOWN** |

Dependency installation initially failed with `ENOSPC` because Yarn Classic cached native packages for many platforms. Recoverable Yarn cache and portable-runtime artifacts were cleaned, and the CRM unit suite was rerun successfully with a space-efficient temporary pnpm layout. No lockfile change from that local workaround is retained.

## Required Compatibility Checks

| Acceptance check | Status |
|---|---|
| Frappe starts | **UNKNOWN** |
| CRM installs | **UNKNOWN** |
| Wiki installs | **UNKNOWN** |
| `list-apps` contains `frappe`, `crm`, `wiki` | **UNKNOWN** |
| `/crm` and initial APIs load | **UNKNOWN** |
| `/wiki-app` and `/docs` load | **UNKNOWN** |
| CRM and Wiki assets coexist | **UNKNOWN** |
| Default Wiki Space exists | **UNKNOWN** |
| Wiki page create/edit/render | **UNKNOWN** |
| Same account/session works | **UNKNOWN** |
| Workers and scheduler start | **UNKNOWN** |
| Redis connections work | **UNKNOWN** |
| Socket.IO/realtime works | **UNKNOWN** |
| MariaDB migration succeeds and reruns | **UNKNOWN** |
| Existing CRM unit tests | **VERIFIED:** 142/142 passed |
| Relevant Wiki tests | **UNKNOWN:** only site-dependent E2E is exposed at this pin |

## Known Warnings and Workarounds

- **WARNING:** Frappe `ba36d039...` was selected from `develop` at spike start because both app manifests accept the v16/develop lane. Its actual compatibility is still **UNKNOWN** until installation passes.
- **WARNING:** the new harness is a purpose-built test image, not a production image or deployment design.
- **WARNING:** MariaDB 10.11.14 differs from the repository's old local 10.8 and migration CI's 10.6; that is intentional but must be validated by the migration test.
- **WARNING:** the existing v15 local Docker and build workflow remain unchanged and still contradict the `develop` app metadata.
- **Workaround:** raw Git SHAs are converted into local immutable tags because Bench's interface clones branch/tag refs.
- **Workaround:** the automated test is available as a manual GitHub Actions workflow because the local Linux runner is unhealthy.
- **No workaround accepted:** app installation, session, route, worker, migration, and combined build checks may not be inferred from metadata or unit tests.

## Files Changed

- [`WIKI_DISCOVERY.md`](./WIKI_DISCOVERY.md) — approved discovery retained as the Phase 1 basis.
- [`docker/wiki-phase1/Containerfile`](./docker/wiki-phase1/Containerfile) — exact-pin Bench build.
- [`docker/wiki-phase1/compose.yml`](./docker/wiki-phase1/compose.yml) — disposable one-site MariaDB/Redis/Bench topology.
- [`docker/wiki-phase1/entrypoint.sh`](./docker/wiki-phase1/entrypoint.sh) — site creation, app installation, migration, and startup.
- [`docker/wiki-phase1/verify.py`](./docker/wiki-phase1/verify.py) — pins, apps, routes, assets, shared session, and Wiki CRUD checks.
- [`docker/wiki-phase1/run.sh`](./docker/wiki-phase1/run.sh) — build/run/verify/migrate/cleanup entrypoint.
- [`.github/workflows/wiki-phase1.yml`](./.github/workflows/wiki-phase1.yml) — manual healthy-Linux execution path.
- [`WIKI_PHASE1_RESULT.md`](./WIKI_PHASE1_RESULT.md) — this result.

No CRM navigation, Wiki permissions, branding, Arabic/RTL behavior, attachment behavior, public documentation, entity linking, production deployment, or production database was changed.

## Phase 2 Recommendation

**Do not proceed to Phase 2.** First run the checked-in Phase 1 harness successfully on a healthy Linux Docker host and replace the **UNKNOWN** rows with observed results. If every required check passes, update this document to **PASS** or **PASS WITH CHANGES** and request explicit Phase 2 approval.

> Awaiting approval before Phase 2.
