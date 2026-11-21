from unittest.mock import Mock
import pytest
import requests
from repoforge.intelligence.github_collector import GitHubAPIError, GitHubRepositoryCollector


def response(payload, status=200, headers=None):
    item = Mock()
    item.status_code = status
    item.headers = headers or {}
    item.json.return_value = payload
    item.raise_for_status.return_value = None
    return item


def test_search_normalizes_metadata_and_marks_limitations():
    session = Mock(spec=requests.Session)
    session.headers = {}
    session.get.return_value = response({
        "total_count": 1, "incomplete_results": False,
        "items": [{
            "full_name": "owner/project", "stargazers_count": 50, "forks_count": 4,
            "size": 1024, "open_issues_count": 2, "archived": False, "fork": False,
            "html_url": "https://github.com/owner/project", "default_branch": "main",
            "license": {"spdx_id": "MIT"}, "language": "Python",
            "updated_at": "2026-01-01T00:00:00Z",
        }],
    })
    result = GitHubRepositoryCollector(session=session).search("language:python", pages=1)
    assert result["fetched_count"] == 1
    assert result["repositories"][0]["full_name"] == "owner/project"
    assert result["repositories"][0]["stars"] == 50
    assert "not engineering quality" in result["limitations"][2]


@pytest.mark.parametrize("kwargs", [
    {"query": ""}, {"query": "python", "per_page": 101},
    {"query": "python", "pages": 11}, {"query": "python", "sort": "unknown"},
])
def test_rejects_invalid_search_parameters(kwargs):
    with pytest.raises(ValueError):
        GitHubRepositoryCollector(session=Mock()).search(**kwargs)


def test_rate_limit_is_reported_without_retry_storm():
    session = Mock(spec=requests.Session)
    session.headers = {}
    session.get.return_value = response({}, 403, {
        "X-RateLimit-Remaining": "0", "X-RateLimit-Reset": "123",
    })
    with pytest.raises(GitHubAPIError, match="rate limit exhausted"):
        GitHubRepositoryCollector(session=session).search("python")
    session.get.assert_called_once()


def test_only_github_api_host_is_allowed():
    collector = GitHubRepositoryCollector(session=Mock())
    with pytest.raises(ValueError):
        collector._get("https://example.com/steal")
