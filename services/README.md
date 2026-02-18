# Services Container Security Decisions

This document summarizes the security decisions used to build and run the Docker images for:

- `services/ui`
- `services/api`
- `services/worker`

## 1) Use Multi-Stage Builds

All service Dockerfiles use a two-stage build:

- **Builder stage** installs dependencies from `requirements.txt` into `/install`.
- **Runtime stage** starts fresh and copies only what is required to run.

Why this is used:

- Keeps build-time tooling out of production images.
- Reduces runtime attack surface.
- Improves image hygiene and maintainability.

## 2) Use Minimal Runtime Base Images

Each service uses `python:3.12-slim` as the runtime base image.

Why this is used:

- Smaller footprint than full Python images.
- Fewer OS packages and binaries available to attackers.
- Faster pulls and deployments.

## 3) Run as Non-Root

Each Dockerfile creates and uses a non-root account:

- `appuser` / `appgroup`
- `UID:GID 1000:1000`

Why this is used:

- Limits privilege escalation risk.
- Reduces impact if an application process is compromised.
- Aligns with Kubernetes restricted pod security expectations.

## 4) Avoid Embedding Secrets

Secrets are not hardcoded into source code or Dockerfiles.
Runtime configuration is injected via environment variables.

Examples:

- `API_URL`
- `WORKER_URL`
- `LOG_LEVEL`


## 5) Minimise Image Size

Several decisions reduce image size:

- Multi-stage builds
- Slim base image
- `pip install --no-cache-dir`
- Copying only required runtime artifacts

Why this is used:

- Smaller images reduce attack surface.
- Faster image transfer and startup.
- Lower registry and node storage usage.

## 6) Avoid Unnecessary Packages

Dependencies are kept minimal and only include what is needed to run each service.
No extra build tools are intentionally kept in final runtime images.

Why this is used:

- Fewer components to patch and monitor.
- Lower vulnerability count in image scans.

## 7) Use Pinned Dependency Versions

Python dependencies are pinned in each service `requirements.txt`.

Why this is used:

- Reproducible and deterministic builds.
- Lower risk from unexpected breaking updates.
- Better supply-chain control and auditability.

## 8) Follow Container Hardening Best Practices

The images and runtime settings follow practical hardening patterns:

- Run as non-root user
- Minimal base image
- No embedded secrets
- Multi-stage build separation
- Structured logs to stdout/stderr for centralized monitoring
- Health endpoints (`/healthz`, `/readyz`) to support safe orchestration behavior

Additional Kubernetes hardening in this project includes:

- Restricted pod security settings
- Dropped Linux capabilities
- Disallowed privilege escalation
- Read-only root filesystem (with writable `/tmp` volume)
- Network policies for traffic control

## Folder-Level Security Intent

Service folders are intentionally separated:

- `services/ui`: external-facing web UI logic only
- `services/api`: internal API and orchestration logic
- `services/worker`: internal processing logic

This separation supports least privilege and clearer network/security boundaries when deployed on Kubernetes.

