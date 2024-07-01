import re
import pytest
from unittest.mock import patch, MagicMock, Mock

from gha_runner.gh import TokenRetrievalError, GitHubInstance, MissingRunnerLabel
from github.SelfHostedActionsRunner import SelfHostedActionsRunner


@pytest.fixture
def github_release_mock():
    # Create MagicMocks for components not directly patched
    mock_release = MagicMock()
    mock_asset = MagicMock()
    mock_runners = MagicMock()
    runner = MagicMock(spec=SelfHostedActionsRunner)
    runner2 = MagicMock(spec=SelfHostedActionsRunner)

    # Setup fixed attributes for mocks
    asset_name = "runner-linux-x64.tar.gz"
    asset_url = "https://github.com/testing/runner-linux-x64.tar.gz"
    mock_asset.name = asset_name
    mock_asset.browser_download_url = asset_url
    runner.labels.return_value = [{"name": "runner-linux-x64"}]
    runner2.labels.return_value = [{"name": "runner-linux-x64"}]
    mock_runners.__iter__.return_value = [runner, runner2]

    # Using patch as a context manager inside the fixture
    with patch("gha_runner.gh.Github") as mock_github:
        mock_repo = MagicMock()
        mock_github.return_value.get_repo.return_value = mock_repo
        mock_repo.get_latest_release.return_value = mock_release
        mock_repo.get_self_hosted_runners.return_value = mock_runners
        mock_release.get_assets.return_value = [mock_asset]
        mock_repo.remove_self_hosted_runner.return_value = True

        instance = GitHubInstance("test", "testing/testing")

        yield instance, mock_asset, mock_repo


@pytest.mark.parametrize(
    "platform, architecture, expected, raises, match_msg",
    [
        # Test case where the latest release exists
        (
            "linux",
            "x64",
            "https://github.com/testing/runner-linux-x64.tar.gz",
            None,
            None,
        ),
        # Test case where the platform is not supported
        (
            "darwin",
            "x64",
            None,
            ValueError,
            "Platform 'darwin' not supported. Supported platforms are ['linux']",
        ),
        # Test case where the architecture is not supported
        (
            "linux",
            "armv7",
            None,
            ValueError,
            "Architecture 'armv7' not supported for platform 'linux'. Supported architectures are ['x64', 'arm', 'arm64']",
        ),
        # Test case where the latest release does not exist
        (
            "linux",
            "arm",
            None,
            RuntimeError,
            "Runner release not found for platform linux and architecture arm",
        ),
    ],
)
def test_get_latest_runner_release(
    github_release_mock, platform, architecture, expected, raises, match_msg
):
    instance, _, _ = github_release_mock
    if raises:
        msg = re.escape(match_msg)
        with pytest.raises(raises, match=msg):
            instance.get_latest_runner_release(platform, architecture)
    else:
        result = instance.get_latest_runner_release(platform, architecture)
        assert result == expected, f"Expected URL {expected} but got {result}"


@pytest.mark.parametrize(
    "label, expected",
    [
        # Test case where the runner exists
        ("runner-linux-x64", SelfHostedActionsRunner),
        # Test case where the runner does not exist
        ("runner-darwin-x64", None),
    ],
)
def test_get_runner(github_release_mock, label, expected):
    instance, _, _ = github_release_mock
    result = instance.get_runner(label)
    if expected:
        assert isinstance(result, expected)
    assert (result is not None) == (expected is not None)


def test_get_runners(github_release_mock):
    instance, _, _ = github_release_mock
    runners = instance.get_runners("runner-linux-x64")
    assert len(runners) == 2
    assert isinstance(runners[0], SelfHostedActionsRunner)
    assert isinstance(runners[1], SelfHostedActionsRunner)


@pytest.mark.parametrize(
    "label, error, match",
    [
        ("runner-linux-x64", None, None),
        (
            "runner-darwin-x64",
            RuntimeError,
            "Runner runner-darwin-x64 not found",
        ),
    ],
)
def test_remove_runners(github_release_mock, label, error, match):
    instance, _, mock_repo = github_release_mock
    if error:
        with pytest.raises(MissingRunnerLabel, match=match):
            instance.remove_runners(label)
    else:
        instance.remove_runners(label)
        assert mock_repo.remove_self_hosted_runner.call_count == 2


