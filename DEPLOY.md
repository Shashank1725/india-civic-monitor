# 🚀 Deploying to Render (free tier)

This project deploys as **one free Render web service**: FastAPI serves both the
REST API and the built React dashboard (`frontend/dist`), and restores the
database from a compressed snapshot at boot.

```text
Browser ──► https://<your-app>.onrender.com
                ├── /            → React dashboard (static files)
                ├── /api/*       → FastAPI endpoints
                └── /health      → status + data_ready flag
```

## Why a snapshot? (the free-tier constraints)

| Render free fact | Consequence |
|---|---|
| Filesystem is **wiped on every sleep/restart/redeploy** | The 692 MB SQLite DB cannot persist — it must be restored at boot |
| Only **0.1 CPU** | Re-ingesting 766,648 CSV rows takes **~15 min** on a normal PC → **hours** on Render. Not viable as a boot step |
| **Inbound bandwidth is free** | Downloading a snapshot at boot costs nothing |
| Service **sleeps after 15 min idle** | First request after idle takes ~1–2 min (spin-up + snapshot restore) |

So the data ships as a **78.6 MB zstd snapshot** hosted as a free GitHub
Release asset. At boot the app streams it in, verifies SHA-256 + SQLite
integrity + row count, and atomically swaps it into place (~15–60 s).

---

## Step 1 — Push the repo to GitHub

```powershell
cd C:\Users\Asus\Downloads\DATASci\india-civic-monitor
git init
git add .
git commit -m "India Civic Monitor: Render-ready single-service deploy"

# Create the repo on github.com first, then:
git remote add origin https://github.com/Shashank1725/india-civic-monitor.git
git push -u origin main
```

> The repo includes the raw `Dataset/` CSVs (100 MB) as the ingestion fallback
> source. The DB files (`*.db`) and `snapshots/` are git-ignored.

## Step 2 — Package & upload the DB snapshot (one-time)

```powershell
python scripts/package_db_snapshot.py
```

It prints something like:

```text
snapshot   : snapshots\india_civic_monitor.db.zst  (78.6 MB)
sha256     : 8041a566ad6f3d1aa474e4e899c11b7838664f74a73f201254ce41f706081ce9
```

Upload it to GitHub:

1. GitHub → your repo → **Releases** → **Draft a new release**
2. Tag: `v1`, title: `DB snapshot`
3. **Attach `india-civic-monitor/snapshots/india_civic_monitor.db.zst`** (drag & drop, 78.6 MB)
4. Publish

Your snapshot URL will be:

```text
https://github.com/Shashank1725/india-civic-monitor/releases/download/v1/india_civic_monitor.db.zst
```

> Re-run the script (and re-upload as `v2`…) whenever the data changes; update
> `DB_SNAPSHOT_SHA256` to match.

## Step 3 — Create the Render service

1. Sign up at <https://dashboard.render.com> (free, no credit card)
2. **New → Web Service** → connect your GitHub repo
3. Render detects `render.yaml` (Blueprint) — approve it, or fill in manually:

| Field | Value |
|---|---|
| Runtime | **Python** |
| Build Command | `pip install -r requirements.txt && cd frontend && npm ci && npm run build` |
| Start Command | `python -m uvicorn api.main:app --host 0.0.0.0 --port $PORT` |
| Instance Type | **Free** (0.1 CPU / 512 MB) |

4. **Environment** → add:

| Key | Value |
|---|---|
| `DB_SNAPSHOT_URL` | `https://github.com/Shashank1725/india-civic-monitor/releases/download/v1/india_civic_monitor.db.zst` |
| `DB_SNAPSHOT_SHA256` | the sha256 printed in Step 2 |

(`DATABASE_URL`, `DATASET_DIR`, `PYTHON_VERSION` handling already come from
`render.yaml` / `.python-version`.)

5. **Create Web Service** and wait for the first build (~3–6 min).

## Step 4 — Verify

Watch the **Logs** stream for:

```text
bootstrap: ephemeral disk: total=?.? GB, free=?.? GB      ← free-tier disk size
bootstrap: downloading snapshot: https://github.com/...
bootstrap: snapshot sha256 verified (...)
bootstrap: snapshot verified: 766,648 rows, quick_check ok (...)
bootstrap: state=ready snapshot restored
```

Then check:

- `https://<your-app>.onrender.com/` → the dashboard
- `https://<your-app>.onrender.com/health` → `"data_ready":true, "bootstrap_state":"ready"`
- `https://<your-app>.onrender.com/docs` → Swagger UI

**Note the `ephemeral disk: total=` value.** If it is **below ~1 GB**, the
snapshot won't fit (see Troubleshooting).

---

## Behaviour & limits (free tier)

- **Cold start:** after 15 min without traffic the service sleeps; the next
  visitor waits ~1–2 min (Render spin-up ≈ 1 min + snapshot restore).
  Keep the tab open or share the link knowing the first load is slow.
- **750 free instance-hours/month** per workspace — a sleeping service consumes
  none, so this is plenty for a demo.
- **5 GB outbound bandwidth/month** (dashboard + API JSON). Inbound
  (snapshot downloads) is free.
- **Builds:** 500 pipeline minutes/month (~80 builds).
- The service may be **restarted by Render at any time** — that's fine, the
  snapshot is restored on every boot.
- This is a **historical snapshot (2020–2025)** — no live data updates.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `bootstrap: state=failed` / `database or disk is full` in logs | The free instance's ephemeral disk is < ~800 MB. Options: (1) slim the DB — drop redundant indexes and repackage; (2) switch to the paid `0.5c-512mb` plan ($7/mo) with a persistent disk; (3) deploy on Hugging Face Spaces instead (50 GB disk, 16 GB RAM) |
| `SHA-256 mismatch` | You uploaded a different file than the one you hashed — re-run `package_db_snapshot.py` and update `DB_SNAPSHOT_SHA256` |
| Deploy fails in `pip install` / `npm ci` | Confirm `.python-version` is committed (must say `3.12` — Render's default 3.14 can't build the pinned numpy) and `package-lock.json` exists |
| `/health` stays `"data_ready":false` | Snapshot URL wrong/asset not published (check `DB_SNAPSHOT_URL`), or the CSV fallback is still ingesting (~15 min, hours on 0.1 CPU) — watch the logs |
| `state=downloading` for a long time | Normal on first boot; GitHub release downloads can take 10–60 s |
| Dashboard 404s / API works but UI doesn't | `frontend/dist` wasn't built — check the build log for the `npm ci && npm run build` step |

## Local development (unchanged)

```powershell
# terminal 1 — API (bootstrap is a no-op when the DB already has data)
python -m uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload

# terminal 2 — Vite dev server with /api proxy
cd frontend
npm run dev
```

Open <http://localhost:5173>. Tests: `pytest -v`.
