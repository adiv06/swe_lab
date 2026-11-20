# MongoDB key-value service

A small HTTP service that stores one JSON value under each string key in MongoDB.
The service owns a single database and collection, configured through environment
variables. It creates or replaces a value when you call `PUT`.

## Run the app with Atlas

Create an untracked `.env` file from `.env.example` and set `MONGODB_URI` to
your Atlas connection string. Start Docker Desktop, then run:

```powershell
docker compose up --build
```

Open `http://localhost:5173/register` to create an account, then use the login
page. Compose starts the frontend and API. It requires `MONGODB_URI` and does
not start a local MongoDB server. Stop the stack with `Ctrl+C`.
The login and registration forms show database status and stay disabled until
MongoDB responds. The app checks status every five seconds and blocks its main
pages while the database is unavailable. The API also checks the connection on
every login and registration request.

Accounts, sessions, projects, and the two hardware units go
through the API to Atlas. Existing projects previously stored in a browser are
not automatically imported. The status indicator reflects the Atlas connection.
Keep `.env` out of Git.

## Connect to an existing MongoDB cluster

Set `MONGODB_URI` to the connection string for your MongoDB cluster. Use the
credentials supplied for that cluster; URL-encode special characters in the
username or password. The supplied connection string template is in
[`.env.example`](.env.example). Do not commit a filled-in `.env` file.

| Variable | Default | Purpose |
| --- | --- | --- |
| `MONGODB_URI` | Required | MongoDB connection string |
| `MONGODB_DATABASE` | `swe_lab` | Database name |
| `MONGODB_COLLECTION` | `items` | Collection name |

With Python 3.12 or newer:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:MONGODB_URI = 'mongodb+srv://USERNAME:PASSWORD@cluster0.ukanywx.mongodb.net/?appName=Cluster0'
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Or build and run the container after setting `MONGODB_URI` in your shell:

```powershell
docker build -t mongo-key-value .
docker run --rm -p 8000:8000 -e MONGODB_URI -e MONGODB_DATABASE=swe_lab -e MONGODB_COLLECTION=items mongo-key-value
```

## API

`PUT /items/{key}` stores or replaces a JSON value. The request body must have
a `value` field, which can hold any JSON value, including `null`. The response
is the same JSON body. `GET /items/{key}` returns that body, or `404` if the
key does not exist. `GET /health` checks the database connection. Connection
errors return `503`.

```powershell
curl.exe -X PUT http://localhost:8000/items/example -H 'Content-Type: application/json' -d '{"value":{"name":"Ada","active":true}}'
curl.exe http://localhost:8000/items/example
curl.exe http://localhost:8000/health
```

Interactive API documentation is at `http://localhost:8000/docs`.

## Username and password login

The frontend registration and login forms call `POST /api/auth/register` and
`POST /api/auth/login`. Users are stored in the `users` MongoDB collection with
hashed passwords. Login sessions are stored in `sessions` and held in an
HTTP-only browser cookie. The login response contains only the public user profile.
If running outside Compose, run the backend on port 8000, then run `npm run dev`
in `frontend`; Vite forwards `/api` requests to the backend.

## Two hardware units

The app uses two individual items in the `HW Allocation` MongoDB collection:
Arduino Kit 1 and Raspberry Pi Kit 1. A fresh database gets these two records
automatically. Each item has one available unit. The project page shows `1 / 1`
when it is available and `0 / 1` when it is checked out.

Create a project with a unique Project ID, then check out either item from the
project page. A second checkout of an allocated item returns `409`. Any member
of the same project can check it in, including a member who did not check it
out. The Inventory page shows the holder and project for each item. State is
stored in Atlas and survives logout and login.

The API uses `GET /api/units` and
`POST /api/projects/{project_id}/units/{unit_id}/checkout` or `/checkin`.
Project creators can delete a project after its units are checked in. A deleted
project disappears from every member's list without affecting other projects.

## Demo data

After setting `MONGODB_URI`, run `python -m scripts.seed_demo`. It adds the five
key-value demo records (`demo-user-001` through `demo-user-005`), login accounts
`ada`, `grace` and `alan` (password `password123`), and the two hardware units.
