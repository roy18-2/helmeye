# HelmEye

A traffic-command web app for reviewing helmet-violation incidents from CCTV footage. Operators upload video, a detector pipeline flags riders without helmets, and human reviewers confirm or reject each flag.

> **Status: working prototype with a simulated detector.**
> The detector in this repository is a **mock**. It does not look at the footage: it invents violations from a hash of the file's contents, so results are repeatable but not real. Evidence frames are stamped "MOCK DETECTOR - SIMULATED BOX", and the demo incidents are labelled as demo data. Do not use the output for enforcement.
> The detector sits behind a small interface (`backend/app/detectors/base.py`) so a real model can replace it.

## Features

- Sign-in with JWT, with two roles: admin and reviewer
- Video upload (MP4, MOV, AVI, MKV, WEBM, up to 500 MB) with a background processing job and live progress
- Incident list with filters: review status, camera, detection type, minimum confidence, date range, paging
- Evidence viewer with the full image, details and a complete review history
- Review workflow: confirm, false positive or uncertain, with an optional note. Every decision records who made it and when, and earlier decisions are never overwritten
- Analytics: violations by hour (in your timezone), incidents per day, by camera, review outcomes, and reviewed precision
- Replay: play a processed video with detection boxes at the flagged moments
- Light and dark themes that follow your system setting

## Tech stack

| Part | Tools |
|---|---|
| Backend | Python 3.11+, FastAPI, Uvicorn, Motor (async MongoDB), Pydantic, PyJWT, bcrypt, OpenCV, NumPy |
| Frontend | React 19, Vite, React Router, Tailwind CSS, Recharts, lucide-react, Axios |
| Database | MongoDB (Atlas free tier or a local install) |
| Tests | pytest, httpx |

## Project layout

```
helmeye/
├── backend/
│   ├── app/
│   │   ├── detectors/     # Detector interface and the mock detector
│   │   ├── routers/       # auth, cameras, incidents, videos, replay, analytics
│   │   ├── services/      # evidence images and the processing pipeline
│   │   ├── config.py, database.py, models.py, security.py
│   │   ├── seed.py        # cameras and the admin user
│   │   └── seed_demo.py   # synthetic demo incidents
│   ├── tests/
│   ├── requirements.txt
│   └── .env.example
└── frontend/
    └── src/               # pages, components, theme and auth contexts
```

## Getting started

You need Python 3.11+, Node 20+, Git, and a MongoDB database. A free MongoDB Atlas cluster works. Add your IP address under Network Access.

### 1. Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

Edit `backend/.env`:

- `MONGO_URL`: your MongoDB connection string
- `JWT_SECRET`: generate one with `python -c "import secrets; print(secrets.token_urlsafe(48))"`
- `SEED_ADMIN_EMAIL` and `SEED_ADMIN_PASSWORD`: the first admin account (password 8 to 72 characters)

Then create the cameras and the admin, add demo incidents, and start the server:

```bash
python -m app.seed
python -m app.seed_demo
uvicorn app.main:app --reload --port 8000
```

Interactive API docs are at http://localhost:8000/docs.

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 and sign in with the admin account. The dev server proxies `/api` to port 8000.

## Using it

1. **Upload:** choose a video and a camera on the Upload page. The job list updates by itself.
2. **Review:** open Incidents, click a row, and choose Confirm, False positive or Uncertain.
3. **Analyse:** the Analytics page shows patterns and the reviewed-precision figure (confirmed divided by confirmed plus false positives).
4. **Replay:** pick a processed video to see the flagged moments. Browsers need H.264 video for playback.

Demo incidents use plates that start with `ZZ`, so they cannot match a real vehicle. Reset them with `python -m app.seed_demo --reset`.

## API overview

All routes except login and health need an `Authorization: Bearer <token>` header.

| Method and path | Purpose |
|---|---|
| `POST /api/auth/login` | Log in and get a token |
| `GET /api/auth/me` | Current user |
| `GET, POST /api/auth/users` | List or create users (admin only) |
| `GET /api/cameras` | List cameras |
| `GET /api/incidents` | List with filters and paging |
| `GET /api/incidents/summary` | Counts and reviewed precision |
| `GET /api/incidents/{id}` and `/evidence` | One incident and its image |
| `PATCH /api/incidents/{id}/review` | Record a review decision |
| `POST /api/videos` | Upload a video (starts a background job) |
| `GET /api/videos` and `/{id}` | Job status and progress |
| `POST /api/videos/{id}/stream-token` | Short-lived token for playback |
| `GET /api/videos/{id}/stream?token=...` | Stream the video |
| `GET /api/analytics` | Chart data for a period and timezone |
| `GET /api/health` | Server and database check |

## Tests

```bash
cd backend
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

The tests use a separate database named `helmeye_test` on the server from `MONGO_URL`. Its collections are emptied before and after each run, and your real data is never touched.

## Known limitations

- The detector is a mock (see the status note above).
- Processing runs inside the API process, one video at a time. A server restart marks running jobs as failed.
- The login token is stored in the browser's localStorage, and stream tokens appear in the video URL for 30 minutes.
- There is no login rate limiting, and uploaded files are kept on local disk.
- For development the Atlas network rule may allow any IP address. Restrict it before deploying.

## Ideas for next steps

- Implement `Detector` with a real model (for example YOLO) and compare it against reviewer decisions
- Number plate recognition
- A job queue and object storage for uploads
- User management screens and password changes