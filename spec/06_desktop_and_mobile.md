# spec/06 — Desktop packaging & mobile app

## Desktop (Tauri 2) — `apps/desktop/`

Terra.OS ships as a **signed installable desktop application**. The Tauri (Rust) shell:
1. Serves the **Next.js static export** (`apps/ui` built with `output: 'export'`) in-process — no browser.
2. Supervises **sidecars**: Postgres (bundled binaries), Ollama runtime, and the FastAPI service.
3. Provides privileged local ops: file access (documents, drawings), backup, model download.

```
apps/desktop/
  src-tauri/        # Rust: sidecar supervisor, lifecycle, secure storage, updater
  binaries/         # bundled postgres, (ollama installed/managed), python runtime
  tauri.conf.json   # bundle targets, signing, updater endpoint
```

Requirements:
- **First-run setup:** init local Postgres data dir, run Alembic migrations, create `tenant` + `owner_profile`,
  pull Ollama models (download on first run or import from USB to keep installer small). Show progress.
- **Sidecar health:** the shell starts/stops/monitors Postgres+API+Ollama; `/health` surfaced in UI; if a
  sidecar dies, restart with backoff and show an "offline" banner.
- **Auto-update:** Tauri updater against a QA10-hosted update feed (config). Updates applied with consent.
- **Backup:** scheduled `pg_dump` + document-FS snapshot to a configured disk/NAS path; optional encrypted
  cloud copy; `/backup/status` shows last run; quarterly restore-test command.
- **Single operator:** no login; OS-level user is the boundary. Per-device tokens minted here for mobile.
- **Packaging targets:** Windows primary (NSIS/MSI); macOS/Linux optional. Sign installers.

**Acceptance:** a clean install on a fresh machine boots the app, runs migrations, pulls models, and reaches a
green `/health`; killing the API sidecar shows the offline banner and auto-recovers.

### Hardware paths (client-side, document in installer notes — VERIFY prices)
- Path A: ~32 GB RAM box, no GPU → all inference on Bedrock.
- Path B (recommended): GPU 16–24 GB (RTX 5060 Ti 16GB / used RTX 3090 24GB) → local Ollama carries most tokens.

## Mobile (Flutter) — `apps/mobile/` · Tier 3 only

Thin client to the local API over LAN or secure tunnel (Tailscale). For the field crew.

Features:
- Auth via **device token** (registered from desktop; `POST /mobile/devices/register`). No public accounts.
- Receive **daily plans** (push + pull `GET /mobile/plans`): location photos, technical drawings, Google Maps
  pin (open navigation), doc-derived cautions, boss note.
- **Offline cache** (Drift): today's plan available offline; status updates queue and sync when online.
- **Field status** back to office: `POST /mobile/status` (note + photos), queued offline.

```
apps/mobile/
  lib/ (features/plans, features/status, data/api_client, data/cache(drift), core/auth)
  ios/ android/
```
State mgmt: Riverpod or Bloc. `flutter analyze` clean. Unit + widget tests for plan rendering and offline sync.

**Acceptance:** with a running desktop API, a registered device fetches the dispatched plan, opens the map pin,
works offline (cached), and a queued field status syncs on reconnect.

### Secure reach
When the desktop box is on a private LAN, expose the mobile API via Tailscale/tunnel (Tier 3 reserve). Never
expose the local API publicly without the tunnel + device-token auth.
