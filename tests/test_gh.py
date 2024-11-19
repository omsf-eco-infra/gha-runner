import pytest
from unittest.mock import Mock, patch
import responses
from gha_runner.gh import (
    GitHubInstance,
    SelfHostedRunner,
    TokenRetrievalError,
    MissingRunnerLabel,
    RunnerListError,
)


@pytest.fixture
def github_instance():
    return GitHubInstance(token="fake-token", repo="test/test")


@pytest.fixture
def mock_runner():
    return SelfHostedRunner(
        id=1, name="test-runner", os="linux", labels=["test-label"]
    )


def test_init(github_instance):
    assert github_instance.token == "fake-token"
    assert github_instance.repo == "test/test"
    assert github_instance.BASE_URL == "https://api.github.com"


def test_headers(github_instance):
    headers = github_instance._headers({})
    assert headers["Authorization"] == "Bearer fake-token"
    assert headers["X-Github-Api-Version"] == "2022-11-28"
    assert headers["Accept"] == "application/vnd.github+json"


@responses.activate
def test_create_runner_token(github_instance):
    responses.add(
        responses.POST,
        "https://api.github.com/repos/test/test/actions/runners/registration-token",
        json={"token": "test-token"},
        status=200,
    )
    token = github_instance.create_runner_token()
    assert token == "test-token"


@responses.activate
def test_create_runner_token_error(github_instance):
    responses.add(
        responses.POST,
        "https://api.github.com/repos/test/test/actions/runners/registration-token",
        status=400,
    )
    with pytest.raises(TokenRetrievalError):
        github_instance.create_runner_token()


@responses.activate
def test_create_runner_tokens(github_instance):
    tokens = ["test-token-1", "test-token-2", "test-token-3"]
    for token in tokens:
        responses.add(
            responses.POST,
            "https://api.github.com/repos/test/test/actions/runners/registration-token",
            json={"token": token},
            status=200,
        )
    assert github_instance.create_runner_tokens(3) == tokens


@responses.activate
def test_get_runners(github_instance):
    responses.add(
        responses.GET,
        "https://api.github.com/repos/test/test/actions/runners",
        json={
            "runners": [
                {
                    "id": 1,
                    "name": "test-runner",
                    "os": "linux",
                    "labels": [{"name": "test-label"}],
                }
            ]
        },
        status=200,
    )
    runners = github_instance.get_runners()
    assert len(runners) == 1
    assert runners[0].id == 1
    assert runners[0].name == "test-runner"
    assert runners[0].labels == ["test-label"]


@responses.activate
def test_get_runners_empty(github_instance):
    responses.add(
        responses.GET,
        "https://api.github.com/repos/test/test/actions/runners",
        json={"runners": []},
        status=200,
    )
    assert github_instance.get_runners() is None


@responses.activate
def test_get_runners_no_json(github_instance):
    responses.add(
        responses.GET,
        "https://api.github.com/repos/test/test/actions/runners",
        body="",
        status=200,
    )
    with pytest.raises(RunnerListError, match="Error getting runners: *"):
        github_instance.get_runners()


@responses.activate
def test_get_runners_error(github_instance):
    responses.add(
        responses.GET,
        "https://api.github.com/repos/test/test/actions/runners",
        status=500,
    )
    with pytest.raises(RunnerListError, match="Error getting runners: *"):
        github_instance.get_runners()


def test_get_runner_by_label(github_instance, mock_runner):
    with patch.object(
        github_instance, "get_runners", return_value=[mock_runner]
    ):
        runner = github_instance.get_runner("test-label")
        assert runner.id == 1
        assert runner.name == "test-runner"


def test_get_runner_missing_label(github_instance):
    with patch.object(github_instance, "get_runners", return_value=[]):
        with pytest.raises(MissingRunnerLabel):
            github_instance.get_runner("nonexistent-label")


@responses.activate
def test_remove_runner(github_instance, mock_runner):
    with patch.object(github_instance, "get_runner", return_value=mock_runner):
        responses.add(
            responses.DELETE,
            f"https://api.github.com/repos/test/test/actions/runners/{mock_runner.id}",
            status=204,
        )
        github_instance.remove_runner("test-label")


@responses.activate
def test_remove_runner_error(github_instance, mock_runner):
    with patch.object(github_instance, "get_runner", return_value=mock_runner):
        responses.add(
            responses.DELETE,
            f"https://api.github.com/repos/test/test/actions/runners/{mock_runner.id}",
            status=500,
        )
        with pytest.raises(RuntimeError):
            github_instance.remove_runner("test-label")


def test_generate_random_label():
    label = GitHubInstance.generate_random_label()
    assert label.startswith("runner-")
    assert len(label) == 15  # "runner-" + 8 random chars


@responses.activate
def test_get_latest_runner_release(github_instance):
    responses.add(
        responses.GET,
        "https://api.github.com/repos/actions/runner/releases/latest",
        json={
            "assets": [
                {
                    "name": "actions-runner-linux-x64-2.0.0.tar.gz",
                    "browser_download_url": "https://example.com/runner.tar.gz",
                }
            ]
        },
        status=200,
    )
    url = github_instance.get_latest_runner_release("linux", "x64")
    assert url == "https://example.com/runner.tar.gz"


