# Image used by DockerSandbox to run hidden tests against a patched workspace.
# The workspace and results plugin are bind-mounted at run time; nothing
# task-specific is baked in. Run with --network none (DockerSandbox does).
FROM python:3.11-slim

RUN pip install --no-cache-dir pytest==8.3.3

WORKDIR /workspace
