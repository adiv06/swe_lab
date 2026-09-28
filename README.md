# MongoDB key-value service

A small HTTP service that stores one JSON value under each string key in MongoDB.
The service owns a single database and collection, configured through environment
variables. It creates or replaces a value when you call `PUT`.

## Configure and run

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
hashed passwords. The login response contains only the public user profile.
Run the backend on port 8000, then run `npm run dev` in `frontend`; Vite forwards
`/api` requests to the backend. Project and hardware data in the frontend still
uses browser storage.

To add the five repeatable demo records (`demo-user-001` through
`demo-user-005`) after setting `MONGODB_URI`, run `python -m scripts.seed_demo`.
