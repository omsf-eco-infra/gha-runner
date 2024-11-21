from abc import ABC, abstractmethod
from gha_runner.gh import GitHubInstance, MissingRunnerLabel
from gha_runner.helper import warning, error
from dataclasses import dataclass, field
from typing import Type


class CreateCloudInstance(ABC):
    """Abstract base class for starting a cloud instance.

    This class defines the interface for starting a cloud instance.

    """

    @abstractmethod
    def create_instances(self) -> dict[str, str]:
        """Create instances in the cloud provider and return their IDs.

        The number of instances to create is defined by the implementation.

        Returns
        -------
        dict[str, str]
            A dictionary of instance IDs and their corresponding github runner labels.

        """
        raise NotImplementedError

    @abstractmethod
    def wait_until_ready(self, ids: list[str], **kwargs):
        """Wait until instances are in a ready state.

        Parameters
        ----------
        ids : list[str]
            A list of instance IDs to wait for.
        **kwargs : dict, optional
            Additional arguments to pass to the waiter.

        """
        raise NotImplementedError

    @abstractmethod
    def set_instance_mapping(self, mapping: dict[str, str]):
        """Set the instance mapping in the environment.

        Parameters
        ----------
        mapping : dict[str, str]
            A dictionary of instance IDs and their corresponding github runner labels.

        """
        raise NotImplementedError


class StopCloudInstance(ABC):
    """Abstract base class for stopping a cloud instance.

    This class defines the interface for stopping a cloud instance.

    """

    @abstractmethod
    def remove_instances(self, ids: list[str]):
        """Remove instances from the cloud provider.

        Parameters
        ----------
        ids : list[str]
            A list of instance IDs to remove.

        """
        raise NotImplementedError

    @abstractmethod
    def wait_until_removed(self, ids: list[str], **kwargs):
        """Wait until instances are removed.

        Parameters
        ----------
        ids : list[str]
            A list of instance IDs to wait for.
        **kwargs : dict, optional
            Additional arguments to pass to the waiter.

        """
        raise NotImplementedError

    @abstractmethod
    def get_instance_mapping(self) -> dict[str, str]:
        """Get the instance mapping from the environment.

        Returns
        -------
        dict[str, str]
            A dictionary of instance IDs and their corresponding github runner labels.

        """
        raise NotImplementedError


@dataclass
class DeployInstance:
    """Class that is used to deploy instances and runners.

    Parameters
    ----------
    provider_type : Type[CreateCloudInstance]
        The type of cloud provider to use.
    cloud_params : dict
        The parameters to pass to the cloud provider.
    gh : GitHubInstance
        The GitHub instance to use.
    count : int
        The number of instances to create.
    timeout : int
        The timeout to use when waiting for the runner to come online


    Attributes
    ----------
    provider : CreateCloudInstance
        The cloud provider instance
    provider_type : Type[CreateCloudInstance]
    cloud_params : dict
    gh : GitHubInstance
    count : int
    timeout : int

    """

    provider_type: Type[CreateCloudInstance]
    cloud_params: dict
    gh: GitHubInstance
    count: int
    timeout: int
    provider: CreateCloudInstance = field(init=False)

    def __post_init__(self):
        """Initialize the cloud provider.

        This function is called after the object is created to correctly
        init the provider.

        """
        # We need to create runner tokens for use by the provider
        runner_tokens = self.gh.create_runner_tokens(self.count)
        self.cloud_params["gh_runner_tokens"] = runner_tokens
        release = self.gh.get_latest_runner_release(
            platform="linux", architecture="x64"
        )
        self.cloud_params["runner_release"] = release
        self.provider = self.provider_type(**self.cloud_params)

    def start_runner_instances(self):
        """Start the runner instances.

        This function starts the runner instances and waits for them to be ready.

        """
        print("Starting up...")
        # Create a GitHub instance
        print("Creating GitHub Actions Runner")

        mappings = self.provider.create_instances()
        instance_ids = list(mappings.keys())
        github_labels = list(mappings.values())
        # Output the instance mapping and labels so the stop action can use them
        self.provider.set_instance_mapping(mappings)
        # Wait for the instance to be ready
        print("Waiting for instance to be ready...")
        self.provider.wait_until_ready(instance_ids)
        print("Instance is ready!")
        # Confirm the runner is registered with GitHub
        for label in github_labels:
            print(f"Waiting for {label}...")
            self.gh.wait_for_runner(label, self.timeout)


@dataclass
class TeardownInstance:
    """Class that is used to teardown instances and runners.

    Parameters
    ----------
    provider_type : Type[StopCloudInstance]
        The type of cloud provider to use.
    cloud_params : dict
        The parameters to pass to the cloud provider.
    gh : GitHubInstance
        The GitHub instance to use.

    Attributes
    ----------
    provider : StopCloudInstance
        The cloud provider instance
    provider_type : Type[StopCloudInstance]
    cloud_params : dict
    gh : GitHub

    """

    provider_type: Type[StopCloudInstance]
    cloud_params: dict
    gh: GitHubInstance
    provider: StopCloudInstance = field(init=False)

    def __post_init__(self):
        """Initialize the cloud provider.

        This function is called after the object is created to correctly
        stop the provider.

        """
        self.provider = self.provider_type(**self.cloud_params)

    def stop_runner_instances(self):
        """Stop the runner instances.

        This function stops the runner instances and waits for them to be removed.

        """
        print("Shutting down...")
        try:
            # Get the instance mapping from our input
            mappings = self.provider.get_instance_mapping()
        except Exception as e:
            error(title="Malformed instance mapping", message=e)
            exit(1)
        # Remove the runners and instances
        print("Removing GitHub Actions Runner")
        instance_ids = list(mappings.keys())
        labels = list(mappings.values())
        for label in labels:
            try:
                print(f"Removing runner {label}")
                self.gh.remove_runner(label)
            # This occurs when we have a runner that might already be shutdown.
            # Since we are mainly using the ephemeral runners, we expect this to happen
            except MissingRunnerLabel:
                print(f"Runner {label} does not exist, skipping...")
                continue
            # This is more of the case when we have a failure to remove the runner
            # This is not a concern for the user (because we will remove the instance anyways),
            # but we should log it for debugging purposes.
            except Exception as e:
                warning(title="Failed to remove runner", message=e)
        print("Removing instances...")
        self.provider.remove_instances(instance_ids)
        print("Waiting for instance to be removed...")
        try:
            self.provider.wait_until_removed(instance_ids)
        except Exception as e:
            # Print to stdout
            print(
                f"Failed to remove instances check your provider console: {e}"
            )
            # Print to Annotations
            error(
                title="Failed to remove instances, check your provider console",
                message=e,
            )
            exit(1)
        else:
            print("Instances removed!")
