# Project Scope
This is a project to implement a MCP server for github copilot usage. The MCP server can use hybrid search to query an existing pgvector database for more context information.

## Structure

```
src/
  server.py   – FastMCP entry point; defines the two MCP tools
  search.py   – embeds queries and calls hybrid_search_files() in Postgres
  database.py – SQLAlchemy connection helper (reads DATABASE_URL env var)
pyproject.toml
```

## Tools Exposed

| Tool | Description |
|------|-------------|
| `search_code` | Hybrid semantic + full-text search over indexed source files. Args: `query`, optional `project_id`, optional `limit`. |
| `list_projects` | Returns all indexed projects (id, name, git_url, language, summary). |

## Running Locally

```bash
# install deps
uv sync

# start the server (stdio transport for VS Code Copilot)
uv run python src/server.py
```


