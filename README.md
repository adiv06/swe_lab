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

Accounts, sessions, projects, hardware sets, allocations, and unit requests go
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

## Project hardware unit requests

In the `swe_lab` database, create a collection named exactly `HW Allocation`.
Paste the two documents from [`data/hw_units_seed.json`](data/hw_units_seed.json)
into that collection, one document at a time. Each starts with
`"status": "available"`. The Create a project form lists available units.
When a user chooses one, the API atomically marks it allocated and writes the
user ID, project ID, and a new allocation ID to the unit document. The project
also stores that allocation ID and displays it on the project page. A second
request for the same unit returns `409`.

## Hardware pool

Hardware sets live in the `hardware_sets` collection. Each set has a total
`capacity`, the units still `available` in the pool, and `max_per_user`, the
most units one user may hold at once. The `allocations` collection links a
user ID to a hardware set and the number of units that user holds.

| Endpoint | Purpose |
| --- | --- |
| `GET /api/hardware` | List sets; `held` is what the logged-in user holds |
| `POST /api/hardware` | Create a set: `{"name", "capacity", "max_per_user"}` |
| `GET /api/hardware/{id}/allocations` | Which users hold units of a set |
| `POST /api/hardware/{id}/checkout` | Claim units: `{"quantity"}` |
| `POST /api/hardware/{id}/checkin` | Return units to the pool: `{"quantity"}` |

A checkout that would exceed the units available or the per-user cap, or a
check-in of more units than the user holds, returns `409`. An unknown user or
hardware set returns `404`.

## Demo data

After setting `MONGODB_URI`, run `python -m scripts.seed_demo`. It adds the five
key-value demo records (`demo-user-001` through `demo-user-005`), login accounts
`ada`, `grace` and `alan` (password `password123`), four hardware sets, and a
few allocations. Re-running it resets the demo hardware pool.
