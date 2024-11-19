"""Module to manage GitHub repository actions through the GitHub API."""

from json import JSONDecodeError
import urllib.parse
from dataclasses import dataclass
import requests
import time
import random
import string


class TokenRetrievalError(Exception):
    """Exception raised when there is an error retrieving a token from GitHub."""


class MissingRunnerLabel(Exception):
    """Exception raised when a runner does not exist in the repository."""


class RunnerListError(Exception):
    """Exception raised when there is an error getting the list of runners."""


@dataclass
class SelfHostedRunner:
    id: int
    name: str
    os: str
    labels: list[str]


class GitHubInstance:
    """Class to manage GitHub repository actions through the GitHub API.

    Parameters
    ----------
    token : str
        GitHub API token for authentication.
    repo : str
        Full name of the GitHub repository in the format "owner/repo".

    Attributes
    ----------
    headers : dict
        Headers for HTTP requests to GitHub API.
    github : Github
        Instance of Github object for interacting with the GitHub API.


    """

    BASE_URL = "https://api.github.com"

    def __init__(self, token: str, repo: str):
        self.token = token
        self.headers = self._headers({})
        self.repo = repo

    def _headers(self, header_kwargs):
        """Generate headers for API requests, adding authorization and specific API version.

        Can be removed if this is added into PyGitHub.

        Parameters
        ----------
        header_kwargs : dict
            Additional headers to include in the request.

        Returns
        -------
        dict
            Headers including authorization, API version, and any additional headers.

        """
        headers = {
            "Authorization": f"Bearer {self.token}",
            "X-Github-Api-Version": "2022-11-28",
            "Accept": "application/vnd.github+json",
        }
        headers.update(header_kwargs)
        return headers

    def _do_request(self, func, endpoint, **kwargs):
        """Make a request to the GitHub API.

        This can be removed if this is added into PyGitHub.
        """
        endpoint_url = urllib.parse.urljoin(self.BASE_URL, endpoint)
        headers = self.headers
        resp: requests.Response = func(endpoint_url, headers=headers, **kwargs)
        if not resp.ok:
            raise RuntimeError(
                f"Error in API call for {endpoint_url}: " f"{resp.content}"
            )
        else:
            try:
                return resp.json()
            except JSONDecodeError:
                return resp.content

    def create_runner_tokens(self, count: int) -> list[str]:
        """Generate registration tokens for GitHub Actions runners.
        This can be removed if this is added into PyGitHub.

        Parameters
        ----------
        count : int
            The number of runner tokens to generate.
        Returns
        -------
        list[str]
            A list of runner registration tokens.
        Raises
        ------
        TokenCreationError
            If there is an error generating the tokens.

        """
        tokens = []
        for _ in range(count):
            token = self.create_runner_token()
            tokens.append(token)
        return tokens

    def create_runner_token(self) -> str:
        """Generate a registration token for GitHub Actions runners.

        This can be removed if this is added into PyGitHub.

        Returns
        -------
        str
            A runner registration token.

        Raises
        ------
        TokenRetrievalError
            If there is an error generating the token.

        """
        try:
            res = self.post(
                f"repos/{self.repo}/actions/runners/registration-token"
            )
            return res["token"]
        except Exception as e:
            raise TokenRetrievalError(f"Error creating runner token: {e}")

    def post(self, endpoint, **kwargs):
        """Make a POST request to the GitHub API.

        This can be removed if this is added into PyGitHub.

        Parameters
        ----------
        endpoint : str
            The endpoint to make the request to.
        **kwargs : dict, optional
            Additional keyword arguments to pass to the request.
            See the requests.post documentation for more information.

        """
        return self._do_request(requests.post, endpoint, **kwargs)

    def get(self, endpoint, **kwargs):
        """Make a GET request to the GitHub API.

        Parameters
        ----------
        endpoint : str
            The endpoint to make the request to.
        **kwargs : dict, optional
            Additional keyword arguments to pass to the request.
            See the requests.get documentation for more information.
        """
        return self._do_request(requests.get, endpoint, **kwargs)

    def delete(self, endpoint, **kwargs):
        """Make a DELETE request to the GitHub API.

        Parameters
        ----------
        endpoint : str
            The endpoint to make the request to.
        **kwargs : dict, optional
            Additional keyword arguments to pass to the request.
            See the requests.delete documentation for more information.
        """
        return self._do_request(requests.delete, endpoint, **kwargs)

    def get_runners(self) -> list[SelfHostedRunner] | None:
        runners = []
        try:
            res = self.get(f"repos/{self.repo}/actions/runners")
            if type(res) is not dict:
                raise RunnerListError(f"Error getting runners: {res}")
            for runner in res["runners"]:
                id = runner["id"]
                name = runner["name"]
                os = runner["os"]
                labels = [label["name"] for label in runner["labels"]]
                runners.append(SelfHostedRunner(id, name, os, labels))
            return runners if len(runners) > 0 else None
        except Exception as e:
            raise RunnerListError(f"Error getting runners: {e}")

    def get_runner(self, label: str) -> SelfHostedRunner:
        runners = self.get_runners()
        if runners is not None:
            for runner in runners:
                if label in runner.labels:
                    return runner
        raise MissingRunnerLabel(f"Runner {label} not found")

    def wait_for_runner(self, label: str, timeout: int, wait: int = 15):
        """Wait for the runner with the given label to be online.

        Parameters
        ----------
        label : str
            The label of the runner to wait for.
        wait : int
            The time in seconds to wait between checks. Defaults to 15 seconds.
        timeout : int
            The maximum time in seconds to wait for the runner to be online.
        """
        max = time.time() + timeout
        runner = self.get_runner(label)
        while runner is None:
            if time.time() > max:
                raise RuntimeError(f"Timeout reached: Runner {label} not found")
            print(f"Runner {label} not found. Waiting...")
            runner = self.get_runner(label)
            time.sleep(wait)
        print(f"Runner {label} found!")

    def remove_runner(self, label: str):
        """Remove a runner by a given label.
        Parameters
        ----------
        label : str
            The label of the runner to remove.
        Raises
        ------
        RuntimeError
            If there is an error removing the runner or the runner is not found.
        """
        runner = self.get_runner(label)
        try:
            self.delete(f"repos/{self.repo}/actions/runners/{runner.id}")
        except Exception as e:
            raise RuntimeError(f"Error removing runner {label}. Error: {e}")

    @staticmethod
    def generate_random_label() -> str:
        """Generate a random label for a runner.

        Returns
        -------
        str
            A random label for a runner. The label is in the format
            "runner-<random_string>". The random string is 8 characters long
            and consists of lowercase letters and digits.

        """
        letters = string.ascii_lowercase + string.digits
        result_str = "".join(random.choice(letters) for i in range(8))
        return f"runner-{result_str}"

    def _get_latest_release(self, repo: str) -> dict:
        """Get the latest release for a repository.
        Parameters
        ----------
        repo : str
            The repository to get the latest release for.
        Returns
        -------
        str
            The tag name of the latest release.
        """
        try:
            release = self.get(f"repos/{repo}/releases/latest")
            return release
        except Exception as e:
            raise RuntimeError(f"Error getting latest release: {e}")

    def get_latest_runner_release(
        self, platform: str, architecture: str
    ) -> str:
        """Return the latest runner for the given platform and architecture.

        Parameters
        ----------
        platform : str
            The platform of the runner to download.
        architecture : str
            The architecture of the runner to download.

        Returns
        -------
        str
            The download URL of the runner.

        Raises
        ------
        RuntimeError
            If the runner is not found for the given platform and architecture.
        ValueError
            If the platform or architecture is not supported.

        """
        repo = "actions/runner"
        supported_platforms = {"linux": ["x64", "arm", "arm64"]}
        if platform not in supported_platforms:
            raise ValueError(
                f"Platform '{platform}' not supported. "
                f"Supported platforms are {list(supported_platforms)}"
            )
        if architecture not in supported_platforms[platform]:
            raise ValueError(
                f"Architecture '{architecture}' not supported for platform '{platform}'. "
                f"Supported architectures are {supported_platforms[platform]}"
            )
        release = self._get_latest_release(repo)
        assets = release["assets"]
        for asset in assets:
            if platform in asset["name"] and architecture in asset["name"]:
                return asset["browser_download_url"]
        raise RuntimeError(
            f"Runner release not found for platform {platform} and architecture {architecture}"
        )
