from abc import ABC, abstractmethod
from gha_runner.gh import GitHubInstance
from dataclasses import dataclass, field
import importlib.resources
import boto3
from string import Template


class StartCloudDeployment(ABC):
    """Abstract base class for starting a cloud instance.

    This class defines the interface for starting a cloud instance.

    """

    @abstractmethod
    def create_instance(self) -> str:
        """Create an instance in the cloud provider and return its ID.
        The number of instances to create is defined by the implementation.

        Returns
        -------
        str
            The instance ID.
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


class StopCloudDeployment(ABC):
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
