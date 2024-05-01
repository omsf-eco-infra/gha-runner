from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
import boto3
from string import Template
import os


class CloudDeployment(ABC):
    @abstractmethod
    def create_instance(self, count: int) -> list[str]:
        raise NotImplementedError

    @abstractmethod
    def remove_instances(self, ids: list[str]):
        raise NotImplementedError

    @abstractmethod
    def wait_until_ready(self, ids: list[str], **kwargs):
        raise NotImplementedError

    @abstractmethod
    def wait_until_removed(self, ids: list[str], **kwargs):
        raise NotImplementedError


@dataclass
class AWS(CloudDeployment):
    image_id: str
    instance_type: str
    gh_runner_token: str
    homedir: str
    repo: str
    tags: list[dict[str, str]]
    region_name: str
    runnerRelease: str
    labels: str = ""
    subnet_id: str = ""
    security_group_id: str = ""
    iam_role: str = ""
    script: str = ""

    def create_instance(self, count: int) -> list[str]:
        ec2 = boto3.client("ec2", region_name=self.region_name)
        userDataParams = {
            "token": self.gh_runner_token,
            "repo": self.repo,
            "homedir": self.homedir,
            "script": self.script,
            "runnerRelease": self.runnerRelease,
            "labels": self.labels,
        }
        params = {
            "ImageId": self.image_id,
            "InstanceType": self.instance_type,
            "MinCount": count,
            "MaxCount": count,
            "TagSpecifications": self.tags,
            "UserData": self.build_user_data(**userDataParams),
        }
        ## These lines help with mocking the AWS calls.
        ## They allow use to use the default AWS credentials for moto.
        if self.subnet_id != "":
            params["SubnetId"] = self.subnet_id
        if self.security_group_id != "":
            params["SecurityGroupIds"] = [self.security_group_id]
        if self.iam_role != "":
            params["IamInstanceProfile"] = {"Name": self.iam_role}
        result = ec2.run_instances(**params)
        instances = result["Instances"]
        ids = [instance["InstanceId"] for instance in instances]
        return ids

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
        waiter.wait(InstanceIds=ids)
        if kwargs:
            waiter.wait(InstanceIds=ids, WaiterConfig=kwargs)
        else:
            waiter.wait(InstanceIds=ids)

    def build_user_data(self, **kwargs) -> str:
        file = Path(os.getcwd(), "templates", "user-script.sh.templ")
        with open(file, "r") as f:
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
            raise ValueError("Invalid provider name")
