import pytest
from unittest.mock import Mock, patch
from gha_runner.clouddeployment import (
    CreateCloudInstance,
    DeployInstance,
    StopCloudInstance,
    TeardownInstance,
)
from gha_runner.gh import GitHubInstance, MissingRunnerLabel


class MockStartCloudInstance(CreateCloudInstance):
    def __init__(self, **kwargs):
        self.instances = {"i-123": "runner-1"}

    def create_instances(self):
        return self.instances

    def wait_until_ready(self, ids, **kwargs):
        pass

    def set_instance_mapping(self, mapping):
        pass


class MockStopCloudInstance(StopCloudInstance):
    def __init__(self):
        self.instances = {"i-123": "runner-1"}

    def remove_instances(self, ids):
        pass

    def get_instance_mapping(self):
        return self.instances

    def wait_until_removed(self, ids, **kwargs):
        pass

class MockFailableWaitStop(StopCloudInstance):
    def __init__(self):
        self.instances = {"i-123": "runner-1"}

    def remove_instances(self, ids):
        pass

    def get_instance_mapping(self):
        return self.instances

    def wait_until_removed(self, ids, **kwargs):
        raise Exception("Bad wait")


@pytest.fixture
def gh_mock():
    gh_mock = Mock(spec=GitHubInstance)
    gh_mock.create_runner_tokens.return_value = ["token1"]
    gh_mock.get_latest_runner_release.return_value = "https://github.com/actions/runner/releases/download/v2.278.0/actions-runner-linux-x64-2.278.0.tar.gz"
    yield gh_mock


@pytest.fixture
def deploy_instance(gh_mock):
    deploy = DeployInstance(
        provider_type=MockStartCloudInstance,
        cloud_params={},
        gh=gh_mock,
        count=1,
        timeout=30,
    )
    yield deploy


def test_deploy_instance_creation(deploy_instance, gh_mock):
    assert isinstance(deploy_instance.provider, MockStartCloudInstance)
    gh_mock.create_runner_tokens.assert_called_once_with(1)
    gh_mock.get_latest_runner_release.assert_called_once()


def test_deploy_instance_start_runners(deploy_instance, gh_mock):
    deploy_instance.start_runner_instances()
    gh_mock.wait_for_runner.assert_called_once_with("runner-1", 30)


def test_teardown_instance_stop_runner(gh_mock):
    teardown = TeardownInstance(
        provider_type=MockStopCloudInstance,
        cloud_params={},
        gh=gh_mock,
    )
    teardown.stop_runner_instances()
    gh_mock.remove_runner.assert_called_once_with("runner-1")


def test_teardown_instance_missing(gh_mock):
    gh_mock.remove_runner.side_effect = MissingRunnerLabel("runner-1")

    teardown = TeardownInstance(
        provider_type=MockStopCloudInstance,
        cloud_params={},
        gh=gh_mock,
    )
    teardown.stop_runner_instances()  # No exception raised


def test_teardown_instance_malformed_instance_mapping(gh_mock):
    provider_mock = Mock(spec=MockStopCloudInstance)
    provider_mock.get_instance_mapping.side_effect = Exception("Bad mapping")
    with pytest.raises(SystemExit) as exit_info:
        teardown = TeardownInstance(
            # Using a lambda to return the mock instance,
            # since we can't use the mock instance directly
            provider_type=lambda **kwargs: provider_mock,
            cloud_params={},
            gh=gh_mock,
        )
        teardown.stop_runner_instances()
    assert exit_info.value.code == 1


def test_teardown_instance_failure(gh_mock, capsys):
    gh_mock.remove_runner.side_effect = Exception("Testing")
    teardown = TeardownInstance(
        provider_type=MockStopCloudInstance,
        cloud_params={},
        gh=gh_mock,
    )
    teardown.stop_runner_instances()
    captured = capsys.readouterr()
    catpured_output = captured.out
    expected_output = ["Shutting down...",
        "Removing GitHub Actions Runner",
        "Removing runner runner-1",
        "::warning title=Failed to remove runner::Testing",
        "Removing instances...",
        "Waiting for instance to be removed...",
        "Instances removed!"
    ]
    actual_output = catpured_output.strip().split("\n")
    assert actual_output == expected_output

def test_teardown_instance_failed_wait(gh_mock, capsys):
    with pytest.raises(SystemExit) as exit_info:
        teardown = TeardownInstance(
            # Using a lambda to return the mock instance,
            # since we can't use the mock instance directly
            provider_type=MockFailableWaitStop,
            cloud_params={},
            gh=gh_mock,
        )
        teardown.stop_runner_instances()
    captured = capsys.readouterr()
    catpured_output = captured.out
    expected_output = [
        "Shutting down...",
        "Removing GitHub Actions Runner",
        "Removing runner runner-1",
        "Removing instances...",
        "Waiting for instance to be removed...",
        "Failed to remove instances check your provider console: Bad wait",
        "::error title=Failed to remove instances, check your provider console::Bad wait",
    ]
    actual_output = catpured_output.strip().split("\n")
    assert actual_output == expected_output
    assert exit_info.value.code == 1
