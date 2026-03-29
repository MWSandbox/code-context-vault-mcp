# Code-Context-Vault (CCV) MCP
Code Context Vault (CCV) solves a real pain point in every engineering team: "Has anyone already solved this problem, or built something similar?"

Why it's cool:
- Semantic code search across your entire (company's) codebase — not just keyword matching, but meaning-aware hybrid search (vector + full-text) powered by embeddings. Find relevant code even if you don't know the exact function name.
- Works directly inside GitHub Copilot — exposed as an MCP server, so Copilot can automatically pull in relevant context from your indexed repositories while you code. No context-switching, no manual searching.
- Scales across multiple projects — index many repositories into a single pgVector database. Search across your whole company's codebase in one query.
- Incremental indexing — file checksums mean only changed files are re-processed on subsequent runs, keeping things fast and cheap.
- LLM-generated summaries — each file and project gets an AI-written description, making semantic search much more effective than raw code embeddings alone.
- Low friction to adopt — point it at any git repo, run register_project.py, and the next indexing run picks it up automatically.

In short: it turns your organization's collective codebase into a searchable knowledge base that your AI assistant can query in real time.

![Workflow](docs/Workflow.png)

## Scope of this repo

This repo contains the MCP interface to query the codebase based on the data retrieved from the code-context-vault-indexer (separate repo).

# Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `DATABASE_URL` | `postgresql+psycopg://postgres:postgres@localhost:5432/code_context_vault` | PostgreSQL connection string |

# VS Code MCP Configuration

Add to `.vscode/mcp.json` (or user `settings.json`):

```json
{
  "servers": {
    "code-context-vault": {
      "type": "sse",
      "url": "http://127.0.0.1:8000/sse"
    }
  }
}
```