# Frappe Wiki Integration Discovery

**Discovery date:** 2026-08-15
**Adah CRM target:** `develop` at `4ccd8dfc166c2e7203aba5aca57b1545700c966b`
**Upstream Wiki inspected:** `develop` at `2e4e4f215368387c08553c3c59723c7a2e1bf306` (2026-08-14)
**Recommendation:** **APPROVE WITH CONDITIONS**
**Scope:** Technical and product discovery only. No Wiki installation or application/deployment change is included.

## Status vocabulary

- **Verified** — established from the referenced source at the revisions above.
- **Inference** — a reasoned conclusion that still needs an integration environment test.
- **Unknown** — the repositories do not prove the answer.
- **Decision Required** — a product or operational choice must be approved before implementation.

## 1. Executive Summary

**Verified:** Frappe Wiki is a strong functional match for Adah's internal knowledge-base use case. The current Wiki has a separate Vue 3/frappe-ui authoring SPA, a server-rendered reader, hierarchical documents, Markdown/rich editing, media, SQLite full-text search, per-space role access, change requests, approval/merge, and revision storage. It uses the normal Frappe `User`, session, Role, database, File, worker, scheduler, and site model rather than a second identity system. Evidence: [Wiki hooks](https://github.com/frappe/wiki/blob/2e4e4f215368387c08553c3c59723c7a2e1bf306/wiki/hooks.py), [permissions](https://github.com/frappe/wiki/blob/2e4e4f215368387c08553c3c59723c7a2e1bf306/wiki/permissions.py), [Wiki router](https://github.com/frappe/wiki/blob/2e4e4f215368387c08553c3c59723c7a2e1bf306/frontend/src/router.js), and the v3 DocTypes under `wiki/frappe_wiki/doctype/`.

**Recommendation:** install Wiki as another app on the **same Frappe site**, keep Wiki upstream and commit-pinned, add one CRM `Docs` navigation entry, and use the Wiki's own reader/editor routes. Do not embed the entire Wiki SPA inside the CRM SPA and do not build a custom wiki.

```text
One immutable application image
├── frappe (compatible v16 commit)
├── crm (Adah develop, pinned)
└── wiki (upstream develop commit, pinned)

One Frappe site / database / user directory
├── /crm                         CRM Vue SPA
├── /docs/...                    Wiki reader (configured space route)
└── /wiki-app/...                Wiki authoring Vue SPA
```

**Verified compatibility at metadata level:** both CRM and Wiki declare Frappe `>=16.0.0-dev,<=17.0.0-dev`. Wiki and current Frappe `develop` require Python 3.14. CRM itself only declares Python `>=3.10`, but its Frappe dependency determines the effective runtime. Evidence: local [`pyproject.toml`](./pyproject.toml) and [Wiki `pyproject.toml`](https://github.com/frappe/wiki/blob/2e4e4f215368387c08553c3c59723c7a2e1bf306/pyproject.toml). Current Frappe `develop` also declares Python `>=3.14,<3.15`: [Frappe `pyproject.toml`](https://github.com/frappe/frappe/blob/develop/pyproject.toml).

**Unknown:** runtime compatibility is not proven because this discovery did not install the apps. The repository's development Docker script still creates a Frappe `version-15` bench, contradicting the v16 application metadata: [`docker/init.sh`](./docker/init.sh). The actual production image manifest and deployed `bench version` are not present in this repository.

**Candidate version strategy:** use Wiki `develop@2e4e4f215368387c08553c3c59723c7a2e1bf306` only as the integration-test candidate, pinned by immutable commit rather than a floating branch. Prefer a later signed/tagged upstream release that contains this commit's access/search/XSS-related fixes if one exists when implementation begins. Do **not** select `main` (Wiki's default branch is `develop`, and there is no current `main`) or the old `master`. The `v3.0.0` tag (`0a6025159289bcdaae26d727ada34764370ac765`, 2026-07-28) has matching v16/Python 3.14 metadata but predates several relevant fixes on `develop`, so it is not the recommended production pin without a security backport review.

**Blocking conditions before production implementation:**

