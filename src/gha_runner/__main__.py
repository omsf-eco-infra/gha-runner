from gha_runner.clouddeployment import CloudDeploymentFactory
from gha_runner.gh import GitHubInstance
import os
import json


def _env_parse_helper(
    params: dict, var: str, key: str, is_json: bool = False
) -> dict:
    val = os.environ.get(var)
    if val is not None:
        if val != "":
            if is_json:
                params[key] = json.loads(val)
            else:
                params[key] = val
    return params


def parse_aws_params() -> dict:
    params = {}
    ami = os.environ.get("INPUT_AWS_IMAGE_ID")
    if ami is not None:
        params["image_id"] = ami
    instance_type = os.environ.get("INPUT_AWS_INSTANCE_TYPE")
    if instance_type is not None:
        params["instance_type"] = instance_type
    params = _env_parse_helper(params, "INPUT_AWS_SUBNET_ID", "subnet_id")
    params = _env_parse_helper(
        params, "INPUT_AWS_SECURITY_GROUP_ID", "security_group_id"
    )
    params = _env_parse_helper(params, "INPUT_AWS_IAM_ROLE", "iam_role")
    params = _env_parse_helper(params, "INPUT_AWS_TAGS", "tags", is_json=True)
    region_name = os.environ.get("INPUT_AWS_REGION_NAME")
    if region_name is not None:
        params["region_name"] = region_name
    home_dir = os.environ.get("INPUT_AWS_HOME_DIR")
    if home_dir is not None:
        params["home_dir"] = home_dir
    params = _env_parse_helper(params, "INPUT_EXTRA_GH_LABELS", "labels")
    return params


def get_instance_mapping() -> dict[str, str]:
    mapping_str = os.environ.get("INPUT_INSTANCE_MAPPING")
    if mapping_str is None:
        raise ValueError(
            "Missing required input variable INPUT_INSTANCE_MAPPING"
        )
    return json.loads(mapping_str)


def start_runner_instances(
    provider: str, cloud_params: dict, gh: GitHubInstance, count: int
):
    release = gh.get_latest_runner_release(platform="linux", architecture="x64")
    cloud_params["runner_release"] = release
    print("Starting up...")
    # Create a GitHub instance
    print("Creating GitHub Actions Runner")
    # We need to create a runner token first
    runner_tokens = gh.create_runner_tokens(count)
    cloud_params["gh_runner_tokens"] = runner_tokens
    # We will also get the latest runner release
    cloud = CloudDeploymentFactory().get_provider(
        provider_name=provider, **cloud_params
    )
    mappings = cloud.create_instances()
    instance_ids = list(mappings.keys())
    github_labels = list(mappings.values())
    with open(os.environ["GITHUB_OUTPUT"], "a") as output:
        json_mappings = json.dumps(mappings)
        output.write(f"mapping={json_mappings}\n")
    print("Waiting for instance to be ready...")
    cloud.wait_until_ready(instance_ids)
    print("Instance is ready!")
    for label in github_labels:
        print(f"Waiting for {label}...")
        gh.wait_for_runner(label)


def stop_runner_instances(
    provider: str, cloud_params: dict, gh: GitHubInstance
):
    print("Shutting down...")
    try:
        mappings = get_instance_mapping()
    except Exception as e:
        # This format is the native format for GitHub Actions
        # https://docs.github.com/en/actions/using-workflows/workflow-commands-for-github-actions#setting-an-error-message
        print(f"::error title=Malformed instance mapping::{e}")
        exit(1)
    print("Removing GitHub Actions Runner")
    instance_ids = list(mappings.keys())
    labels = list(mappings.values())
    for label in labels:
        print(f"Removing runner {label}")
        gh.remove_runner(label)
    cloud = CloudDeploymentFactory().get_provider(
        provider_name=provider, **cloud_params
    )
    print("Removing instances...")
    cloud.remove_instances(instance_ids)
    print("Waiting for instance to be removed...")
    cloud.wait_until_removed(instance_ids)
    print("Instances removed!")


def main():  # pragma: no cover
    """
    Main entrypoint for the application. As of right now, this is just a test.
    Requires the following environment variables:
        - GH_PAT: GitHub Personal Access Token
        - AWS_ACCESS_KEY_ID: AWS Access Key ID
        - AWS_SECRET_ACCESS_KEY: AWS Secret Access Key
    """
    # Check for required environment variables
    required = ["GH_PAT", "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"]
    for req in required:
        if req not in os.environ:
            raise Exception(f"Missing required environment variable {req}")
    provider = os.environ.get("INPUT_PROVIDER")
    if provider is None:
        raise Exception("Missing required input variable INPUT_PROVIDER")

    gha_params = {
        "token": os.environ["GH_PAT"],
    }
    repo = os.environ.get("INPUT_REPO")
    # Instance count will default to 1 if not provided
    instance_count = int(os.environ["INPUT_INSTANCE_COUNT"])
    if repo is not None:
        gha_params["repo"] = repo
    else:
        gha_params["repo"] = os.environ["GITHUB_REPOSITORY"]
    cloud_params = parse_aws_params()
    cloud_params["repo"] = gha_params["repo"]
    action = os.environ["INPUT_ACTION"]
    gh = GitHubInstance(**gha_params)
    if action == "start":
        start_runner_instances(
            provider,
            cloud_params,
            gh,
            instance_count,
        )
    elif action == "stop":
        stop_runner_instances(provider, cloud_params, gh)


if __name__ == "__main__":
    main()
