"""Hybrid search against the code-context-vault pgvector database."""

from __future__ import annotations

import os
from dataclasses import dataclass

from langchain_openai import OpenAIEmbeddings
from sqlalchemy import text

from database import get_connection


_embedding_model = OpenAIEmbeddings(
    model=os.getenv('OPENAI_EMBEDDING_MODEL', 'text-embedding-3-small'),
)


@dataclass
class SearchResult:
    id: int
    project_id: int
    path: str
    summary: str | None
    rrf_score: float


@dataclass
class Project:
    id: int
    name: str
    git_url: str
    language: str | None
    summary: str | None


@dataclass
class FunctionResult:
    id: int
    file_id: int
    project_id: int
    path: str
    name: str
    summary: str | None
    body: str
    rrf_score: float


@dataclass
class CombinedResult:
    kind: str  # 'file' or 'function'
    id: int
    project_id: int
    path: str
    name: str | None  # function/method name; None for files
    summary: str | None
    rrf_score: float


def search_files(
    query: str,
    project_id: int | None = None,
    limit: int = 10,
    file_id: int | None = None,
) -> list[SearchResult]:
    """
    Embed *query*, then call the hybrid_search_files Postgres function which
    combines semantic (cosine distance) and keyword (full-text) ranking via
    Reciprocal Rank Fusion (RRF).
    """
    embedding = _embedding_model.embed_query(query)

    with get_connection() as conn:
        rows = conn.execute(
            text(
                """
                SELECT id, project_id, path, summary, rrf_score
                FROM hybrid_search_files(
                    :embedding ::vector,
                    :query_text,
                    :project_id,
                    :match_count,
                    60,
                    :file_id
                )
                """
            ),
            {
                'embedding': embedding,
                'query_text': query,
                'project_id': project_id,
                'match_count': limit,
                'file_id': file_id,
            },
        ).fetchall()

    return [
        SearchResult(
            id=row.id,
            project_id=row.project_id,
            path=row.path,
            summary=row.summary,
            rrf_score=row.rrf_score,
        )
        for row in rows
    ]


def search_functions(
    query: str,
    project_id: int | None = None,
    limit: int = 10,
) -> list[FunctionResult]:
    """
    Embed *query*, then call the hybrid_search_functions Postgres function which
    combines semantic (cosine distance) and keyword (full-text) ranking via
    Reciprocal Rank Fusion (RRF) to surface the most relevant functions.
    """
    embedding = _embedding_model.embed_query(query)

    with get_connection() as conn:
        rows = conn.execute(
            text(
                """
                SELECT id, file_id, project_id, path, name, summary, body, rrf_score
                FROM hybrid_search_functions(
                    :embedding ::vector,
                    :query_text,
                    :project_id,
                    :match_count
                )
                """
            ),
            {
                'embedding': embedding,
                'query_text': query,
                'project_id': project_id,
                'match_count': limit,
            },
        ).fetchall()

    return [
        FunctionResult(
            id=row.id,
            file_id=row.file_id,
            project_id=row.project_id,
            path=row.path,
            name=row.name,
            summary=row.summary,
            body=row.body,
            rrf_score=row.rrf_score,
        )
        for row in rows
    ]


def search_code(
    query: str,
    project_id: int | None = None,
    limit: int = 10,
) -> list[CombinedResult]:
    """
    Embed *query* once, then run hybrid_search_files and hybrid_search_functions
    in parallel within a single connection, merge the results and re-rank by
    rrf_score so the most relevant hits—whether files or functions—surface first.
    """
    embedding = _embedding_model.embed_query(query)
    candidate_limit = limit * 2

    with get_connection() as conn:
        file_rows = conn.execute(
            text(
                """
                SELECT id, project_id, path, summary, rrf_score
                FROM hybrid_search_files(
                    :embedding ::vector,
                    :query_text,
                    :project_id,
                    :match_count
                )
                """
            ),
            {
                'embedding': embedding,
                'query_text': query,
                'project_id': project_id,
                'match_count': candidate_limit,
            },
        ).fetchall()

        func_rows = conn.execute(
            text(
                """
                SELECT id, project_id, path, name, summary, rrf_score
                FROM hybrid_search_functions(
                    :embedding ::vector,
                    :query_text,
                    :project_id,
                    :match_count
                )
                """
            ),
            {
                'embedding': embedding,
                'query_text': query,
                'project_id': project_id,
                'match_count': candidate_limit,
            },
        ).fetchall()

    results: list[CombinedResult] = [
        CombinedResult(
            kind='file',
            id=row.id,
            project_id=row.project_id,
            path=row.path,
            name=None,
            summary=row.summary,
            rrf_score=row.rrf_score,
        )
        for row in file_rows
    ] + [
        CombinedResult(
            kind='function',
            id=row.id,
            project_id=row.project_id,
            path=row.path,
            name=row.name,
            summary=row.summary,
            rrf_score=row.rrf_score,
        )
        for row in func_rows
    ]

    results.sort(key=lambda r: r.rrf_score, reverse=True)
    return results[:limit]


@dataclass
class FileContent:
    id: int
    project_id: int
    path: str
    body: str | None


def get_file_content(file_id: int) -> FileContent | None:
    """
    Fetch the stored source content for a single file by its *file_id*.
    Returns None when no matching file is found.
    """
    with get_connection() as conn:
        row = conn.execute(
            text('SELECT id, project_id, path, body FROM files WHERE id = :file_id'),
            {'file_id': file_id},
        ).fetchone()

    if row is None:
        return None

    return FileContent(
        id=row.id,
        project_id=row.project_id,
        path=row.path,
        body=row.body,
    )


def list_projects() -> list[Project]:
    """Return all indexed projects."""
    with get_connection() as conn:
        rows = conn.execute(
            text('SELECT id, name, git_url, language, summary FROM projects ORDER BY name')
        ).fetchall()

    return [
        Project(
            id=row.id,
            name=row.name,
            git_url=row.git_url,
            language=row.language,
            summary=row.summary,
        )
        for row in rows
    ]
