# Running and deploying the console

## On your own machine

```bash
./run.sh
```

Then open <http://localhost:8000>. That builds the console if needed and
serves it with the API from one process on one port. Nothing else to start.

To use a different port: `PORT=9000 ./run.sh`

While editing the console itself, `npm --prefix web run dev` gives hot reload
against the same API on port 8000.

## Why not Vercel

Vercel is built for a static frontend plus short-lived serverless functions.
This application is a poor fit for that shape:

- The audit engine loads the YAML registry on every call. On serverless that
  is re-read per cold start, and the registry has to be bundled into the
  function rather than living beside the code.
- `/hygiene` fetches around twenty live pages and takes 8-15 seconds. Vercel's
  Hobby plan caps a function at 10 seconds, so that route would time out.
- The report routes accept file uploads, which serverless handles awkwardly
  and with a smaller body limit.

You could split it — console on Vercel, API elsewhere — but that adds CORS,
two deployments and two sets of logs for no gain over a single container.

## Where it does fit

The `Dockerfile` builds one image containing both the API and the console.
Any of these will run it from a GitHub push:

| Host | Free tier | Notes |
|---|---|---|
| **Railway** | $5 credit/month | Detects the Dockerfile, deploys on push. Simplest. |
| **Render** | Free web service | Sleeps when idle; roughly 30 seconds to wake. |
| **Fly.io** | Small VMs | Scales to zero. More configuration up front. |

### Railway, step by step

1. Sign in at <https://railway.app> with GitHub.
2. **New Project** → **Deploy from GitHub repo** → `county-blog-authority`.
3. Railway finds the `Dockerfile` on its own. No build command needed.
4. Under **Variables**, leave `PORT` unset — the container reads whatever
   Railway provides.
5. Under **Settings → Networking**, click **Generate Domain**.

The first deploy takes a few minutes because it builds the React bundle and
installs Python dependencies. Afterwards, every push to `main` redeploys.

### Confirming a deploy worked

```bash
curl https://<your-domain>/health
```

You want `"status":"ok"` and `"registry_errors":[]`. An empty error list
matters as much as the status: it means every project file parsed, so the
audit engine is actually enforcing its facts rather than running with a
partly-loaded registry.

## Before it is public

There is no authentication. That is a deliberate choice for now — the pricing
and RERA data it exposes are published on countygroup.in anyway — but two
things are worth knowing:

- `/projects` also returns the internal editorial rules and the
  `needs_human_review` notes, which are working material rather than
  published fact.
- The upload routes accept files from anyone who finds the URL. They are
  capped and written to a temporary file that is deleted afterwards, but an
  open endpoint is still an open endpoint.

If either matters, put HTTP basic auth in front of it. That is about an
hour's work and does not need the app to change.

## Docker locally

Docker is not installed on the machine where this was built, so the image has
only been verified by CI, not run by hand. If you have Docker:

```bash
docker build -t county-console .
docker run -p 8000:8000 county-console
```

The CI workflow (`.github/workflows/console.yml`) builds the image, starts the
container and calls `/health`, so a green run means the image genuinely serves
rather than merely compiling.
