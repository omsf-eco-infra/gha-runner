from abc import ABC, abstractmethod
from gha_runner.gh import GitHubInstance, MissingRunnerLabel
from gha_runner.helper import warning, error
from dataclasses import dataclass, field
import importlib.resources
import boto3
from string import Template
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


class CloudDeployment(ABC):
    """Abstract base class for cloud deployment.

    This class defines the interface for cloud deployment classes.

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
    def remove_instances(self, ids: list[str]):
        """Remove instances from the cloud provider.

        Parameters
        ----------
        ids : list[str]
            A list of instance IDs to remove.

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
    def instance_running(self, id: str) -> bool:
        """Check if an instance exists.

        Parameters
        ----------
        id : str
            The instance ID to check.

        Returns
        -------
        bool
            True if the instance exists, False otherwise.

        """
        raise NotImplementedError


@dataclass
class AWS(CloudDeployment):
    image_id: str
    instance_type: str
    home_dir: str
    repo: str
    region_name: str
    runner_release: str = ""
    tags: list[dict[str, str]] = field(default_factory=list)
    gh_runner_tokens: list[str] = field(default_factory=list)
    labels: str = ""
    subnet_id: str = ""
    security_group_id: str = ""
    iam_role: str = ""
    script: str = ""

    def _build_aws_params(self, user_data_params: dict) -> dict:
        """Build the parameters for the AWS API call.

        Parameters
        ----------
        count : int
            The number of instances to create.
        user_data_params : dict
            A dictionary of parameters to pass to the user

        Returns
        -------
        dict
            A dictionary of parameters for the AWS API call.

        """
        params = {
            "ImageId": self.image_id,
            "InstanceType": self.instance_type,
            "MinCount": 1,
            "MaxCount": 1,
            "UserData": self._build_user_data(**user_data_params),
        }
        if self.subnet_id != "":
            params["SubnetId"] = self.subnet_id
        if self.security_group_id != "":
            params["SecurityGroupIds"] = [self.security_group_id]
        if self.iam_role != "":
            params["IamInstanceProfile"] = {"Name": self.iam_role}
        if len(self.tags) > 0:
            specs = {"ResourceType": "instance", "Tags": self.tags}
            params["TagSpecifications"] = [specs]

        return params

    def create_instances(self) -> dict[str, str]:
        if not self.gh_runner_tokens:
            raise ValueError(
                "No GitHub runner tokens provided, cannot create instances."
            )
        if not self.runner_release:
            raise ValueError(
                "No runner release provided, cannot create instances."
            )
        if not self.home_dir:
            raise ValueError(
                "No home directory provided, cannot create instances."
            )
        if not self.image_id:
            raise ValueError("No image ID provided, cannot create instances.")
        if not self.instance_type:
            raise ValueError(
                "No instance type provided, cannot create instances."
            )
        ec2 = boto3.client("ec2", region_name=self.region_name)
        id_dict = {}
        for token in self.gh_runner_tokens:
            label = GitHubInstance.generate_random_label()
            # unique_labels.append(label)
            labels = self.labels
            if labels == "":
                labels = label
            else:
                labels = self.labels + "," + label
            user_data_params = {
                "token": token,
                "repo": self.repo,
                "homedir": self.home_dir,
                "script": self.script,
                "runner_release": self.runner_release,
                "labels": labels,
            }
            params = self._build_aws_params(user_data_params)
            result = ec2.run_instances(**params)
            instances = result["Instances"]
            id = instances[0]["InstanceId"]
            id_dict[id] = label
            # ids += [instance["InstanceId"] for instance in instances]
        return id_dict

    def remove_instances(self, ids: list[str]):
        ec2 = boto3.client("ec2", self.region_name)
        params = {
            "InstanceIds": ids,
        }
        ec2.terminate_instances(**params)

    def wait_until_ready(self, ids: list[str], **kwargs):
        ec2 = boto3.client("ec2", self.region_name)
        waiter = ec2.get_waiter("instance_running")
        # Pass custom config for the waiter
        if kwargs:
            waiter.wait(InstanceIds=ids, WaiterConfig=kwargs)
        # Otherwise, use the default config
        else:
            waiter.wait(InstanceIds=ids)

    def wait_until_removed(self, ids: list[str], **kwargs):
        ec2 = boto3.client("ec2", self.region_name)
        waiter = ec2.get_waiter("instance_terminated")

        if kwargs:
            waiter.wait(InstanceIds=ids, WaiterConfig=kwargs)
        else:
            # Use a longer WaiterConfig to allow for GPU to properly terminate
            waiter_config = {"MaxAttempts": 80}
            waiter.wait(InstanceIds=ids, WaiterConfig=waiter_config)

    def instance_running(self, id: str) -> bool:
        ec2 = boto3.client("ec2", self.region_name)
        params = {
            "InstanceIds": [id],
        }
        response = ec2.describe_instances(**params)
        # Loop through the response to find the state of the instance
        for reservation in response["Reservations"]:
            for instance in reservation["Instances"]:
                instance_state = instance["State"]["Name"]
                if instance_state == "running":
                    return True
                else:
                    return False
        return False

    def _build_user_data(self, **kwargs) -> str:
        """Build the user data script.

        Parameters
        ----------
        kwargs : dict
            A dictionary of parameters to pass to the template.

        Returns
        -------
        str
            The user data script as a string.

        """
        template = importlib.resources.files("gha_runner").joinpath(
            "templates/user-script.sh.templ"
        )
        with template.open() as f:
            template = f.read()
            try:
                parsed = Template(template)
                return parsed.substitute(**kwargs)
            except Exception as e:
                raise Exception(f"Error parsing user data template: {e}")


class CloudDeploymentFactory:
    providers = {"aws": AWS}

    def get_provider(self, provider_name: str, **kwargs) -> CloudDeployment:
        if self.providers.get(provider_name):
            try:
                return self.providers[provider_name](**kwargs)
            except TypeError as t:
                # Raise a more informative error message
                raise TypeError(
                    f"Invalid configuration for provider {provider_name}: {t}"
                )
        else:
            raise ValueError(f"Invalid provider name: '{provider_name}'")


@dataclass
class DeployInstance:
    provider_type: Type[CreateCloudInstance]
    cloud_params: dict
    gh: GitHubInstance
    count: int
    timeout: int
    provider: CreateCloudInstance = field(init=False)

    def __post_init__(self):
        # We need to create runner tokens for use by the provider
        runner_tokens = self.gh.create_runner_tokens(self.count)
        self.cloud_params["gh_runner_tokens"] = runner_tokens
        release = self.gh.get_latest_runner_release(
            platform="linux", architecture="x64"
        )
        self.cloud_params["runner_release"] = release
        self.provider = self.provider_type(**self.cloud_params)

    def start_runner_instances(self):
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
    provider_type: Type[StopCloudInstance]
    cloud_params: dict
    gh: GitHubInstance
    provider: StopCloudInstance = field(init=False)

    def __post_init__(self):
        self.provider = self.provider_type(**self.cloud_params)

    def stop_runner_instances(self):
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
