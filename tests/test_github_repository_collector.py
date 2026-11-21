from unittest.mock import Mock

import pytest
import requests

from repoforge.intelligence.github_collector import (
    GitHubAPIError,
    GitHubRepositoryCollector,
)


def response(payload, status=200, headers=None):
    item = Mock()
    item.status_code = status
    item.headers = headers or {}
    item.json.return_value = payload
    item.raise_for_status.return_value = None
    return item


def session_with_response(result):
    session = Mock(spec=requests.Session)
    session.headers = {}
    session.get.return_value = result
    return session


def test_search_normalizes_metadata_and_marks_limitations():
    session = session_with_response(response({
        "total_count": 1,
        "incomplete_results": False,
        "items": [{
            "full_name": "owner/project",
            "stargazers_count": 50,
            "forks_count": 4,
            "size": 1024,
            "open_issues_count": 2,
            "archived": False,
            "fork": False,
            "html_url": "https://github.com/owner/project",
            "default_branch": "main",
            "license": {"spdx_id": "MIT"},
            "language": "Python",
            "updated_at": "2026-01-01T00:00:00Z",
        }],
    }))
    result = GitHubRepositoryCollector(session=session).search("language:python", pages=1)
    assert result["fetched_count"] == 1
    assert result["repositories"][0]["full_name"] == "owner/project"
    assert result["repositories"][0]["stars"] == 50
    assert "not engineering quality" in result["limitations"][2]


@pytest.mark.parametrize("kwargs", [
    {"query": ""},
    {"query": "python", "per_page": 101},
    {"query": "python", "per_page": True},
    {"query": "python", "pages": 11},
    {"query": "python", "pages": True},
    {"query": "python", "sort": "unknown"},
])
def test_rejects_invalid_search_parameters(kwargs):
    with pytest.raises(ValueError):
        GitHubRepositoryCollector(session=Mock()).search(**kwargs)


@pytest.mark.parametrize("timeout", [0, -1, float("nan"), float("inf"), True])
def test_rejects_invalid_timeout(timeout):
    with pytest.raises(ValueError):
        GitHubRepositoryCollector(timeout=timeout, session=Mock())


def test_rate_limit_is_reported_without_retry_storm():
    session = session_with_response(response({}, 403, {
        "X-RateLimit-Remaining": "0",
        "X-RateLimit-Reset": "123",
    }))
    with pytest.raises(GitHubAPIError, match="rate limit exhausted"):
        GitHubRepositoryCollector(session=session).search("python")
    session.get.assert_called_once()


def test_redirects_are_not_followed():
    session = session_with_response(response({}, 302, {"Location": "https://evil.example"}))
    with pytest.raises(GitHubAPIError, match="redirect"):
        GitHubRepositoryCollector(session=session).search("python")
    assert session.get.call_args.kwargs["allow_redirects"] is False


def test_malformed_license_metadata_does_not_crash_collection():
    session = session_with_response(response({
        "total_count": 1,
        "items": [{"full_name": "owner/project", "license": "MIT"}],
    }))
    result = GitHubRepositoryCollector(session=session).search("python")
    assert result["repositories"][0]["license_spdx"] is None


def test_duplicate_repositories_across_pages_are_deduplicated():
    session = session_with_response(response({
        "total_count": 2,
        "items": [
            {"full_name": "owner/project"},
            {"full_name": "OWNER/PROJECT"},
        ],
    }))
    result = GitHubRepositoryCollector(session=session).search("python")
    assert result["fetched_count"] == 1


def test_only_github_api_host_is_allowed():
    collector = GitHubRepositoryCollector(session=Mock())
    for url in (
        "http://api.github.com/steal",
        "https://example.com/steal",
        "https://api.github.com.evil.example/steal",
        "https://api.github.com:444/steal",
    ):
        with pytest.raises(ValueError):
            collector._get(url)
