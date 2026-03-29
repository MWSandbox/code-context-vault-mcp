"""MCP server exposing hybrid code search over the code-context-vault database."""

from __future__ import annotations

from dataclasses import asdict

from mcp.server.fastmcp import FastMCP

import search as search_module


mcp = FastMCP(
    'ccv',
    instructions=(
        'Use list_projects to retrieve all indexed projects (id, name, git_url, language, summary). '
        'Use search_code to search across both files and functions at once when user did not specify explicitly where to look for. '
        'Use search_files to find relevant source files by natural language query. '
        'Use search_functions to find relevant functions or methods by natural language query. '
        'All search tools support an optional project_id filter from list_projects and an optional limit. '
        'Results include a kind field ("file" or "function"), path, LLM-generated summary, and a relevance score. '
        'Use get_file_content with the id from a search result to retrieve the full raw source of a file. '
        'Prefer calling get_file_content whenever the user wants to read, understand, or replicate an existing implementation — '
        'do not guess at the file content from the summary alone.'
    ),
    host='127.0.0.1',
    port=8000,
)


@mcp.tool()
def search_code(
    query: str,
    project_id: int | None = None,
    limit: int = 10,
) -> list[dict]:
    """
    Search across both indexed source files and functions using hybrid semantic + keyword search.

    Embeds the query once, runs hybrid RRF search over files and functions,
    then merges and re-ranks the results by score. Use this when unsure whether
    the relevant code lives in a file summary or a specific function.

    Args:
        query: Natural language description of what you are looking for.
        project_id: Optional project ID to restrict search to a single repo.
        limit: Maximum number of results to return (default 10).

    Returns:
        List of matching results with kind ("file" or "function"), path, name,
        summary, project_id, and rrf_score, sorted by relevance.
    """
    results = search_module.search_code(query, project_id=project_id, limit=limit)
    return [asdict(r) for r in results]


@mcp.tool()
def search_files(
    query: str,
    project_id: int | None = None,
    limit: int = 10,
) -> list[dict]:
    """
    Search indexed source files using hybrid semantic + keyword search.

    Combines vector (cosine) similarity and full-text ranking via Reciprocal
    Rank Fusion (RRF) to surface the most relevant files for a query.

    Args:
        query: Natural language description of what you are looking for.
        project_id: Optional project ID to restrict search to a single repo.
        limit: Maximum number of results to return (default 10).

    Returns:
        List of matching files with path, summary, project_id, and rrf_score.
    """
    results = search_module.search_files(query, project_id=project_id, limit=limit)
    return [asdict(r) for r in results]


@mcp.tool()
def search_functions(
    query: str,
    project_id: int | None = None,
    limit: int = 10,
) -> list[dict]:
    """
    Search indexed functions and methods using hybrid semantic + keyword search.

    Combines vector (cosine) similarity and full-text ranking via Reciprocal
    Rank Fusion (RRF) to surface the most relevant functions for a query.

    Args:
        query: Natural language description of what you are looking for.
        project_id: Optional project ID to restrict search to a single repo.
        limit: Maximum number of results to return (default 10).

    Returns:
        List of matching functions with name, path, summary, project_id, and rrf_score.
    """
    results = search_module.search_functions(query, project_id=project_id, limit=limit)
    return [asdict(r) for r in results]


@mcp.tool()
def get_file_content(file_id: int) -> dict | None:
    """
    Retrieve the full source content of an indexed file by its ID.

    Use this after search_files or search_code to inspect the actual source
    of a result — for example to understand an implementation before writing
    something similar.

    Args:
        file_id: The id field from a search_files or search_code result.

    Returns:
        Dict with id, project_id, path, and body (raw file content), or None
        if the file ID does not exist.
    """
    result = search_module.get_file_content(file_id)
    return asdict(result) if result is not None else None


@mcp.tool()
def list_projects() -> list[dict]:
    """
    List all projects indexed in the code-context-vault database.

    Returns:
        List of projects with id, name, git_url, language, and summary.
    """
    projects = search_module.list_projects()
    return [asdict(p) for p in projects]


if __name__ == '__main__':
    mcp.run(transport='sse')
