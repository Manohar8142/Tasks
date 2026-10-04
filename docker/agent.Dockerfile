# The environment an agent works in for one task.
#
#   docker build -f docker/agent.Dockerfile --build-arg TASK=ttlcache-expired-entries -t task-env .
#   docker run --rm -it --network none task-env
#
# Only the pre-fix repo is copied in. hidden_tests/, solution.patch and
# alt_solutions/ never enter this image, so the agent cannot read them.
FROM python:3.11-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends git \
 && rm -rf /var/lib/apt/lists/* \
 && pip install --no-cache-dir pytest==8.3.3 \
 && useradd --create-home agent

ARG TASK
COPY --chown=agent:agent tasks/${TASK}/repo /workspace
COPY --chown=agent:agent tasks/${TASK}/issue.md /issue.md

USER agent
WORKDIR /workspace
RUN git init -q \
 && printf '__pycache__/\n*.pyc\n.pytest_cache/\n' > .git/info/exclude \
 && git -c user.name=env -c user.email=env@localhost add -A \
 && git -c user.name=env -c user.email=env@localhost commit -qm "pre-fix baseline"

CMD ["bash"]
