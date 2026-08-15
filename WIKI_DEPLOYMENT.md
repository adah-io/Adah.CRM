# Adah Docs deployment runbook

This runbook is for a human maintainer after the pull request is reviewed and
approved. It deliberately contains placeholders and no production identifiers
or secrets. Nothing in this repository deploys Wiki automatically.

## Runtime decision

Wiki is an explicit new **v16 lane**, separate from the retained legacy
`stable-v15` workflow. The exact source/runtime inputs are:

| Component | Immutable input |
|---|---|
| Frappe | `ba36d03916ee05391bee0cf0f979ab97d552eede` |
| Wiki | `2e4e4f215368387c08553c3c59723c7a2e1bf306` |
| CRM | the approved merge commit; record its full SHA before building |
| Python base | Python 3.14.2 slim Bookworm digest in `Containerfile` |
| Node | 24.19.0 tarball with the checked SHA-256 |
| Yarn / Bench | 1.22.22 / 5.31.0 |

Adopting this image is a coordinated Frappe v15-to-v16 application-runtime
change. Do not replace a v15 image without completing the backup, restore, and
staging rehearsal below.

## Pre-deployment

1. Schedule a maintenance window and stop user writes through the normal
   maintenance mechanism.
2. Record the current image tag **and digest**, Compose configuration, installed
   apps (`bench --site <site> list-apps`), `bench version`, Python/Node versions,
   running containers, worker/scheduler state, and site configuration.
3. Confirm the approved CRM merge SHA and that CI's Wiki compatibility job passed.
4. Create and verify a database plus public/private-file backup:

   ```bash
   bench --site <site> backup --with-files --compress
   ```

5. Copy the backup outside the application host and perform a test restore on a
   disposable staging site. Record the exact restore commands used.
6. Verify free disk and RAM can hold the old image, new image, build layers,
   backup, database migration, Redis, workers, and asset build concurrently.
7. Confirm MariaDB and Redis versions are supported by the selected Frappe pin.

## Build

From the approved CRM commit, build the immutable runtime target:

```bash
docker build --pull --target runtime \
  --file docker/wiki-phase1/Containerfile \
  --build-arg FRAPPE_COMMIT=ba36d03916ee05391bee0cf0f979ab97d552eede \
  --build-arg CRM_COMMIT=<approved-full-crm-sha> \
  --build-arg WIKI_COMMIT=2e4e4f215368387c08553c3c59723c7a2e1bf306 \
  --tag <registry>/adah-crm:wiki-v16-<approved-full-crm-sha> .
```

Alternatively, manually dispatch **Build Wiki v16 Image** at the approved commit.
It publishes `ghcr.io/adah-io/adah.crm:wiki-v16-<full-sha>` and never moves a
`latest` or `stable` tag. Record the resulting registry digest and deploy by
digest (`image@sha256:...`), not by a mutable tag.

## Staging rehearsal

Restore a recent backup to an isolated site and use the new image for every
application process: web/backend, websocket, scheduler, short/long workers, and
any queue-specific workers. Keep MariaDB, Redis cache, Redis queue, site and
public/private file volumes persistent and shared exactly as required by the
existing deployment topology.

Before installing Wiki, verify `/crm`, login, one read operation, one safe test
write, workers, scheduler and Socket.IO. Then run:

```bash
bench --site <site> install-app wiki
bench --site <site> migrate
bench --site <site> migrate
```

The CRM `after_app_install`/`after_migrate` hooks idempotently configure `Adah
Docs` at `/docs`, disable contributions, and set `Sales User: Read` plus `Sales
Manager: Write`. Existing CRM users in either role receive native `Wiki User`.

Run the complete acceptance checklist below. Rehearse rollback, including a
database/files restore, before approving production deployment.

## Deploy

1. Pull the recorded image digest on every application node.
2. Update Compose so all Frappe application services use that same digest. Do
   not run `bench get-app`, patch files inside containers, or use floating refs.
3. Recreate application containers using the deployment's normal controlled
   procedure. Do not remove database, Redis, site, public-file, or private-file
   volumes.
4. Verify CRM and infrastructure health before installing Wiki.
5. Install and migrate exactly once through a single backend container:

   ```bash
   bench --site <site> install-app wiki
   bench --site <site> migrate
   ```

6. Recreate/restart all application processes after migration, then disable
   maintenance mode only after verification passes.

## Verification

- `/crm` loads and existing CRM read/write flows work.
- `/wiki-app` and `/docs` load their own `/assets/wiki/` assets; CRM assets still load.
- One existing login session works across CRM, reader, and editor.
- Guest cannot read `/docs`, Wiki APIs/search, or a copied private attachment URL.
- Sales User can read but cannot create/update; contributions remain disabled.
- Sales Manager can create, edit, publish, render, and upload an allowed asset.
- Administrator/System Manager retains native full Wiki administration.
- Uploaded editor assets use `/private/files/`; SVG/HTML/script uploads are rejected.
- Raw HTML, script/event-handler, `javascript:`/data URLs, SVG markup, malformed
  HTML and embeds are rejected; fenced HTML examples remain escaped and readable.
- Arabic title/content stores and renders. Full RTL layout is intentionally deferred.
- MariaDB is healthy; Redis cache/queue respond; workers consume both queues;
  scheduler is enabled and advancing; Socket.IO connects without repeated errors.
- `bench --site <site> migrate` succeeds a second time.
- Logs contain no repeated permission, migration, asset, queue, or realtime errors.

## Security boundary and limitations

The pinned upstream Wiki renderer permits raw HTML. Adah CRM therefore rejects
raw HTML and dangerous Markdown URL schemes before every `Wiki Document` save;
this is a strict policy guard, not a sanitizer. HTML examples are supported only
inside inline/fenced code. Removing this guard would re-open a stored-XSS risk.

Wiki's upstream editor requests public uploads. CRM overrides only that upstream
whitelisted method, forces private storage, attaches each file to the protected
Wiki Space so Frappe's normal document permission chain controls downloads, and
uses an image/PDF/video extension allowlist. Other File uploads are unaffected.

The upstream Wiki dependency remains unmodified and commit-pinned. Full RTL UI,
public documentation, generic attachments, contribution workflows, and entity
links are outside V1.

## Rollback

If failure occurs **before** `install-app wiki`, redeploy the recorded previous
image digest and recreate application processes.

After Wiki installation or any v16 migration, do not assume an image-only rollback
is schema-compatible. Re-enable maintenance mode, stop application workers/web,
restore the pre-deployment database and both public/private file backups using the
rehearsed commands, restore the previous image digest/Compose configuration, then
start services and verify CRM, workers, scheduler, Socket.IO, MariaDB and Redis.

Keep the failed image, logs and migration output for diagnosis. Do not run
`uninstall-app wiki` as a substitute for restoring the known-good backup.
