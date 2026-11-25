---
name: new-service
description: Scaffold and verify a new Python service repository with the igarape CLI. The default is an in-memory FastAPI API configured for Codex, with optional PostgreSQL, Redis and Kafka or RabbitMQ. Use for "novo serviço", "novo repositório", "scaffold", "criar projeto", "bootstrap", "new service".
---

# New service

1. Use the inputs already provided. Ask for the project name if missing. Default to Python 3.13,
   `../<slug>` as the destination, the in-memory profile and the `codex` agent. Enable the
   integrations and agents requested for the service. Use Copier's defaults for the description
   and owning team unless provided.
2. Run the CLI from this checkout:
   ```bash
   uv run --locked igarape new "<target-dir>" --template . --name "<name>"
   ```
   Pass requested metadata via `--description`, `--author` and `--python`, agents via `--agent`
   (repeatable), integrations via `--postgres`, `--redis` and `--broker`, and selected HTTPS
   endpoints via `--mcp NAME=URL`. The CLI prepares the new Git repository and lockfile. Point it
   at a new directory.
3. In the generated repository, run `make bootstrap` and `make check`. Integration profiles
   require a running Docker daemon for their tests. If a step fails, investigate the environment
   and dependencies before attributing the failure to the template.
4. Once validation passes, create the initial local commit:
   `git add -A && git commit -m "chore: scaffold with igarape"`.
5. Report the generated profile, the checks run, and how to start the app. The in-memory profile
   starts with `make run`. For infrastructure profiles, follow the generated README.
