# Cloudflare deployment for the MVC module

**Status:** Proposed for review
**Date:** 2026-10-03

## Goal

Deploy only `architectures/mvc` from `aikitr/aikitr-python-template` as a Cloudflare Python Worker. A push to `main` should publish a new version only when files under `architectures/mvc/` change. The task API should retain its current HTTP behavior and persist data across Worker instances.

## Chosen approach

Use Cloudflare Python Workers to host the existing FastAPI API, Cloudflare D1 for persistent task data, and Cloudflare Workers Builds for GitHub-based build and deployment.

The Worker will use Cloudflare's FastAPI ASGI adapter and D1 binding. The existing SQLite-backed SQLAlchemy setup remains the local development and test backend. The Worker runtime uses an asynchronous D1 repository behind the same task operations, so its API contract and task state rules remain consistent with the local app. D1 schema changes use versioned SQL migrations.

The Worker and D1 resource names will be `aikitr-mvc-api` and `aikitr-mvc-tasks`. The Wrangler configuration and Worker entry point will live inside `architectures/mvc`, keeping other architecture examples outside the deployment root.

## GitHub deployment

Connect the existing GitHub repository `aikitr/aikitr-python-template` to Cloudflare Workers Builds with:

- Production branch: `main`.
- Root directory: `/architectures/mvc`.
- Included watch path: `architectures/mvc/**`.
- Build command: sync the locked Python environment and prepare the Python Worker bundle.
- Deploy command: apply pending D1 migrations remotely, then deploy the Worker with Pywrangler.

Cloudflare's Git integration will publish automatically after matching pushes. Changes outside `architectures/mvc/` will not start this Worker build. Preview deployments are out of scope for the initial setup.

## Runtime behavior and data

The deployed app will keep the current task endpoints and error semantics. The Worker entry point will adapt a FastAPI app through Cloudflare's ASGI support. The D1 repository will use the Worker database binding; it will not depend on a local SQLite file, local filesystem persistence, or an external database credential.

The D1 migration creates the task table and primary key matching the existing model; the current model has no secondary indexes. Deployment applies pending migrations before publishing a new Worker version. Local development continues to use the current SQLite URL and Alembic workflow.

## Validation and completion criteria

- Build the Python Worker locally with Pywrangler.
- Verify the deployed `/health` route and task CRUD routes at the Cloudflare Worker URL.
- Verify that task records remain available after separate requests.
- Confirm the Cloudflare build configuration points to `main`, uses `/architectures/mvc` as root, and watches only `architectures/mvc/**`.
- Confirm a GitHub push touching the MVC module triggers a build, while a change outside the module does not.

## Boundaries

This work does not deploy the other architecture modules, add a custom domain, configure a frontend, or change the public task API. It does not add a separate GitHub Actions workflow; Cloudflare Workers Builds owns the Git-triggered deployment.

## Operational note

The app currently uses synchronous SQLAlchemy sessions over a local SQLite file. Cloudflare's Python Worker runtime uses Pyodide and a D1 binding, so the cloud persistence path requires an explicit D1 adapter rather than reusing the local file database. Python package versions must be compatible with Python Workers and Pyodide.
