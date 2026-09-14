# AGENTS.md

## Project Environment

- Repository root: `E:\study\data-agent\data-agent`
- Shell: PowerShell
- Python environment: Conda env `dataagent`
- Python env path: `D:\MyProgram\anaconda\envs\dataagent`

Activate Python environment before development:

```powershell
conda activate dataagent
```

## Docker Services

Project services are managed with:

```powershell
docker compose -f E:\study\data-agent\data-agent\docker\docker-compose.yaml ps
```

Expected local services:

- Elasticsearch: `localhost:9200`
- Kibana: `localhost:5601`
- MySQL: `localhost:3307` mapped to container `3306`
- Qdrant: `localhost:6333` and `localhost:6334`
- Embedding service: `localhost:8081` mapped to container `80`

## Guidance For Codex

- Keep changes minimal and scoped to the requested task.
- Match existing project style before introducing new patterns.
- Prefer verifying changes with the project's existing tests or checks when available.
