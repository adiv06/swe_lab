# Hardware Allocator (swe_lab)

A web app where users sign up, create or join projects, and check hardware in
and out of two shared hardware sets. FastAPI + MongoDB Atlas on the back end,
React (Vite) on the front end, deployed as **one** Docker service on Render.

## How it works

| Thing | Where it lives |
| --- | --- |
| Users (hashed passwords) | `users` collection |
| Login sessions (HTTP-only cookie `hw_session`) | `sessions` collection |
| Projects: `_id` = project ID, `member_ids`, `hardware: {"HWSet1": n, ...}` | `projects` collection |
| Hardware sets: `capacity`, `available` | `hardware_sets` collection |

A fresh database automatically gets **HWSet1** and **HWSet2**, each with
capacity 100. Checkout and check-in use conditional atomic updates, so:

- you can't check out more than is available (409, "only N available");
- you can't check in more than your project holds (409);
- only project members can check hardware in or out (403 until you join);
- any member can check in units another member checked out;
- everything is in Atlas, so it survives logout, login and redeploys.

## Run locally

1. Copy `.env.example` to `.env` and set `MONGODB_URI` to your Atlas string
   (URL-encode special characters in the password). Never commit `.env`.
2. With Docker Desktop running:

   ```powershell
   docker compose up --build
   ```

   Open http://localhost:8000.

To work on the frontend with hot reload instead, run the API on port 8000
(`uvicorn app.main:app --reload`) and, in `frontend/`, `npm install` then
`npm run dev`, and open http://localhost:5173. Vite forwards `/api` to port 8000.

Tests: `pip install -r requirements.txt pytest httpx` then `python -m pytest`.

## Deploy on Render (instead of Heroku)

1. **Atlas → Network Access → Add IP Address → `0.0.0.0/0`.** Render's IPs
   change, so without this every login fails with "MongoDB unavailable".
2. Push this repo to GitHub.
3. At https://render.com, sign in with GitHub → **New → Blueprint** → pick
   this repo. Render reads `render.yaml` and asks for `MONGODB_URI`: paste your
   Atlas string.
4. Wait for the build, then open the `https://<name>.onrender.com` URL.
   `/health` should return `{"status":"ok"}`.

The free plan sleeps after 15 minutes with no traffic and takes about a minute
to wake, so open the site a couple of minutes before a demo.

## API

All `/api` routes except register/login/status need the login cookie.

| Method & path | Body | Notes |
| --- | --- | --- |
| `POST /api/auth/register` | `{name, username, password}` | username 3–32 letters/digits/`_`, password ≥ 8 chars; 409 if taken |
| `POST /api/auth/login` | `{username, password}` | 401 on a wrong username/password |
| `POST /api/auth/logout` | | |
| `GET /api/projects` | | all projects, with `isMember` |
| `POST /api/projects` | `{id, name, description?}` | 409 if the ID exists |
| `POST /api/projects/{id}/join` | | 404 if no such project |
| `GET /api/hardware` | | `[{id, name, capacity, available}]` |
| `POST /api/projects/{id}/hardware/{setId}/checkout` | `{quantity}` | 403 non-member, 409 more than available |
| `POST /api/projects/{id}/hardware/{setId}/checkin` | `{quantity}` | 409 more than the project holds |
| `GET /api/inventory` | | each set with the projects holding units |
| `DELETE /api/projects/{id}` | | creator only, after all hardware is checked in |

Interactive docs: `/docs`.

## Checkpoint test script

Use two browsers (or one normal window and one private window) for the two users.

| # | Do this | Expect |
| --- | --- | --- |
| 1 | Register `user1` (password ≥ 8 chars) | Logged in on the Projects page |
| 2 | Log out, log in with the right password | Projects page |
| 3 | Log in with a wrong password | "Invalid username or password" |
| 4 | Create project ID `p100` | Appears under My projects |
| 5 | Create `p100` again | "Project ID already exists" |
| 6 | Join an existing project by ID (e.g. one user2 made) | Moves to My projects |
| 7–8 | Open `p100`, check out 10 of HWSet1 and 20 of HWSet2 | Success message |
| 9 | Look at Available | HWSet1 90/100, HWSet2 80/100 |
| 10 | Check out 1000 of HWSet1 | "only 90 available", nothing changes |
| 11–12 | Check in 1 of HWSet1 | HWSet1 91/100 |
| 13–14 | Log out, log back in, open `p100` | Same numbers as before |
| 15 | TA registers `user2` in the other browser | Logged in |
| 16 | TA creates `p100` | "Project ID already exists" |
| 17 | TA opens `p100` before joining | Must join first (checkout returns 403); then Join |
| 18–19 | TA checks in 20 of HWSet2 | HWSet2 back to 100/100 |
| 20 | TA checks out hardware | Available drops |

## Demo data

`python -m scripts.seed_demo` adds accounts `ada`, `grace` and `alan`
(password `password123`) and creates the hardware sets.