1. Prove the exact Frappe, Python 3.14, Node/Yarn, CRM, and Wiki pins in the same immutable image and on a restored copy of an Adah site.
2. Resolve attachment privacy. The current editor calls `useFileUpload(..., { private: false })`, so uploaded images/video/PDFs are public `/files` assets even when the Wiki Space is role-restricted. Page permissions do not make those URLs private. Evidence: [WikiEditor upload path](https://github.com/frappe/wiki/blob/2e4e4f215368387c08553c3c59723c7a2e1bf306/frontend/src/components/WikiEditor.vue) and [upload endpoint](https://github.com/frappe/wiki/blob/2e4e4f215368387c08553c3c59723c7a2e1bf306/wiki/api/__init__.py).
3. Run an adversarial content-security test. The reader renders generated HTML with Jinja `safe`, and the Markdown renderer enables raw HTML. The framework may sanitize persisted values, but this discovery did not execute the full save/render path. Evidence: [Markdown renderer](https://github.com/frappe/wiki/blob/2e4e4f215368387c08553c3c59723c7a2e1bf306/wiki/wiki/markdown.py) and [reader template](https://github.com/frappe/wiki/blob/2e4e4f215368387c08553c3c59723c7a2e1bf306/wiki/templates/wiki/document.html).
4. Perform Arabic/RTL acceptance testing. Arabic storage is technically plausible, but the inspected first-party Wiki UI has no explicit RTL layout implementation.

## 2. Current Adah CRM Architecture Relevant to Wiki

### Repository and upstream relationship

**Verified:** at discovery time, `adah-io/Adah.CRM:develop` and `frappe/crm:develop` resolve to the same commit, `4ccd8dfc166c2e7203aba5aca57b1545700c966b`. The Adah repository is a GitHub fork of `frappe/crm`. Therefore there is no current source divergence to account for at the target commit.

**Verified:** the repository nevertheless contains material CRM behavior relevant to integration, including form scripting, custom FieldLayout behavior, domain enrichment, user hierarchy, custom role checks, and a bespoke CRM SPA. These are documented in [`AGENTS.md`](./AGENTS.md), [`.pi/PLAN.md`](./.pi/PLAN.md), [`.pi/SPEC.md`](./.pi/SPEC.md), and [`.pi/ARCHIVE.md`](./.pi/ARCHIVE.md). None names Wiki DocTypes or routes, so no direct schema collision was found.

### Backend and site model

| Area | Finding | Status / evidence |
|---|---|---|
| Framework | Frappe app named `crm`; Frappe dependency range is v16 development through before v17 development. | **Verified:** [`pyproject.toml`](./pyproject.toml) |
| Python | CRM declares `>=3.10`; effective current Frappe v16 `develop` requires Python 3.14. | **Verified:** local and Frappe/Wiki `pyproject.toml` |
| Authentication | Normal Frappe cookie session; unauthenticated `/crm` navigation redirects to `/login?redirect-to=/crm`. | **Verified:** [`frontend/src/stores/session.js`](./frontend/src/stores/session.js), [`frontend/src/router.js`](./frontend/src/router.js) |
| CRM users | CRM recognizes `System Manager`, `Sales Manager`, and `Sales User`; the SPA rejects logged-in users without a CRM role. | **Verified:** [`crm/api/session.py`](./crm/api/session.py), [`frontend/src/router.js`](./frontend/src/router.js) |
| Hooks | CRM adds its app to the app screen, installs records/custom fields, adds permission hooks, scheduled jobs, and a `/crm/*` catch-all route. | **Verified:** [`crm/hooks.py`](./crm/hooks.py), [`crm/install.py`](./crm/install.py) |
| Database/site | Standard Frappe DocTypes and one site database; app tables are created when an app is installed on a site. | **Verified:** [Frappe Apps documentation](https://docs.frappe.io/framework/user/en/basics/apps) |
| Background services | CRM already expects Redis, Socket.IO, scheduler and workers for events, notifications, and scheduled jobs. | **Verified:** [`crm/hooks.py`](./crm/hooks.py), [`docker/docker-compose.yml`](./docker/docker-compose.yml) |

### Frontend and routing

**Verified:** CRM is a Vue 3 + Pinia + frappe-ui SPA built by Vite. Its history base is `/crm`; server routing maps `/crm/<path>` back to the CRM entry page. Assets build under `/assets/crm/frontend/`. Evidence: [`frontend/src/main.js`](./frontend/src/main.js), [`frontend/src/router.js`](./frontend/src/router.js), [`frontend/package.json`](./frontend/package.json), and [`crm/hooks.py`](./crm/hooks.py).

**Verified:** the main navigation links are a local `links` array in [`frontend/src/components/Layouts/AppSidebar.vue`](./frontend/src/components/Layouts/AppSidebar.vue), then combined with public and pinned CRM views. An initial Wiki integration therefore needs an intentional CRM navigation change; it is not automatically provided by installing another app.

**Verified:** CRM currently uses `frappe-ui@1.0.0-beta.29`; inspected Wiki uses `frappe-ui@1.0.0-beta.25`. Both use Vue 3.5 and TipTap 3.26, but the bundles are independent. This reduces runtime collision risk while leaving visual-version drift. Evidence: [`frontend/package.json`](./frontend/package.json) and [Wiki frontend package](https://github.com/frappe/wiki/blob/2e4e4f215368387c08553c3c59723c7a2e1bf306/frontend/package.json).

### Build and deployment evidence

**Verified:** CRM's repository build uses `yarn build` and copies the Vite entry to `crm/www/crm.html`. Generated frontend assets are ignored from Git. Evidence: [`package.json`](./package.json), [`frontend/package.json`](./frontend/package.json), and [`.gitignore`](./.gitignore).

**Verified:** the checked-in Docker Compose is a development setup. It mounts the repository, uses `frappe/bench:latest`, and runs a script that initializes `version-15`, downloads CRM `main`, and installs it. It is not an immutable multi-app production definition. Evidence: [`docker/docker-compose.yml`](./docker/docker-compose.yml) and [`docker/init.sh`](./docker/init.sh).

**Unknown:** the actual production `apps.json`, image build file, persistent volume map, Frappe commit, Python version, and site list are external to this repository. They must be collected before Phase 1.

## 3. Frappe Wiki Architecture

### Application surfaces

**Verified:** Wiki has two distinct product surfaces:

- `/wiki-app/...` — a Vue 3 + Pinia + frappe-ui authoring SPA with history base `/wiki-app`; unauthenticated users are sent to the common Frappe login.
- `/<space-route>/...` — server-rendered/Jinja reader pages with Alpine-enhanced navigation, sidebar, breadcrumbs, table of contents, search, and responsive behavior. A fresh install creates a space routed at `/docs`.

Evidence: [Wiki router](https://github.com/frappe/wiki/blob/2e4e4f215368387c08553c3c59723c7a2e1bf306/frontend/src/router.js), [Wiki hooks](https://github.com/frappe/wiki/blob/2e4e4f215368387c08553c3c59723c7a2e1bf306/wiki/hooks.py), [install hook](https://github.com/frappe/wiki/blob/2e4e4f215368387c08553c3c59723c7a2e1bf306/wiki/install.py), and [Wiki Document renderer](https://github.com/frappe/wiki/blob/2e4e4f215368387c08553c3c59723c7a2e1bf306/wiki/frappe_wiki/doctype/wiki_document/wiki_document.py).

### Data model

The active v3 model is:

```text
Wiki Space
├── roles[] -> Wiki Space Role -> Role + Read/Write level
├── root_group -> Wiki Document (tree root)
├── main_revision -> Wiki Revision
└── Wiki Documents (nested set)
    ├── title, slug, route, Markdown content, is_published
    ├── group/tab/external-link flags
    └── optional meta image -> File

Wiki Change Request
├── base/head/merge -> Wiki Revision
├── status: Draft → In Review → Approved → Merged
└── conflicts -> Wiki Merge Conflict

Wiki Revision
└── Wiki Revision Item[]
    └── content_blob -> Wiki Content Blob (deduplicated Markdown)

Uploads -> standard Frappe File records + public/private site files
```

**Verified:** `Wiki Document` is a Frappe nested-set tree and stores Markdown in a Code field. It tracks publication, route, external links, tabs, and meta data. Revision snapshots are split into `Wiki Revision`, `Wiki Revision Item`, and hash-addressed `Wiki Content Blob`. `Wiki Change Request` and `Wiki Merge Conflict` implement review and three-way merge. Evidence: the JSON/controllers under [v3 DocTypes](https://github.com/frappe/wiki/tree/2e4e4f215368387c08553c3c59723c7a2e1bf306/wiki/frappe_wiki/doctype).

**Verified:** old `Wiki Page`, `Wiki Page Patch`, `Wiki Page Revision`, `Wiki Sidebar`, and related v2 records remain in the source for migration/legacy compatibility. `Wiki Page.validate()` explicitly says it is deprecated and should migrate to `Wiki Document`. New integration work must use v3 concepts. Evidence: [deprecated Wiki Page controller](https://github.com/frappe/wiki/blob/2e4e4f215368387c08553c3c59723c7a2e1bf306/wiki/wiki/doctype/wiki_page/wiki_page.py) and [patch list](https://github.com/frappe/wiki/blob/2e4e4f215368387c08553c3c59723c7a2e1bf306/wiki/patches.txt).

**Verified:** no CRM DocType, module, route, or asset-name collision was found. CRM uses `/crm` and `/assets/crm`; Wiki uses `/wiki-app`, configurable reader routes such as `/docs`, and `/assets/wiki`.

## 4. Compatibility Matrix

| Component | Adah CRM target | Wiki candidate | Assessment |
|---|---|---|---|
| Frappe | Declares `>=16.0.0-dev,<=17.0.0-dev` | Same declared range | **Verified metadata match; runtime unverified** |
| Python | CRM says `>=3.10`; current Frappe `develop` effectively requires `>=3.14,<3.15` | Wiki says `>=3.14` | **Condition:** production must move as one tested v16/Python 3.14 stack |
| Node | CRM frontend requires `^20.19.0 || >=22.12.0` | Wiki has no engine declaration; dependencies/build need modern Node | **Unknown:** prove one Node version in image build |
| JS package manager | Yarn scripts/locks | Yarn scripts/locks | **Verified approach match** |
| Vue | 3.5.13 | 3.5.13 | **Verified** |
| frappe-ui | beta.29 | beta.25 | **Compatible by isolation; visual/API drift risk** |
| TipTap | 3.26.x | 3.26.x | **Verified broad match** |
| Python dependencies | CRM: Twilio, requests, tldextract | Wiki: `markdown-it-py>=3.0`, `mdit-py-plugins>=0.4` | **Verified:** add at image build; loose Wiki pins should be lock-tested |
| Database | Standard Frappe-supported site DB; dev Compose uses MariaDB 10.8 | Standard DocTypes and Frappe query APIs | **Inference:** compatible; migration test required |
| Redis/workers | Already expected by CRM/Frappe | Framework search queue, cache, realtime and normal jobs use existing services | **Verified no separate RedisSearch service required for active v3 search** |
| Assets | `/assets/crm/frontend/` | `/assets/wiki/frontend/` plus generated Wiki CSS/theme | **Verified isolated paths; both must build into image** |
| Wiki release | N/A | `v3.0.0` exists but predates important `develop` fixes | **Do not blindly pin v3.0.0** |

**Explicit compatible-version strategy:**

1. Pin all three repositories by commit SHA in the image build, not floating branch names.
2. Start the compatibility spike with CRM `4ccd8dfc...`, Wiki `2e4e4f2...`, and the exact Frappe commit used by the production v16 image.
3. Require Python 3.14 and one supported Node version across the builder.
4. Generate a dependency lock/SBOM and run both apps' tests on the same site image.
5. Before production, prefer the first upstream Wiki release whose history includes `2e4e4f2...` (or a later reviewed commit). If no such release exists, document the commit pin as a controlled exception and review upstream changes monthly.

**Unknown:** compatibility cannot be declared proven until the spike completes. This is why the recommendation is conditional.

## 5. Integration Options

### Option A — Wiki as another app on the same site

| Dimension | Assessment |
|---|---|
| Authentication/users | Native shared Frappe cookies, sessions, `User` rows, roles, password policy, OAuth/2FA. No second account. |
| Database | Same site DB; separate `Wiki *` tables. Standard site migration/backup lifecycle. |
| Permissions | CRM roles can be selected directly in each Wiki Space's Read/Write rows. |
| URLs/assets | Separate `/crm`, `/wiki-app`, configurable reader routes, `/assets/crm`, `/assets/wiki`. |
| Deployment | One image must contain and build both apps; install Wiki once per target site, then migrate on updates. |
| Isolation | Separate frontend entry points and namespaces, but shared framework/runtime means upgrades must be tested together. |
| UX | A CRM Docs entry can navigate to `/docs`; Wiki remains visually related through frappe-ui and branding but not inside the CRM shell. |

**Assessment:** **Recommended.** Lowest identity and operational complexity, and it matches Frappe's app/site model.

### Option B — separate Frappe site/application

**Verified:** a separate site means a separate database and separate `User` rows/session cookie scope. Shared accounts do not happen automatically.

**Inference:** meeting “no second account” would require SSO/OAuth configuration, account lifecycle synchronization, role mapping, cross-site links, separate backups/migrations, and likely a separate domain. It improves blast-radius isolation and independent upgrades, but adds material operations and UX friction.

**Assessment:** reject for V1. Reconsider only if Wiki's runtime cannot coexist with the production CRM/Frappe pin, or if public documentation needs a deliberately isolated security boundary.

### Option C — build documentation directly inside CRM

**Inference:** this duplicates document trees, routing, editor/media, search, permissions, revisioning, approval, reader rendering, mobile behavior, migration, and maintenance already present in Wiki. It creates the tightest coupling to the CRM fork and the largest long-term cost.

**Assessment:** reject unless the compatibility spike fails or attachment/access requirements cannot be safely achieved without a large Wiki fork.

## 6. Recommended Architecture

**Decision:** Option A, same-site sibling app.

- Keep `frappe/wiki` untouched as an upstream dependency wherever possible.
- Put the exact Wiki and Frappe commits in the production image's application manifest/build inputs.
- Install `wiki` on the same site as `crm`; do not copy Wiki code into this repository.
- Configure an internal Wiki Space at route `docs`, marked published for rendering but with Read/Write role rows that exclude `Guest`.
- Map `Sales User` -> Read and `Sales Manager` -> Write. `Administrator`, `System Manager`, and/or `Wiki Manager` retain administration. Disable contributions for read-only users in V1 unless Adah explicitly wants suggestions.
- Add a CRM `Docs` link that performs a normal same-tab navigation to `/docs` (or the selected landing page). Let the reader's Edit action navigate authorized writers to `/wiki-app`.
- Keep public documentation and CRM-record relationships out of V1.

**Why not embed Wiki inside CRM:** two independent history routers, shells, sidebars, themes, mobile layouts, CSP/frame behavior, and asset lifecycles would have to be reconciled. A full-page route transition is simpler, deep-linkable, accessible, and preserves browser back/forward behavior. Visual consistency is realistic through Wiki Space branding and shared frappe-ui language; pixel-identical CRM chrome is not a V1 requirement.

## 7. Authentication and Users

**Verified:** both SPAs read the normal Frappe `user_id` cookie and redirect guests to the normal `/login` endpoint. Installing Wiki on the same site therefore uses the existing user account and session. Evidence: [`frontend/src/stores/session.js`](./frontend/src/stores/session.js), [Wiki session store](https://github.com/frappe/wiki/blob/2e4e4f215368387c08553c3c59723c7a2e1bf306/frontend/src/stores/session.js), and [Frappe users/permissions](https://docs.frappe.io/framework/user/en/basics/users-and-permissions).

**Verified:** Wiki has no separate person/account DocType. `get_user_info()` loads the current Frappe `User` and its roles. Evidence: [Wiki API](https://github.com/frappe/wiki/blob/2e4e4f215368387c08553c3c59723c7a2e1bf306/wiki/api/__init__.py).

**Verified:** Wiki's migration assigns `Wiki User` to existing enabled users, and a `User.after_insert` hook adds `Wiki User` to future users. Evidence: [assignment patch](https://github.com/frappe/wiki/blob/2e4e4f215368387c08553c3c59723c7a2e1bf306/wiki/wiki/doctype/wiki_space/patches/v3/assign_wiki_user_to_active_users.py), [Wiki hooks](https://github.com/frappe/wiki/blob/2e4e4f215368387c08553c3c59723c7a2e1bf306/wiki/hooks.py), and [user helper](https://github.com/frappe/wiki/blob/2e4e4f215368387c08553c3c59723c7a2e1bf306/wiki/utils.py).

**Concern:** the migration gives the role to **all enabled users**, not only CRM users, while the CRM SPA only accepts `System Manager`, `Sales Manager`, and `Sales User`. Space role rows must therefore be the authoritative access gate; do not rely on `Wiki User` alone.

**Website/System Users:** Frappe's `All` automatic role applies to registered users including Website Users; `Desk User` applies only to System Users. Wiki's reader permission helper reasons over normal roles and can technically admit either user type. The authoring SPA and Wiki DocType permissions should be tested with Adah's actual invited-user type. **Unknown:** the current repository does not prove that all CRM users are System Users in production.

## 8. Permissions

### Native behavior

**Verified:** access is primarily per `Wiki Space` using child rows of `(Role, Read|Write)`:

- Manager roles (`Administrator`, `System Manager`, `Wiki Manager`) always have full access.
- Any matching Read or Write role can read.
- A matching Write role can create/edit/delete and approve/merge; Write implies Read.
- A space with no role rows is readable by any logged-in user, not Guest.
- `Guest` in a space role row makes that space publicly readable.
- Read users can propose Change Requests when `allow_contributions` is enabled; Write users can always contribute and can review/merge.
- Git-synced spaces are read-only inside Wiki.

Evidence: [Wiki permission hooks](https://github.com/frappe/wiki/blob/2e4e4f215368387c08553c3c59723c7a2e1bf306/wiki/permissions.py) and [change request controller](https://github.com/frappe/wiki/blob/2e4e4f215368387c08553c3c59723c7a2e1bf306/wiki/frappe_wiki/doctype/wiki_change_request/wiki_change_request.py).

### Proposed mapping

| Adah persona | Frappe/Wiki configuration | Result |
|---|---|---|
| Administrator | Built-in Administrator / System Manager (optionally Wiki Manager) | Full Wiki and space administration |
| Sales Manager | Add `Sales Manager` as Write on the internal space | Read, create/edit through CR, review, approve and merge/publish |
| Sales User | Add `Sales User` as Read; set `allow_contributions = 0` for strict read-only V1 | Read only |

**Verified:** existing CRM roles can be used directly; no source mapping layer is required.

**Gap:** Wiki Write is a broad editor/publisher tier. It does not natively express “can edit but cannot approve/merge” within one space. If Adah wants Sales Managers to author but a smaller group to publish, use a distinct existing/new Frappe role as the Write role and keep Sales Manager at Read with contributions enabled. That provides authorship via CR and approval by the narrower Write role. **Decision Required.**

**Gap:** page ownership is stored in standard Frappe ownership/audit fields and CR authorship, but access is space-level, not owner-scoped or page-level.

## 9. Internal/Public Access

| Level | Supported behavior | Status |
|---|---|---|
| Global | No single “all Wiki internal” switch found. App SPA requires login; reader access is evaluated by each space. | **Verified** |
| Per space | Role rows control readers/writers; no rows means all logged-in; `Guest` makes public; `is_published` controls whether the space renders. | **Verified** |
| Per category/tree group | No independent ACL on a group/category inside a space. Use separate spaces for different audiences. | **Verified** |
| Per page | `is_published` controls live visibility; no per-page role ACL. | **Verified** |

**Important semantic distinction:** for internal content, a page and its space still need to be “published” so authorized readers can render them. “Published” is not synonymous with public; the space role check still gates the request.

**Recommended V1 configuration:** one role-restricted published space, explicit `Sales User: Read` and `Sales Manager: Write`, no `Guest`, contributions off for Sales User, and no public space.

**Critical attachment exception:** the text/page ACL does not protect editor uploads currently created as public files. Sensitive attachment support is not approved until the blocking privacy condition is resolved and tested.

## 10. Product UX Integration

### Navigation and routing

**Verified:** CRM's sidebar is code-defined and currently emits Vue Router targets. A future Docs item can use a normal anchor/full-page navigation to `/docs`; a local CRM catch-all route should not attempt to render Wiki. Evidence: [`frontend/src/components/Layouts/AppSidebar.vue`](./frontend/src/components/Layouts/AppSidebar.vue) and [`frontend/src/router.js`](./frontend/src/router.js).

**Verified:** Wiki provides its own nested editor routes, reader sidebar/tree, breadcrumbs, prior/next links, page anchors, deep links, and browser history behavior. Evidence: [Wiki router](https://github.com/frappe/wiki/blob/2e4e4f215368387c08553c3c59723c7a2e1bf306/frontend/src/router.js), [reader template](https://github.com/frappe/wiki/blob/2e4e4f215368387c08553c3c59723c7a2e1bf306/wiki/templates/wiki/document.html), and [Wiki Document controller](https://github.com/frappe/wiki/blob/2e4e4f215368387c08553c3c59723c7a2e1bf306/wiki/frappe_wiki/doctype/wiki_document/wiki_document.py).

### Recommended V1 behavior

1. CRM sidebar shows `Docs` for users intended to have documentation access.
2. Clicking it navigates in the same tab to the configured internal landing page (`/docs` or `/docs/sales-playbook`).
3. Wiki's reader owns documentation navigation and mobile UI.
4. Authorized contributors use the reader's Edit action to enter `/wiki-app/spaces/...`.
5. Browser back returns to CRM; copied deep links work directly after login.

**Decision Required:** label (`Docs` vs `Knowledge Base`), landing route, same-tab vs new-tab (same-tab recommended), and whether the link is hidden client-side for users without the target space role. Server-side Wiki permissions remain authoritative.

### Visual consistency and mobile

**Inference:** visual consistency is achievable but not automatic. Both products use frappe-ui concepts, semantic tokens, Vue, responsive shells, and dark mode. Wiki Space supports light/dark logos, favicon, app-switcher logo, navbar items, and names. The products use different frappe-ui versions and distinct layouts, so some transition is visible.

**Verified:** Wiki has responsive mobile components and E2E tests such as `mobile-view.spec.ts` and `spa-editor.mobile.spec.ts`. **Unknown:** usability on Adah's supported devices and Arabic keyboards has not been validated.

## 11. Wiki Feature Assessment

Legend: ✓ primary classification; “partial” is explained in Notes.

| Capability | Native | Requires configuration | Requires customization | Not supported | Notes |
|---|:---:|:---:|:---:|:---:|---|
| Create page | ✓ | | | | Created in a change request/tree |
| Edit page | ✓ | | | | TipTap rich editor backed by Markdown |
| Rich text / Markdown | ✓ | | | | Headings, lists, tables, code, callouts, embeds, Mermaid, etc. |
| Images | ✓ | | | | Upload/paste/drop; privacy condition applies |
| File attachments | | | ✓ | | Native image/video/PDF embeds; generic attachment UX and protected files need work |
| Nested documentation | ✓ | | | | `Wiki Document` nested set, groups and optional tabs |
| Search | ✓ | ✓ | | | Frappe SQLite search must be indexed; access-filtered results |
| Table of contents | ✓ | ✓ | | | Global setting plus generated h2/h3 headings; editor TOC exists |
| Revision history | ✓ | | ✓ | | Revision data is native; end-user history UI is not on inspected `develop` (open issue/feature branch) |
| Draft/publish | ✓ | ✓ | | | CR drafts + document/space publication flags |
| Approval workflow | ✓ | ✓ | | | Submit, approve/request changes/reject, explicit merge, conflict resolution |
| Internal/private docs | | ✓ | | | Per-space roles; attachments are an exception |
| Public docs | | ✓ | | | Add Guest role to a published space |
| Permissions | ✓ | ✓ | | | Per-space Read/Write roles; no per-page ACL |
| Arabic content | ✓ | | | | Unicode storage/rendering technically supported; acceptance test required |
| RTL | | | ✓ | | No explicit first-party RTL layout rules found |
| Mobile usability | ✓ | | | | Responsive implementation/tests exist; Adah QA required |
| Links between pages | ✓ | | | | Markdown links and link editor; routes/deep links |
| Navigation/sidebar | ✓ | ✓ | | | Tree, groups, tabs, space switcher and branding |

## 12. Arabic/RTL Assessment

| Concern | Finding |
|---|---|
| Arabic titles/content | **Technically possible:** Frappe/MariaDB use Unicode and Wiki fields are normal Data/Code fields. No ASCII validation was found. Runtime test still required. |
| Arabic slugs | **Unknown/unverified:** Wiki derives segments using Frappe `cleanup_page_name()` and also allows route editing. Test Arabic-only, mixed, duplicate and percent-encoded URLs before approval. Evidence: [slug/route code](https://github.com/frappe/wiki/blob/2e4e4f215368387c08553c3c59723c7a2e1bf306/wiki/frappe_wiki/doctype/wiki_document/wiki_document.py). |
| Editor RTL | **Not implemented explicitly:** no first-party `dir="rtl"`, RTL mode, or logical layout switch was found in inspected Wiki frontend/templates. Browser bidi may display Arabic text, but cursor, selection, lists, tables and mixed text need QA. |
| Reader RTL | **Requires customization:** the layout is visually LTR (left sidebar, right TOC, left/right arrow assumptions). Some CSS uses logical properties, but there is no overall RTL mode. |
| Fonts | **Unknown:** bundled Inter CSS declares broad Unicode ranges, but actual Arabic glyph/fallback quality must be inspected on supported browsers. |
| Mixed Arabic/English | **Unknown:** browser bidi should help, but punctuation, inline code, links, tables and editor selection must be tested. |
| Arabic search | **Technically possible, unverified:** SQLite FTS5 uses `unicode61`; there is no Arabic stemming/morphology. Exact word/prefix behavior, normalization, alef/hamza variants and diacritics require a corpus test. |

**V1 recommendation:** Arabic content may enter pilot scope; full RTL parity must be an explicit acceptance decision. If full RTL is mandatory for V1, budget an integration/customization phase rather than treating it as configuration.

## 13. Search

**Verified active architecture:** Wiki registers `WikiSQLiteSearch` through the Frappe `sqlite_search` hook. It indexes published, non-group, non-external `Wiki Document` title/content/route/space metadata in `wiki_search.db` under the site's index storage. It uses SQLite FTS5 with the `unicode61 remove_diacritics 2` tokenizer. Evidence: [Wiki hooks](https://github.com/frappe/wiki/blob/2e4e4f215368387c08553c3c59723c7a2e1bf306/wiki/hooks.py) and [Wiki SQLite search](https://github.com/frappe/wiki/blob/2e4e4f215368387c08553c3c59723c7a2e1bf306/wiki/frappe_wiki/doctype/wiki_document/wiki_sqlite_search.py).

**Verified permission behavior:** the search endpoint may be called as Guest, but it post-filters hits by published-space state and `can_read_space()`. A recent code fix specifically hides unpublished results. Evidence: [search endpoint](https://github.com/frappe/wiki/blob/2e4e4f215368387c08553c3c59723c7a2e1bf306/wiki/frappe_wiki/doctype/wiki_document/search.py).

**Verified operational behavior:** normal document updates enter the framework search queue; merge fast paths explicitly queue reindexing. Unpublishing removes a document synchronously so stale results do not remain while the framework's periodic queue drains. This uses the normal Frappe scheduler/worker/Redis queue infrastructure. It does **not** require Elasticsearch, OpenSearch, Algolia, or a RedisSearch module.

**Clarification:** the repository still contains a legacy `wiki/search.py` using RedisSearch, and the README still mentions RedisSearch. The active v3 hook and frontend endpoint use Frappe SQLite search; the README is stale for this path.

**Backup implication:** the SQLite index is derived state. Normal DB + file backup preserves source content, but the index should be rebuilt/verified after restore rather than treated as authoritative data.

## 14. Deployment

### Immutable image approach

**Recommended future build input (conceptual, not executed):**

```json
[
  {
    "url": "https://github.com/adah-io/Adah.CRM",
    "branch": "develop",
    "commit": "4ccd8dfc166c2e7203aba5aca57b1545700c966b"
  },
  {
    "url": "https://github.com/frappe/wiki",
    "branch": "develop",
    "commit": "2e4e4f215368387c08553c3c59723c7a2e1bf306"
  }
]
```

The exact schema depends on Adah's external image pipeline; common `frappe_docker` `apps.json` accepts repository/branch inputs but commit pinning may require a pinned branch/tag or checkout step. **Decision Required:** identify the actual production builder and encode immutable SHAs in its supported way.

**Verified:** Wiki's root build runs Tailwind theme generation and then its Vite build; generated Wiki frontend/CSS output is not tracked in Git. Merely installing Python requirements is insufficient. Evidence: [Wiki root package](https://github.com/frappe/wiki/blob/2e4e4f215368387c08553c3c59723c7a2e1bf306/package.json), [Wiki frontend package](https://github.com/frappe/wiki/blob/2e4e4f215368387c08553c3c59723c7a2e1bf306/frontend/package.json), and [asset bundling documentation](https://docs.frappe.io/framework/user/en/basics/asset-bundling).

### Eventual deployment sequence

For a new app on an existing site, after approval:

1. Build and scan a new image containing pinned Frappe, CRM and Wiki plus all Python/Node dependencies and both apps' production assets.
2. Restore/snapshot production into staging and run a preflight (`bench version`, Python/Node versions, `list-apps`, DB engine, disk space).
3. Back up database, site config, public files and private files.
4. Deploy the image to staging.
5. Run `bench --site <site> install-app wiki` once; this syncs Wiki DocTypes, runs install behavior, and creates the initial space/page.
6. Run `bench --site <site> migrate` as required by the deployment workflow and rebuild/verify search indexes.
7. Configure roles/space/branding; run acceptance and security tests.
8. Repeat through a controlled production maintenance window, then smoke test before reopening traffic.

On later releases, deploy the new pinned image and run `bench --site <site> migrate`; never `git pull` or `bench get-app` manually inside a running production container.

### Persistence and downtime

**Verified principle:** application code/assets belong in the immutable image. Site DB, `sites/<site>/public/files`, `sites/<site>/private/files`, site config, logs as required, and other site state belong in persistent services/volumes/object storage. A manual app install in an ephemeral container without the app in subsequent images will break migrations and runtime imports.

**Inference:** initial install and schema migration should use a maintenance window. Wiki's install creates many tables/records and patches; exact downtime depends on site size and orchestrator behavior. Asset building should happen before deploy, not during the outage.

### Rollback

- Take and verify a full pre-deployment backup with files.
- Preserve the previous image digest and deployment manifest.
- If failure occurs before schema/data change, redeploy the previous image.
- If Wiki installation/migration has changed the site, restore the pre-change DB and file backup together, then redeploy the previous image. Do not assume `uninstall-app wiki` is an equivalent rollback.
- Retain logs and the failed image for diagnosis.

## 15. Upgrade Strategy and Customization Boundary

### Recommended ownership

```text
Upstream Frappe Wiki (unchanged, pinned)
        ↓
Adah image includes it
        ↓
Frappe records configure roles, space, branding
        ↓
Small CRM integration owns Docs navigation only
        ↓
Optional Adah integration code handles proven gaps
```

**Do not fork Wiki initially.** A fork would require continuous merge/security ownership across a fast-moving project. Direct edits inside an installed package are worse because they are neither reproducible nor upgrade-safe.

| Requirement | Preferred boundary |
|---|---|
| Shared auth/users | Native Frappe, no custom code |
| Sales role mapping | Wiki Space role configuration/fixtures |
| Internal vs public | Space roles and publication configuration |
| Approval | Native Change Requests and role configuration |
| Docs navigation | Small CRM frontend change |
| Branding | Wiki Space/Wiki Settings records first; CSS only if accepted gap |
| Attachment privacy | Must be designed/tested; prefer upstream fix or isolated Adah integration override, not a broad fork |
| RTL | Integration CSS/layout contribution upstream if feasible |
| CRM-record links | Plain deep links first; custom CRM fields/components only later |

### Update procedure

1. Review upstream Frappe, CRM and Wiki release notes/diffs, especially hooks, routes, DocTypes, permissions, search, renderer, file upload, and migration patches.
2. Advance pins in a branch and rebuild the full image.
3. Restore a recent anonymized production backup into staging.
4. Run requirements/assets, migrations, app unit tests, CRM tests, Wiki E2E, permission/security tests, Arabic smoke tests, and backup/restore.
5. Record schema/patch effects and rollback point.
6. Promote the tested image digest; never let branch movement change a rebuild silently.

**Cross-app risk:** CRM and Wiki are isolated at the app level but share Frappe, Python, Node builder, database, Redis, workers, login, global `User` hooks, and site routing. A framework upgrade affects both; a Wiki route/permission hook can affect site requests; an asset build change can affect the image. Joint regression testing is mandatory.

## 16. Licensing

**Verified:** Frappe Wiki's repository `LICENSE` is MIT, and `wiki/hooks.py` identifies MIT. The license permits use, copying, modification, distribution, sublicensing and sale subject to retaining the copyright/license notice. Evidence: [Wiki LICENSE](https://github.com/frappe/wiki/blob/2e4e4f215368387c08553c3c59723c7a2e1bf306/LICENSE).

**Verified:** Adah CRM's repository license is AGPL-3.0 at [`LICENSE`](./LICENSE), while some local metadata strings differ (`package.json` says GPL-3.0; hooks say AGPLv3). Wiki's MIT license itself presents no obvious incompatibility for including it as a separate dependency.

**Legal boundary:** this is repository evidence, not legal advice. Legal review should confirm combined-distribution notices and Adah's obligations under the CRM/Frappe licenses.

## 17. Security

| Area | Finding and mitigation |
|---|---|
| Unauthorized page reads | **Verified controls:** space query/has-permission hooks and renderer checks. Configure explicit role rows; test direct HTML, Markdown `.md`, API, search, sitemap/`llms.txt`, OG image, print/PDF and cached responses as unauthorized user and Guest. |
| Public/private leakage | **High risk:** no role rows means all logged-in; Guest row means public. Provision through reviewed fixtures/config and assert it after every migration. |
| Attachments | **Blocking:** editor uploads set `private:false`. Prohibit sensitive uploads in pilot or implement/test protected files tied to the Wiki document/space before production. Test raw URL access as Guest and unrelated logged-in user. |
| Search | **Verified design:** post-filters by published/readable space; test stale index, unpublish, role removal and Guest. Keep the inspected or later security-fix commit. |
| API | Frappe whitelisting/session/DocType hooks provide a base, but enumerate Wiki methods and test direct calls, especially CR merge, tree mutation, upload, PDF, crawler and search endpoints. |
| CSRF | Same-site Frappe APIs use normal session/CSRF mechanisms. Test editor mutations and uploads; do not weaken CSRF for integration. |
| XSS/content rendering | **Condition:** raw HTML is enabled by the Markdown renderer and output is marked safe. Execute stored-XSS tests (`script`, event handlers, SVG, `javascript:` links, malformed attributes, callout/media metadata) through both direct editor and CR merge paths. Confirm Frappe v16 sanitation rather than assuming it. |
| Embeds | Frontend iframe parsing has a provider allowlist, but raw Markdown/HTML and legacy data need server-render tests. Consider disabling embeds for internal V1 if not needed. |
| File uploads | Enforce Frappe file-size/type policy, malware scanning where required, safe content disposition, SVG policy, PDF/active-content review, and authorization. |
| Global hooks | Wiki adds a `User.after_insert` hook and app/route/search hooks. Test user invitation/update flows and role over-assignment. |
| Public metadata/caches | Current code includes fixes for restricted crawler routes and cache headers. Test sitemap, `llms.txt`, OG images, titles, error timing and CDN behavior with internal spaces. |

This is an integration-focused review, not a full security audit.

## 18. Backup/Restore

**Verified:** Wiki canonical content, roles, trees, revisions, CRs and File metadata live in the normal site database. Standard database backup covers those tables. Wiki uploads use standard Frappe File storage, so a **database-only** backup is insufficient for media.

**Verified:** `bench --site <site> backup --with-files` includes database, public files and private files; explicit destinations are available for each archive. Evidence: [bench backup documentation](https://docs.frappe.io/framework/user/en/bench/reference/backup).

**Recommended backup set:** database + `site_config.json` + public files + private files + image manifests/pins + any external object-storage version/snapshot. Search indexes and generated caches are derived; rebuild and test them after restore.

**Acceptance requirement:** perform a real restore into a clean environment, run migrate/reindex, and verify an internal page, its revision history, image/PDF/video, permissions, and search. A successful backup command alone is not sufficient.

## 19. Risks

| Risk | Probability | Impact | Mitigation | Blocking? |
|---|---|---|---|:---:|
| Frappe/Python version incompatibility | High until environment known | High | Inventory production; pin Frappe/CRM/Wiki; Python 3.14 image; full staging install/migrate | Yes |
| Public attachment leakage from internal pages | High with native uploader | High | Prohibit sensitive uploads or implement upstream/integration protected-file flow; raw-URL tests | Yes |
| Raw HTML/stored XSS path | Medium / unverified | High | Adversarial persistence/render tests; upstream fix or sanitizer boundary if failing | Yes |
| Floating `develop` changes | High if branch-pinned | High | Immutable SHA/image digest; reviewed update cadence | Yes |
| CRM/Wiki frontend collision | Low | Medium | Keep separate SPAs/routes/assets; do not embed one in the other | No |
| Route collision | Low now | Medium | Reserve `/wiki-app` and selected `/docs`; route regression tests | No |
| Asset build/collision | Medium | Medium | Build both in image; verify `/assets/crm` and `/assets/wiki`; no runtime builds | No |
| Incorrect role configuration | Medium | High | Explicit reviewed role rows, no Guest, automated permission matrix | Yes for go-live |
| Public crawler/cache metadata leakage | Low-Medium | High | Pin post-fix commit; test `.md`, sitemap, `llms.txt`, OG and CDN cache | Yes for go-live |
| Upgrade coupling through Frappe | Medium | High | Joint compatibility matrix, restored-site migration, pinned rollbacks | No |
| Database migration failure | Medium | High | Backup/restore rehearsal, maintenance window, prior image, staging clone | Yes for go-live |
| Docker build complexity | Medium | Medium | Immutable multi-app builder with Python/Node locks and asset smoke tests | No |
| UI inconsistency | Medium | Low-Medium | Wiki branding; accept separate surface in V1; align versions later | No |
| Arabic/RTL limitations | High for full RTL | Medium-High | Arabic corpus/device QA; scoped RTL customization; explicit V1 criterion | Decision |
| Search quality for Arabic | Medium | Medium | Corpus tests; document limitations; defer semantic/external search | Decision |
| Revision history UI absent | High | Medium | Rely on CR audit initially; defer end-user history browser or adopt later upstream feature | No |
| Wiki maintenance/release maturity | Medium | Medium-High | Active project but fast-moving; commit pin, monthly review, avoid fork | No |
| Development Docker contradicts app v16 | High for local script | Medium | Do not use it as production evidence; update only in approved implementation | No |

## 20. V1 Scope

### Include

- Same-site upstream Frappe Wiki app in the immutable image.
- One internal, published-but-role-restricted Wiki Space.
- Shared Frappe login and existing users.
- `Sales User` Read, `Sales Manager` Write, Administrator/System Manager administration (subject to final approval-role decision).
- CRM `Docs` navigation entry to the Wiki reader.
- Wiki reader/editor, nested pages, search, TOC, links, images only if attachment privacy is resolved.
- Branding sufficient to identify the surface as Adah Docs.
- English and Arabic content smoke tests; RTL only to the approved level.
- Deployment, migration, permission, security, backup and restore tests.

### Explicitly defer

- Public documentation portal.
- CRM entity <-> Wiki relational model.
- AI/semantic search or chatbot.
- Custom editor or custom Wiki engine.
- Custom approval engine beyond native Change Requests.
- GitHub sync.
- Per-page ACLs.
- Full custom CRM shell around Wiki.
- Version-history UI unless a suitable upstream release provides it.

## 21. Alternatives Considered

- **Separate site:** rejected for V1 because it introduces identity/SSO and operating duplication without a demonstrated isolation need.
- **Custom CRM documentation module:** rejected because it recreates core Wiki capabilities and increases maintenance coupling.
- **Iframe/microfrontend embedding:** rejected because it complicates routing, focus/accessibility, mobile, security headers, theming and browser navigation.
- **Adah Wiki fork:** rejected initially; only reconsider for a small, unavoidable, long-lived gap that upstream will not accept.
- **Plain links to external documents:** viable temporary fallback if compatibility/privacy conditions fail, but does not meet the integrated governance/search objective.

## 22. CRM Coupling Opportunities (Post-V1)

**Verified:** standard routes are sufficient for simple links. A CRM record can link to a Wiki reader URL, and a Wiki page can link back to `/crm/...`.

Future low-coupling patterns:

- status/configuration records store a documentation URL;
- CRM detail pages show a “Related guide” link;
- Wiki pages use stable deep links to CRM filtered views;
- a small mapping DocType links `(reference_doctype, reference_name or status, wiki_document)` if reporting/administration becomes necessary.

**Inference:** contextual cards, automatic recommendations, relation search, permissions synchronized to record ownership, or inline Wiki previews require custom CRM backend fields/APIs/components and careful cross-permission checks. None belongs in V1.

## 23. Recommendation

# APPROVE WITH CONDITIONS

Frappe Wiki is the right product and architectural fit: it shares Frappe users/authentication and infrastructure, its v3 data and approval model cover the requested knowledge-base capabilities, CRM/Wiki routes and assets are naturally isolated, and existing CRM roles map directly to per-space Read/Write access. A custom Wiki or separate site would cost more and integrate worse.

Approval should authorize an **implementation spike**, not immediate production rollout. Production remains blocked until:

1. the exact Frappe v16/Python 3.14/Node/image matrix passes same-site install and restored-site migration tests;
2. a reviewed immutable Wiki pin at or after `2e4e4f2...` is selected;
3. internal attachment access is made safe or attachments are explicitly disabled;
4. stored-XSS and public-metadata/cache tests pass;
5. Adah decides the author/approver role split and Arabic/RTL V1 acceptance level;
6. backup/restore and rollback rehearsal succeeds.

## 24. Implementation Plan After Approval

### Phase 1 — Version and image compatibility spike

- **Goal:** prove CRM + Wiki + Frappe coexist in one reproducible image.
- **Expected files/config:** external production image/app manifest; lock files/build pipeline. No CRM behavior changes.
- **Migrations:** none on production; create disposable test site.
- **Tests:** build both apps; Python/Node dependency resolution; `bench version`; install CRM then Wiki; asset and route smoke tests; both apps' unit tests.
- **Acceptance:** immutable image starts all services; `/crm`, `/wiki-app`, `/docs`, assets, worker and scheduler work; selected pins recorded.
- **Rollback:** discard test image/site; production unchanged.

### Phase 2 — Install on a restored development/staging site

- **Goal:** validate installation and patches against real Adah schema/data.
- **Expected files/config:** deployment inventory/runbook only; app is already in image.
- **Migrations:** `install-app wiki`, Wiki DocType sync/patches, initial space/page and role assignment.
- **Tests:** pre/post schema counts, CRM data integrity, migrate idempotence, search build, user invitation hook, site restart.
- **Acceptance:** no CRM regression or collision; a second migrate is clean; migration duration measured.
- **Rollback:** restore pre-install database/files and prior image.

### Phase 3 — Authentication, permissions, content security and attachments

- **Goal:** make the internal access model safe.
- **Expected files/config:** Wiki Space/Wiki Settings/Role configuration; preferably fixtures or an idempotent Adah integration setup hook if configuration must be reproducible. A small override/custom module only if attachment security cannot be solved upstream/configurably.
- **Migrations:** fixture/config sync only; possible File relationship changes if approved design needs them.
- **Tests:** full persona matrix across reader, editor, API, search, `.md`, sitemap/`llms.txt`, OG/PDF, cache and raw attachment URLs; CSRF/XSS/file-type tests.
- **Acceptance:** Sales User read-only; Sales Manager approved capability; unauthorized/Guest cannot infer internal data; attachments meet policy; no broad role leakage.
- **Rollback:** revert configuration/override, restore staging snapshot; no production change until accepted.

### Phase 4 — CRM navigation integration

- **Goal:** add the Docs entry without merging the two SPAs.
- **Expected files:** likely [`frontend/src/components/Layouts/AppSidebar.vue`](./frontend/src/components/Layouts/AppSidebar.vue), possibly [`frontend/src/router.js`](./frontend/src/router.js) only if a redirect route is chosen, an existing/new icon, translations, and frontend tests.
- **Migrations:** none.
- **Tests:** desktop/mobile sidebar, permission-based visibility, same-tab navigation, browser back/forward, login redirect and deep links; existing CRM routes.
- **Acceptance:** intended users reach the configured reader landing page in one click; CRM navigation remains stable.
- **Rollback:** remove the isolated navigation commit.

### Phase 5 — Branding and Arabic/RTL acceptance

- **Goal:** make Docs recognizably Adah and meet the approved language bar.
- **Expected files/config:** Wiki Space logos/favicon/name/navbar and possibly narrowly scoped integration CSS/translations. Prefer upstream contribution for reusable RTL changes.
- **Migrations:** configuration/fixtures only.
- **Tests:** light/dark, desktop/mobile, Arabic titles/content/routes, mixed text, editor cursor/lists/tables, search corpus, print/PDF.
- **Acceptance:** brand review passes; documented RTL criterion passes or known limitations are explicitly accepted.
- **Rollback:** revert branding/CSS fixtures; content remains.

### Phase 6 — Release, operations and production rollout

- **Goal:** deploy safely and prove operability.
- **Expected files/config:** production image manifest/pins, deployment/runbook, monitoring, backup policy, CI tests.
- **Migrations:** production `install-app wiki` once, then normal migrate.
- **Tests:** complete strategy below on production-like staging; backup/restore; container recreation; load/smoke; post-deploy checks.
- **Acceptance:** approved change window, verified backup, image digest, migration duration, smoke suite, observability and rollback owner.
- **Rollback:** previous image + coordinated DB/files restore if schema changed.

## 25. Testing Strategy After Approval

### Existing repository requirements

- Run `cd frontend && yarn test:run`; project context currently requires all **118 unit tests** to pass: [`AGENTS.md`](./AGENTS.md).
- Run the repository's existing frontend, server, migration and E2E CI-equivalent suites (`.github/workflows/`).
- Run Wiki Python/unit tests and relevant Playwright E2E tests at the selected pin.

### Required integration matrix

- Existing CRM login/logout and password/OAuth/2FA behavior works.
- Existing CRM tests and routes pass.
- Wiki reader and `/wiki-app` load with both assets and no console errors.
- Existing CRM user uses the same account/session; no second credentials.
- CRM non-user, Website User, disabled user, Guest, Sales User, Sales Manager, System Manager and Administrator are explicitly tested.
- Unauthorized users cannot read private pages via HTML, API, search, `.md`, sitemap, `llms.txt`, OG image, PDF/print, cache, title/breadcrumb or timing side channels.
- Role changes take effect after cache invalidation/session refresh.
- Sales User read-only/contribution behavior matches decision.
- Sales Manager create/edit/submit/review/approve/merge behavior matches decision.
- Create, move, nest, rename, unpublish, delete and conflict/merge page flows work.
- Images, video, PDF and permitted generic files work; raw URLs enforce attachment policy.
- Search indexes, updates, unpublishes and permission changes work; workers/scheduler drain queues.
- Arabic titles/content, mixed Arabic/English, links, tables, headings, TOC, slugs and search corpus work.
- RTL reader/editor/mobile meets the approved criterion.
- CRM and Wiki desktop/mobile navigation, breadcrumbs, deep links and browser back/forward work.
- Websocket, Redis, scheduler and background workers remain healthy.
- Installation/migration works on a copy of an existing site; second migrate is idempotent.
- Full backup and clean restore preserve Wiki database content, revisions, public/private files and permissions; search rebuild succeeds.
- Container/pod recreation and image replacement preserve the site and Wiki content without manual container edits.
- Previous image + backup rollback is timed and rehearsed.
- Stored-XSS corpus and malicious upload corpus produce no executable content or unauthorized disclosure.

## 26. Open Decisions

1. **Production baseline:** what exact Frappe commit, Python, Node, DB, Redis, image builder, sites and volumes are deployed?
2. **Wiki pin:** accept a reviewed `develop` SHA temporarily, or wait for a later release containing the required fixes?
3. **Attachment policy:** protected uploads, external controlled storage, or no sensitive attachments in V1?
4. **Roles:** may every Sales Manager approve/merge, or should a narrower Wiki Publisher role own Write while Sales Manager contributes at Read tier?
5. **Sales User contributions:** strict read-only (`allow_contributions=0`) or allowed suggestions?
6. **UX:** `Docs` or `Knowledge Base`; landing page; same tab (recommended) or new tab?
7. **Arabic/RTL:** Arabic-content smoke support or full RTL as a V1 release requirement?
8. **Public docs:** explicitly deferred (recommended), or create a separate public space with a separate content review?
9. **Configuration ownership:** manual site configuration or reproducible fixtures/idempotent integration setup?
10. **Operational owner:** who reviews Wiki upstream monthly and owns joint migration/security testing?

## 27. Evidence / Source References

### Adah CRM repository

- [`AGENTS.md`](./AGENTS.md) — project context, architecture and required frontend tests.
- [`.pi/PLAN.md`](./.pi/PLAN.md), [`.pi/SPEC.md`](./.pi/SPEC.md), [`.pi/ARCHIVE.md`](./.pi/ARCHIVE.md) — Adah/CRM scripting and FieldLayout roadmap/contracts/history.
- [`README.md`](./README.md) — documented local/production/development setup.
- [`pyproject.toml`](./pyproject.toml) — Python and Frappe dependency metadata.
- [`package.json`](./package.json), [`frontend/package.json`](./frontend/package.json) — CRM build and frontend dependencies.
- [`crm/hooks.py`](./crm/hooks.py), [`crm/install.py`](./crm/install.py) — routes, hooks, permissions, jobs and install behavior.
- [`frontend/src/router.js`](./frontend/src/router.js), [`frontend/src/stores/session.js`](./frontend/src/stores/session.js), [`frontend/src/stores/users.js`](./frontend/src/stores/users.js) — CRM routing, authentication and user roles.
- [`frontend/src/components/Layouts/AppSidebar.vue`](./frontend/src/components/Layouts/AppSidebar.vue) — current navigation model.
- [`docker/docker-compose.yml`](./docker/docker-compose.yml), [`docker/init.sh`](./docker/init.sh) — checked-in development Docker assumptions and v15 drift.

### Frappe Wiki upstream at inspected commit

- [Dependency metadata](https://github.com/frappe/wiki/blob/2e4e4f215368387c08553c3c59723c7a2e1bf306/pyproject.toml), [root build](https://github.com/frappe/wiki/blob/2e4e4f215368387c08553c3c59723c7a2e1bf306/package.json), [frontend dependencies/build](https://github.com/frappe/wiki/blob/2e4e4f215368387c08553c3c59723c7a2e1bf306/frontend/package.json).
- [Hooks/routes/search registration](https://github.com/frappe/wiki/blob/2e4e4f215368387c08553c3c59723c7a2e1bf306/wiki/hooks.py), [install behavior](https://github.com/frappe/wiki/blob/2e4e4f215368387c08553c3c59723c7a2e1bf306/wiki/install.py), [patches](https://github.com/frappe/wiki/blob/2e4e4f215368387c08553c3c59723c7a2e1bf306/wiki/patches.txt).
- [Permission model](https://github.com/frappe/wiki/blob/2e4e4f215368387c08553c3c59723c7a2e1bf306/wiki/permissions.py), [user/upload APIs](https://github.com/frappe/wiki/blob/2e4e4f215368387c08553c3c59723c7a2e1bf306/wiki/api/__init__.py).
- [Authoring routes](https://github.com/frappe/wiki/blob/2e4e4f215368387c08553c3c59723c7a2e1bf306/frontend/src/router.js), [session](https://github.com/frappe/wiki/blob/2e4e4f215368387c08553c3c59723c7a2e1bf306/frontend/src/stores/session.js), [editor/uploads](https://github.com/frappe/wiki/blob/2e4e4f215368387c08553c3c59723c7a2e1bf306/frontend/src/components/WikiEditor.vue).
- [Wiki Document/reader](https://github.com/frappe/wiki/blob/2e4e4f215368387c08553c3c59723c7a2e1bf306/wiki/frappe_wiki/doctype/wiki_document/wiki_document.py), [reader template](https://github.com/frappe/wiki/blob/2e4e4f215368387c08553c3c59723c7a2e1bf306/wiki/templates/wiki/document.html), [Markdown renderer](https://github.com/frappe/wiki/blob/2e4e4f215368387c08553c3c59723c7a2e1bf306/wiki/wiki/markdown.py).
- [Search implementation](https://github.com/frappe/wiki/blob/2e4e4f215368387c08553c3c59723c7a2e1bf306/wiki/frappe_wiki/doctype/wiki_document/wiki_sqlite_search.py), [permission-filtered search API](https://github.com/frappe/wiki/blob/2e4e4f215368387c08553c3c59723c7a2e1bf306/wiki/frappe_wiki/doctype/wiki_document/search.py).
- [Change Request approval/merge](https://github.com/frappe/wiki/blob/2e4e4f215368387c08553c3c59723c7a2e1bf306/wiki/frappe_wiki/doctype/wiki_change_request/wiki_change_request.py), [v3 DocTypes](https://github.com/frappe/wiki/tree/2e4e4f215368387c08553c3c59723c7a2e1bf306/wiki/frappe_wiki/doctype).
- [MIT license](https://github.com/frappe/wiki/blob/2e4e4f215368387c08553c3c59723c7a2e1bf306/LICENSE).

### Official Frappe references

- [Apps and install-app](https://docs.frappe.io/framework/user/en/basics/apps).
- [Users and permissions](https://docs.frappe.io/framework/user/en/basics/users-and-permissions).
- [Asset bundling](https://docs.frappe.io/framework/user/en/basics/asset-bundling).
- [Production setup and update behavior](https://docs.frappe.io/framework/user/en/production-setup).
- [Backup with public/private files](https://docs.frappe.io/framework/user/en/bench/reference/backup).
- [Site directory structure](https://docs.frappe.io/framework/user/en/basics/directory-structure).

---

**Stop condition:** this document completes discovery only. No Wiki dependency, app installation, route, navigation, Docker, deployment, or production behavior has been changed.

> **Awaiting approval before implementation.**
