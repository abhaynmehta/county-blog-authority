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
5. **Add a volume mounted at `/data`.** This is not optional if you want the
   audit history to mean anything: a container filesystem is wiped on every
   deploy, so without it the ledger resets each time you push and the whole
   point of tracking repeat mistakes is lost. The image already sets
   `COUNTY_DATA_DIR=/data`, so mounting the volume is the only step.
6. Under **Settings → Networking**, click **Generate Domain**.

### What persists, and what does not

| Data | Where it lives | Survives a deploy |
|---|---|---|
| Project registry, claims, URLs | `county_context/`, in git | Yes — it ships in the image |
| Audit history ledger | `/data`, the mounted volume | Only with the volume |
| Generated reports and dashboard | container filesystem | No, and that is fine — regenerate them |
| Uploaded CSVs | temporary file, deleted after the request | No, by design |

Only the ledger needs the volume. Everything else is either in git or
cheaply regenerated.

The first deploy takes a few minutes because it builds the React bundle and
installs Python dependencies. Afterwards, every push to `main` redeploys.

### Confirming a deploy worked

```bash
curl https://<your-domain>/health
```

Three things to check in that response:

- `"status":"ok"` — the app started.
- `"registry_errors":[]` — every project file parsed. This matters as much
  as the status: a registry that fails to load leaves the engine running
  with partly-loaded facts rather than erroring, so an empty list is what
  tells you it is genuinely enforcing anything.
- `"storage":{"durable":true}` — the volume is mounted. If this says
  `false`, the app works but audit history resets on every deploy, and the
  response carries a `warning` saying so.

CI asserts all three against a running container, so a green build means the
image serves rather than merely compiling.

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