def test_remove_runners_fail(github_release_mock):
    instance, _, mock_repo = github_release_mock
    mock_repo.remove_self_hosted_runner.return_value = False
    with pytest.raises(
        RuntimeError, match="Error removing runner runner-linux-x64"
    ):
        instance.remove_runners("runner-linux-x64")


@pytest.mark.parametrize(
    "label, error, match",
    [
        ("runner-linux-x64", None, None),
        (
            "runner-linux-x64",
            RuntimeError,
            "Error removing runner runner-linux-x64",
        ),
        (
            "non-existent-runner",
            MissingRunnerLabel,
            "Runner non-existent-runner not found",
        ),
    ],
)
def test_remove_runner(github_release_mock, label, error, match):
    instance, _, mock_repo = github_release_mock
    if error:
        mock_repo.remove_self_hosted_runner.return_value = False
        with pytest.raises(error, match=match):
            instance.remove_runner(label)
    else:
        instance.remove_runner(label)
        mock_repo.remove_self_hosted_runner.assert_called_once()


def test_headers(github_release_mock):
    """Tests that headers get set correctly."""
    instance, _, _ = github_release_mock
    headers = {
        "Authorization": f"Bearer {instance.token}",
        "X-Github-Api-Version": "2022-11-28",
        "Accept": "application/vnd.github+json",
    }
    assert instance.headers == headers


@pytest.mark.parametrize(
    "status_code, ok, content, error, match",
    [
        (200, True, None, None, None),
        (
            404,
            False,
            "Not Found",
            RuntimeError,
            "Error in API call for https://api.github.com/mock/test: Not Found",
        ),
    ],
)
def test_do_request(
    github_release_mock, status_code, ok, content, error, match
):
    import requests

    instance, _, _ = github_release_mock
    mock_response = Mock(spec=requests.Response)
    mock_response.status_code = status_code
    mock_response.json.return_value = {
        "token": "LLBF3JGZDX3P5PMEXLND6TS6FCWO6",
        "expires_at": "2020-01-22T12:13:35.123-08:00",
    }
    mock_response.ok = ok
    mock_response.content = content
    endpoint = "/mock/test"
    with patch("requests.get", return_value=mock_response) as mock_func:
        if error:
            with pytest.raises(error, match=match):
                instance._do_request(mock_func, endpoint)
        else:
            response = instance._do_request(mock_func, endpoint)
            assert response == mock_response.json.return_value


@pytest.fixture
def post_fixture(github_release_mock):
    import requests

    instance, _, _ = github_release_mock
    mock_response = Mock(spec=requests.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "token": "LLBF3JGZDX3P5PMEXLND6TS6FCWO6",
        "expires_at": "2020-01-22T12:13:35.123-08:00",
    }
    with patch("requests.post", return_value=mock_response):
        yield instance, mock_response


def test_post(post_fixture):
    instance, mock_response = post_fixture
    response = instance.post("https://api.github.com", data={"key": "value"})
    assert response == mock_response.json.return_value
    mock_response.json.assert_called_once()


@pytest.mark.parametrize(
    "status_code, ok, content, error",
    [(200, True, None, None), (404, False, "Not Found", TokenRetrievalError)],
)
def test_create_runner_token(post_fixture, status_code, ok, content, error):
    instance, mock_response = post_fixture
    mock_response.status_code = status_code
    mock_response.ok = ok
    mock_response.content = content
    error_str = f"Error creating runner token: Error in API call for https://api.github.com/repos/testing/testing/actions/runners/registration-token: {mock_response.content}"
    if error:
        with pytest.raises(error, match=error_str):
            instance.create_runner_token()
    else:
        response = instance.create_runner_token()
        assert response == mock_response.json.return_value["token"]
        mock_response.json.assert_called_once()


