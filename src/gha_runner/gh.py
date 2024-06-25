"""Module to manage GitHub repository actions through the GitHub API."""

from github import Github, Auth
from github.SelfHostedActionsRunner import SelfHostedActionsRunner
import urllib.parse
import requests
import time
import random
import string


class TokenRetrievalError(Exception):
    """Exception raised when there is an error retrieving a token from GitHub."""

class MissingRunnerLabel(Exception):
    """Exception raised when a runner does not exist in the repository."""


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
        auth = Auth.Token(token)
        self.github = Github(auth=auth)
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
            return resp.json()

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

    def get_runner(self, label: str) -> SelfHostedActionsRunner | None:
        """Retrieve a runner by its label.

        Parameters
        ----------
        label : str
            The label of the runner to retrieve.

        Returns
        -------
        SelfHostedActionsRunner | None
            The runner object if found, otherwise None.

        """
        runners = self.github.get_repo(self.repo).get_self_hosted_runners()
        matched_runners = [
            runner
            for runner in runners
            if label in [l["name"] for l in runner.labels()]
        ]
        return matched_runners[0] if matched_runners else None

    def get_runners(self, label: str) -> list[SelfHostedActionsRunner] | None:
        """Get runners by their label.
        Parameters
        ----------
        label : str
            The label of the runners to retrieve.
        Returns
        -------
        list[SelfHostedActionsRunner] | None
            The list of runners if found, otherwise None.
        """
        runners = self.github.get_repo(self.repo).get_self_hosted_runners()
        matched_runners = [
            runner
            for runner in runners
            if label in [l["name"] for l in runner.labels()]
        ]
        return matched_runners if matched_runners else None

    def wait_for_runner(self, label: str, wait: int = 15):
        """Wait for the runner with the given label to be online.

        Parameters
        ----------
        label : str
            The label of the runner to wait for.
        wait : int
            The time in seconds to wait between checks. Defaults to 15 seconds.

        """
        runner = self.get_runner(label)
        while runner is None:
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
        if runner is not None:
            removed = self.github.get_repo(self.repo).remove_self_hosted_runner(
                runner
            )
            if not removed:
                raise RuntimeError(f"Error removing runner {label}")
        else:
            raise MissingRunnerLabel(f"Runner {label} not found")

    def remove_runners(self, label: str):
        """Remove runners by their label.

        Parameters
        ----------
        label : str
            The label of the runners to remove.

        Raises
        ------
        RuntimeError
            If there is an error removing the runners or the runners are not found.

        """
        runners = self.get_runners(label)
        if runners is not None:
            for runner in runners:
                removed = self.github.get_repo(
                    self.repo
                ).remove_self_hosted_runner(runner)
                if not removed:
                    raise RuntimeError(f"Error removing runner {label}")
        else:
            raise MissingRunnerLabel(f"Runner {label} not found")

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

        """
        repo = "actions/runner"
        release = self.github.get_repo(repo).get_latest_release()
        assets = release.get_assets()
        for asset in assets:
            if platform in asset.name and architecture in asset.name:
                return asset.browser_download_url
        raise RuntimeError(
            f"Runner not found for {platform} and {architecture}"
        )
