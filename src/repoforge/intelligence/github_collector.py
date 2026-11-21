"""Rate-limit-aware GitHub repository metadata collector.

Only public repository metadata is collected. No code is downloaded or executed.
The collector deliberately does not invent dependency or benchmark measurements.
"""
from __future__ import annotations

import math
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
    def __init__(
        self,
        token: str | None = None,
        *,
        session: requests.Session | None = None,
        timeout: float = 15.0,
    ):
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or (
            not math.isfinite(timeout) or timeout <= 0
        ):
            raise ValueError("timeout must be a finite positive number")
        if token is not None and (not isinstance(token, str) or not token.strip()):
            raise ValueError("token must be a non-empty string or None")
        self.session = session or requests.Session()
        self.timeout = float(timeout)
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
        if parsed.scheme != "https" or parsed.hostname != ALLOWED_HOST or parsed.port not in (None, 443):
            raise ValueError("collector only permits HTTPS requests to api.github.com:443")
        try:
            # Redirects are disabled: validate every network destination, not only the first URL.
            response = self.session.get(
                url, params=params, timeout=self.timeout, allow_redirects=False
            )
        except requests.RequestException as exc:
            raise GitHubAPIError(f"GitHub request failed: {type(exc).__name__}") from exc
        if 300 <= response.status_code < 400:
            raise GitHubAPIError("GitHub returned an unexpected redirect; request was not followed")
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
            raise GitHubAPIError(f"GitHub returned an invalid response: {type(exc).__name__}") from exc
        if not isinstance(payload, dict):
            raise GitHubAPIError("GitHub returned an unexpected response shape")
        return payload

    def search(
        self,
        query: str,
        *,
        sort: str = "stars",
        order: str = "desc",
        per_page: int = 100,
        pages: int = 1,
    ) -> dict[str, Any]:
        """Search repositories and return normalized, timestamped evidence.

        GitHub Search caps each query at 1,000 results. Pagination is bounded
        to reduce accidental rate-limit exhaustion.
        """
        if not isinstance(query, str) or not query.strip():
            raise ValueError("query must be a non-empty GitHub repository search")
        if sort not in {"stars", "forks", "help-wanted-issues", "updated"}:
            raise ValueError("unsupported repository search sort")
        if order not in {"asc", "desc"}:
            raise ValueError("order must be asc or desc")
        if isinstance(per_page, bool) or not isinstance(per_page, int) or not 1 <= per_page <= 100:
            raise ValueError("per_page must be an integer between 1 and 100")
        if isinstance(pages, bool) or not isinstance(pages, int) or not 1 <= pages <= 10:
            raise ValueError("pages must be an integer between 1 and 10")

        records: list[dict[str, Any]] = []
        seen: set[str] = set()
        total_count = 0
        incomplete_results = False
        for page in range(1, pages + 1):
            payload = self._get(f"{API_ROOT}/search/repositories", params={
                "q": query, "sort": sort, "order": order,
                "per_page": per_page, "page": page,
            })
            try:
                raw_total = payload.get("total_count", 0)
                if isinstance(raw_total, bool) or not isinstance(raw_total, int) or raw_total < 0:
                    raise ValueError("total_count must be a non-negative integer")
                raw_items = payload.get("items", [])
                if not isinstance(raw_items, list):
                    raise ValueError("items must be a list")
                total_count = raw_total
                incomplete_results = bool(payload.get("incomplete_results", False))
            except (TypeError, ValueError) as exc:
                raise GitHubAPIError(f"GitHub returned malformed search metadata: {exc}") from exc

            for repo in raw_items:
                if not isinstance(repo, dict):
                    continue
                full_name = repo.get("full_name")
                if not isinstance(full_name, str) or full_name.count("/") != 1:
                    continue
                key = full_name.casefold()
                if key in seen:
                    continue
                seen.add(key)
                license_info = repo.get("license")
                license_spdx = (
                    license_info.get("spdx_id")
                    if isinstance(license_info, dict) else None
                )
                records.append({
                    "full_name": full_name,
                    "stars": repo.get("stargazers_count"),
                    "forks": repo.get("forks_count"),
                    "size_kb": repo.get("size"),
                    "open_issues": repo.get("open_issues_count"),
                    "archived": repo.get("archived") is True,
                    "fork": repo.get("fork") is True,
                    "measured_at": datetime.now(timezone.utc).isoformat(),
                    "source": "github_rest_search_repositories",
                    "source_url": repo.get("html_url"),
                    "default_branch": repo.get("default_branch"),
                    "license_spdx": license_spdx,
                    "language": repo.get("language"),
                    "updated_at": repo.get("updated_at"),
                })
            if len(raw_items) < per_page or len(records) >= min(total_count, 1000):
                break

        evidence_fields = {
            "full_name", "stars", "forks", "size_kb", "open_issues",
            "archived", "fork", "measured_at",
        }
        evidence_records = [
            {key: value for key, value in record.items() if key in evidence_fields}
            for record in records
        ]
        return {
            "query": query,
            "sort": sort,
            "order": order,
            "fetched_count": len(records),
            "reported_total_count": total_count,
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
