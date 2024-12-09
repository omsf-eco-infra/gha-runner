import re
from gha_runner.helper.input import (
    EnvVarBuilder,
    check_required,
)
import pytest


def test_parse_params_empty():
    env = {}
    env["INPUT_AWS_IMAGE_ID"] = ""
    env["INPUT_AWS_INSTANCE_TYPE"] = ""
    env["INPUT_AWS_SUBNET_ID"] = ""
    env["INPUT_AWS_SECURITY_GROUP_ID"] = ""
    env["INPUT_AWS_IAM_ROLE"] = ""
    env["INPUT_AWS_TAGS"] = ""
    env["INPUT_AWS_REGION_NAME"] = ""
    env["INPUT_AWS_HOME_DIR"] = ""
    env["INPUT_AWS_LABELS"] = ""
    params = (
        EnvVarBuilder(env)
        .with_var("INPUT_AWS_IMAGE_ID", "image_id", allow_empty=True)
        .with_var("INPUT_AWS_INSTANCE_TYPE", "instance_type", allow_empty=True)
        .with_var("INPUT_AWS_SUBNET_ID", "subnet_id")
        .with_var("INPUT_AWS_SECURITY_GROUP_ID", "security_group_id")
        .with_var("INPUT_AWS_IAM_ROLE", "iam_role")
        .with_var("INPUT_AWS_TAGS", "tags", is_json=True)
        .with_var("INPUT_AWS_REGION_NAME", "region_name", allow_empty=True)
        .with_var("INPUT_AWS_HOME_DIR", "home_dir", allow_empty=True)
        .with_var("INPUT_AWS_LABELS", "labels")
        .build()
    )

    assert params == {
        "image_id": "",
        "instance_type": "",
        "home_dir": "",
        "region_name": "",
    }


def test_env_builder():
    env = {}
    env["INPUT_AWS_IMAGE_ID"] = "ami-1234567890"
    env["INPUT_AWS_INSTANCE_TYPE"] = "t2.micro"
    env["INPUT_GH_REPO"] = "owner/test"
    env["GITHUB_REPOSITORY"] = "owner/test_other"
    env["INPUT_INSTANCE_COUNT"] = "1"
    env["INPUT_AWS_TAGS"] = '{"Key": "Name", "Value": "test"}'
    config = (
        EnvVarBuilder(env)
        .with_var("INPUT_AWS_IMAGE_ID", "image_id")
        .with_var("INPUT_AWS_INSTANCE_TYPE", "instance_type")
        .with_var("GITHUB_REPOSITORY", "repo")
        .with_var("INPUT_GH_REPO", "repo")
        .with_var("INPUT_INSTANCE_COUNT", "instance_count", type_hint=int)
        .with_var("INPUT_AWS_TAGS", "tags", is_json=True)
        .build()
    )
    assert config["image_id"] == "ami-1234567890"
    assert config["instance_type"] == "t2.micro"
    assert config["repo"] == "owner/test"
    assert config["instance_count"] == 1
    assert isinstance(config["instance_count"], int)
    assert config["tags"] == {"Key": "Name", "Value": "test"}
    assert isinstance(config["tags"], dict)


def test_check_required():
    env = {"GH_TOKEN": "123", "AWS_ACCESS_KEY": "123", "AWS_SECRET_KEY": "123"}
    required = ["GH_TOKEN", "AWS_ACCESS_KEY", "AWS_SECRET_KEY"]
    check_required(env, required)
    env = {"GH_TOKEN": "123"}
    with pytest.raises(
        Exception,
        match=re.escape(
            "Missing required environment variables: ['AWS_ACCESS_KEY', 'AWS_SECRET_KEY']"
        ),
    ):
        check_required(env, required)
    env = {}
    with pytest.raises(
        Exception,
        match=re.escape(
            "Missing required environment variables: ['GH_TOKEN', 'AWS_ACCESS_KEY', 'AWS_SECRET_KEY']"
        ),
    ):
        check_required(env, required)
