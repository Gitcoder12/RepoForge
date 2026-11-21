"""Rate-limit-aware GitHub repository metadata collector.

Only public repository metadata is collected. No code is downloaded or executed.
The collector deliberately does not invent dependency or benchmark measurements.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

import requests

API_ROOT = "https://api.github.com"
ALLOWED_HOST = "api.github.com"


class GitHubAPIError(RuntimeError):
    """Raised when GitHub rejects or cannot complete a metadata request."""


class GitHubRepositoryCollector:
    def __init__(self, token: str | None = None, *, session: requests.Session | None = None,
                 timeout: float = 15.0):
        if timeout <= 0:
            raise ValueError("timeout must be positive")
        self.session = session or requests.Session()
        self.timeout = timeout
        self.session.headers.update({
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "RepoForge-Global-Repository-Intelligence",
        })
        credential = token or os.getenv("GITHUB_TOKEN")
        if credential:
            self.session.headers["Authorization"] = f"Bearer {credential}"

    def _get(self, url: str, *, params: dict[str, Any] | None = None) -> dict[str, Any]:
        parsed = urlparse(url)
        if parsed.scheme != "https" or parsed.hostname != ALLOWED_HOST:
            raise ValueError("collector only permits HTTPS requests to api.github.com")
        try:
            response = self.session.get(url, params=params, timeout=self.timeout)
        except requests.RequestException as exc:
            raise GitHubAPIError(f"GitHub request failed: {exc}") from exc
        if response.status_code == 403 and response.headers.get("X-RateLimit-Remaining") == "0":
            reset = response.headers.get("X-RateLimit-Reset", "unknown")
            raise GitHubAPIError(f"GitHub API rate limit exhausted; reset epoch: {reset}")
        if response.status_code == 401:
            raise GitHubAPIError("GitHub authentication failed; check GITHUB_TOKEN")
        if response.status_code == 403:
            raise GitHubAPIError("GitHub denied the request; check permissions and rate limits")
        if response.status_code == 422:
            raise GitHubAPIError("GitHub rejected the search query or pagination parameters")
        try:
            response.raise_for_status()
            payload = response.json()
        except (requests.HTTPError, ValueError) as exc:
            raise GitHubAPIError(f"GitHub returned an invalid response: {exc}") from exc
        if not isinstance(payload, dict):
            raise GitHubAPIError("GitHub returned an unexpected response shape")
        return payload

    def search(self, query: str, *, sort: str = "stars", order: str = "desc",
               per_page: int = 100, pages: int = 1) -> dict[str, Any]:
        """Search repositories and return normalized, timestamped evidence.

        GitHub Search caps each query at 1,000 results. Keep page count bounded
        to avoid accidental rate-limit exhaustion.
        """
        if not isinstance(query, str) or not query.strip():
            raise ValueError("query must be a non-empty GitHub repository search")
        if sort not in {"stars", "forks", "help-wanted-issues", "updated"}:
            raise ValueError("unsupported sort; use stars, forks, help-wanted-issues, or updated")
        if order not in {"asc", "desc"}:
            raise ValueError("order must be asc or desc")
        if not 1 <= per_page <= 100:
            raise ValueError("per_page must be between 1 and 100")
        if not 1 <= pages <= 10:
            raise ValueError("pages must be between 1 and 10")
        records: list[dict[str, Any]] = []
        total_count = 0
        incomplete_results = False
        for page in range(1, pages + 1):
            payload = self._get(f"{API_ROOT}/search/repositories", params={
                "q": query, "sort": sort, "order": order,
                "per_page": per_page, "page": page,
            })
            total_count = int(payload.get("total_count", 0))
            incomplete_results = bool(payload.get("incomplete_results", False))
            for repo in payload.get("items", []):
                full_name = repo.get("full_name")
                if not isinstance(full_name, str) or "/" not in full_name:
                    continue
                records.append({
                    "full_name": full_name,
                    "stars": repo.get("stargazers_count"),
                    "forks": repo.get("forks_count"),
                    "size_kb": repo.get("size"),
                    "open_issues": repo.get("open_issues_count"),
                    "archived": bool(repo.get("archived", False)),
                    "fork": bool(repo.get("fork", False)),
                    "measured_at": datetime.now(timezone.utc).isoformat(),
                    "source": "github_rest_search_repositories",
                    "source_url": repo.get("html_url"),
                    "default_branch": repo.get("default_branch"),
                    "license_spdx": (repo.get("license") or {}).get("spdx_id"),
                    "language": repo.get("language"),
                    "updated_at": repo.get("updated_at"),
                })
            if len(payload.get("items", [])) < per_page or len(records) >= min(total_count, 1000):
                break
        evidence_fields = {"full_name", "stars", "forks", "size_kb", "open_issues", "archived", "fork", "measured_at"}
        evidence_records = [
            {key: value for key, value in record.items() if key in evidence_fields}
            for record in records
        ]
        return {
            "query": query, "sort": sort, "order": order,
            "fetched_count": len(records), "reported_total_count": total_count,
            "incomplete_results": incomplete_results,
            "collected_at": datetime.now(timezone.utc).isoformat(),
            "repositories": records,
            "evidence_records": evidence_records,
            "limitations": [
                "GitHub search results are capped and may be incomplete.",
                "Dependency criticality and speed require separate evidence sources.",
                "Stars and forks measure attention, not engineering quality.",
            ],
        }


__all__ = ["GitHubAPIError", "GitHubRepositoryCollector"]