def test_get_latest_runner_release_invalid_platform(github_instance):
    with pytest.raises(ValueError):
        github_instance.get_latest_runner_release("invalid", "x64")


def test_get_latest_runner_release_invalid_arch(github_instance):
    with pytest.raises(ValueError):
        github_instance.get_latest_runner_release("linux", "invalid")


@patch("time.sleep")  # Prevent actual sleeping in tests
def test_wait_for_runner_success(mock_sleep, github_instance, mock_runner):
    with patch.object(
        github_instance, "get_runner", side_effect=[None, mock_runner]
    ):
        github_instance.wait_for_runner("test-label", timeout=30)
        assert mock_sleep.call_count == 1


@patch("time.sleep")
@patch("time.time", side_effect=[0, 31])
def test_wait_for_runner_timeout(mock_time, mock_sleep, github_instance):
    with patch.object(github_instance, "get_runner", return_value=None):
        with pytest.raises(RuntimeError):
            github_instance.wait_for_runner("test-label", timeout=30)


@responses.activate
def test_get_latest_release(github_instance):
    json = {
        "url": "https://api.github.com/repos/octocat/Hello-World/releases/1",
        "html_url": "https://github.com/octocat/Hello-World/releases/v1.0.0",
        "assets_url": "https://api.github.com/repos/octocat/Hello-World/releases/1/assets",
        "upload_url": "https://uploads.github.com/repos/octocat/Hello-World/releases/1/assets{?name,label}",
        "tarball_url": "https://api.github.com/repos/octocat/Hello-World/tarball/v1.0.0",
        "zipball_url": "https://api.github.com/repos/octocat/Hello-World/zipball/v1.0.0",
        "discussion_url": "https://github.com/octocat/Hello-World/discussions/90",
        "id": 1,
        "assets": [
            {
                "url": "https://api.github.com/repos/octocat/Hello-World/releases/assets/1",
                "browser_download_url": "https://github.com/octocat/Hello-World/releases/download/v1.0.0/example.zip",
                "id": 1,
                "node_id": "MDEyOlJlbGVhc2VBc3NldDE=",
                "name": "example.zip",
                "label": "short description",
                "state": "uploaded",
                "content_type": "application/zip",
                "size": 1024,
                "download_count": 42,
                "created_at": "2013-02-27T19:35:32Z",
                "updated_at": "2013-02-27T19:35:32Z",
                "uploader": {
                    "login": "octocat",
                    "id": 1,
                    "node_id": "MDQ6VXNlcjE=",
                    "avatar_url": "https://github.com/images/error/octocat_happy.gif",
                    "gravatar_id": "",
                    "url": "https://api.github.com/users/octocat",
                    "html_url": "https://github.com/octocat",
                    "followers_url": "https://api.github.com/users/octocat/followers",
                    "following_url": "https://api.github.com/users/octocat/following{/other_user}",
                    "gists_url": "https://api.github.com/users/octocat/gists{/gist_id}",
                    "starred_url": "https://api.github.com/users/octocat/starred{/owner}{/repo}",
                    "subscriptions_url": "https://api.github.com/users/octocat/subscriptions",
                    "organizations_url": "https://api.github.com/users/octocat/orgs",
                    "repos_url": "https://api.github.com/users/octocat/repos",
                    "events_url": "https://api.github.com/users/octocat/events{/privacy}",
                    "received_events_url": "https://api.github.com/users/octocat/received_events",
                    "type": "User",
                    "site_admin": False,
                },
            }
        ],
    }
    responses.add(
        responses.GET,
        "https://api.github.com/repos/actions/runner/releases/latest",
        status=200,
        json=json,
    )
    body = github_instance._get_latest_release(repo="actions/runner")
    assert body == json


@responses.activate
def test_get_latest_release_error(github_instance):
    responses.add(
        responses.GET,
        "https://api.github.com/repos/actions/runner/releases/latest",
        status=500,
    )
    with pytest.raises(RuntimeError, match="Error getting latest release: *"):
        github_instance._get_latest_release(repo="actions/runner")


@responses.activate
def test_get_latest_reunner_release_error(github_instance):
    responses.add(
        responses.GET,
        "https://api.github.com/repos/actions/runner/releases/latest",
        status=200,
        json={
            "assets": [
                {
                    "name": "actions-runner-linux-aarch64-2.0.0.tar.gz",
                    "browser_download_url": "https://example.com/runner.tar.gz",
                }
            ]
        },
    )
    platform = "linux"
    arch = "x64"
    responses.add(
        responses.GET,
        "https://api.github.com/repos/actions/runner/releases/latest",
        status=500,
    )
    with pytest.raises(
        RuntimeError,
        match=f"Runner release not found for platform {platform} and architecture {arch}",
    ):
        github_instance.get_latest_runner_release("linux", "x64")
