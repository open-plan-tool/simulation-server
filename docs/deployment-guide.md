# Deploy on a New Machine

For a local Linux setup. Install **Docker, Minikube, kubectl, Git,
Node.js 22/npm, Python 3, and OpenSSL** first. Docker must work without `sudo`.

## 1. Switch the Existing Checkout

Open a terminal in the repository. Check `git status --short` and preserve local
changes before switching branches. Do not commit credentials.

```bash
git fetch origin
git switch daceds+mosaik
git pull --ff-only origin daceds+mosaik
git submodule update --init --recursive
```

If the branch exists only on `origin`, `git switch` normally creates a local
tracking branch. The maintainer must publish the complete integration first.
If switching or pulling fails, stop and resolve it without a hard reset.
Keep all subsequent commands in this repository directory.

## 2. Add Credentials

Keep an existing `.env`; create it from the example only if missing:

```bash
if [ ! -f .env ]; then cp .env.example .env; fi
chmod 600 .env
openssl rand -hex 32
```

Edit `.env` locally:

- `AUTH_DISABLED=true`: local login without OIDC, using a shared development account.
- `OIDC_CLIENT_ID` and `OIDC_CLIENT_SECRET`: may be blank in local mode
- `DB_PASSWORD`: choose a local database password.
- `SESSION_SECRET`: use the generated random value.

Quote shell-special characters. Never commit `.env`. On an existing machine,
keep the existing file and database password. OIDC is enabled by default; use the
local-login bypass only on a trusted local machine, never a public deployment.

## 3. Create Local Certificates

Skip this if valid certificates already exist in `data/certs`.

```bash
mkdir -p data/certs
openssl req -x509 -newkey rsa:2048 -nodes -days 365 \
  -keyout data/certs/key.pem -out data/certs/cert.pem \
  -subj "/CN=localhost" \
  -addext "subjectAltName=DNS:localhost,IP:127.0.0.1"
chmod 600 data/certs/key.pem
```

## 4. Start Minikube and Mount Data

The resource allocation below is a starting point; your host needs spare memory
and tens of GiB of free Docker storage.

```bash
minikube start --driver=docker --container-runtime=docker --cpus=4 --memory=12288 --dns-domain=cluster.local
kubectl config use-context minikube
minikube mount "$(pwd)/data:/data"
```

**Leave this terminal running.** Uploads and results use the mounted `data/`
directory. PostgreSQL and Redis use separate cluster volumes.

## 5. Build and Deploy

In a second terminal:

```bash
bash build-minikube.sh
```

This builds the frontend, backend, DaceDSX worker, wrappers, and Mosaik worker.
The Mosaik editor and Orbit use prebuilt registry images. The first SUMO build
can take a long time.

Check startup before opening the app:

```bash
kubectl -n simservice get pods,jobs
kubectl -n kafka get pods
kubectl -n simservice rollout status deployment/web --timeout=300s
kubectl -n simservice rollout status deployment/mosaik-gui --timeout=300s
```

Service pods should become Ready and the migration job should complete.

## 6. Open the Apps

Run each command in its own terminal and leave it running:

```bash
kubectl -n simservice port-forward service/web 5001:5001
```

```bash
kubectl -n simservice port-forward service/mosaik-gui 8002:80
```

- **Main app:** https://localhost:5001
- **Mosaik editor:** http://localhost:8002

Expect a browser warning for the self-signed certificate. Sign in and choose a
framework. Keep access local; do not expose these forwards publicly.

Test one Pandapower run, one SUMO run, and one known-good Mosaik scenario. Verify
completion and downloads. The maintainers supplied these Save/Load-enabled images;
verify the buttons and scenario execution after deployment:

```text
registry.gitlab.com/mosaik/mosaik-gui/frontend:nfdi4energy-simaas
registry.gitlab.com/mosaik/mosaik-gui/mosaik-orbit:nfdi4energy-simaas
```

The GUI image is named `frontend`; its service remains `mosaik-gui`. A Compose
`MOSAIK_ORBIT_IMAGE` override takes precedence over the default Orbit image.

## Later Updates

Keep the mount running and finish active simulations before updating:

```bash
bash build-minikube.sh
```

The full script runs every local image build, reusing Docker's cached layers when
possible, applies the manifest, and restarts deployments. Keep the existing `.env`
and database password. Back up PostgreSQL before migrations, and review cluster
overrides because applying the manifest restores declared settings.

<details>
<summary>If something fails</summary>

- **Missing certificate:** check the mount is still running.
- **Migration timeout:** PostgreSQL may not be ready yet. Inspect the migration
  job logs, wait for PostgreSQL, then rerun the migration job. Do not delete its PVC.
- **Image pull error:** check registry access and the image reference in pod events.
- **Empty SUMO dependencies:** run `git submodule update --init --recursive`.
- **DNS errors:** the cluster domain must be `cluster.local`, not `8.8.8.8`.
- **Port occupied:** stop your previous port-forward before starting another.

</details>

Fresh-machine deployment and the new upstream images still need runtime
verification. Keep access local: Mosaik scenarios are not sandboxed. Back up both
PostgreSQL and `data/`; the host data directory alone does not preserve ownership.