@pytest.fixture
def post_fixture_multi(monkeypatch):
    import requests

    responses = [
        {
            "status_code": 200,
            "json": {
                "token": "LLBF3JGZDX3P5PMEXLND6TS6FCWO6",
                "expires_at": "2020-01-22T12:13:35.123-08:00",
            },
        },
        {
            "status_code": 200,
            "json": {
                "token": "LLBF3JGZDX3P5PMEXLND6TS6FCWO7",
                "expires_at": "2020-01-22T12:13:35.123-08:00",
            },
        },
        {
            "status_code": 200,
            "json": {
                "token": "LLBF3JGZDX3P5PMEXLND6TS6FCWO8",
                "expires_at": "2020-01-22T12:13:35.123-08:00",
            },
        },
    ]

    def side_effect(*args, **kwargs):
        response = responses.pop(0)
        mock_response = Mock(spec=requests.Response)
        mock_response.status_code = response["status_code"]
        mock_response.json.return_value = response["json"]
        return mock_response

    mock = Mock(side_effect=side_effect)
    monkeypatch.setattr(requests, "post", mock)
    return mock, responses


def test_create_github_runners(github_release_mock, post_fixture_multi):
    instance, _, _ = github_release_mock
    json_mock, responses = post_fixture_multi
    count = len(responses)
    out = instance.create_runner_tokens(count)
    assert len(out) == count
    for idx, resp in enumerate(responses):
        assert out[idx] == resp["json"]["token"]

    assert json_mock.call_count == count


@pytest.fixture
def post_fixture_multi_fail(monkeypatch):
    import requests

    responses = [
        {
            "status_code": 200,
            "json": {
                "token": "LLBF3JGZDX3P5PMEXLND6TS6FCWO6",
                "expires_at": "2020-01-22T12:13:35.123-08:00",
            },
        },
        {
            "status_code": 404,
            "json": {
                "message": "Not Found",
            },
        },
    ]

    def side_effect(*args, **kwargs):
        response = responses.pop(0)
        mock_response = Mock(spec=requests.Response)
        mock_response.status_code = response["status_code"]
        mock_response.json.return_value = response["json"]
        mock_response.ok = response["status_code"] == 200
        return mock_response

    mock = Mock(side_effect=side_effect)
    monkeypatch.setattr(requests, "post", mock)
    return mock, responses


def test_create_github_runners_exception(
    github_release_mock, post_fixture_multi_fail
):
    instance, _, _ = github_release_mock
    json_mock, responses = post_fixture_multi_fail
    count = len(responses)
    with pytest.raises(TokenRetrievalError):
        instance.create_runner_tokens(count)
        assert json_mock.call_count == count


def test_generate_random_label(github_release_mock):
    instance, _, _ = github_release_mock
    with patch("random.choice", return_value="a"):
        label = instance.generate_random_label()
        assert label == f"runner-{'a'*8}"


@pytest.fixture
def mock_get_runner(monkeypatch):
    label = "runner-linux-x64"
    side_effect = [None, None, {"label": label}]
    missing_str = f"Runner {label} not found. Waiting...\n"
    found_str = f"Runner {label} found!\n"
    # Dynamically build out the expected calls based on the side_effect
    expected_calls = [
        missing_str if x is None else found_str for x in side_effect
    ]

    get_runner_mock = MagicMock()
    # Setup the side_effect for the get_runner_mock
    get_runner_mock.side_effect = side_effect
    monkeypatch.setattr(GitHubInstance, "get_runner", get_runner_mock)
    return get_runner_mock, label, expected_calls


def test_wait_for_runner(github_release_mock, mock_get_runner, capsys):
    instance, _, _ = github_release_mock
    get_runner_mock, label, expected_calls = mock_get_runner
    instance.wait_for_runner(label, wait=1)
    captured = capsys.readouterr()
    # Combine all expected calls into a single string
    combined = "".join(expected_calls)

    # Validate that the expected output matches the captured output
    assert captured.out == combined
    # Validate that the get_runner method was called the correct number of times
    assert get_runner_mock.call_count == len(expected_calls)
