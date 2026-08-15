# Wiki compatibility harness

This disposable Linux Docker environment builds one Bench image containing
exact Frappe, CRM, and upstream Wiki commits, installs both apps on one site,
and exercises routes, assets, shared authentication, role access, Wiki CRUD,
Arabic content, private attachments, stored-XSS rejection, workers, Socket.IO,
MariaDB, Redis, and a second migration.

Run from the repository root:

```bash
bash docker/wiki-phase1/run.sh
```

`run.sh` uses the checked-out CRM commit by default. Override `CRM_COMMIT` only
with an immutable commit reachable from `adah-io/Adah.CRM`. The Compose project
and its disposable volumes are removed on exit. It does not connect to any
external site or production service.

The `runtime` target in `Containerfile` is the production image input. The
`phase1` target only adds this harness's entrypoint and verifier.
