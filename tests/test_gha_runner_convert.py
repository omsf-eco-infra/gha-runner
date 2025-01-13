import pytest
from gha_runner_convert.__main__ import before_job, after_job, read_file
from collections import OrderedDict
from click.testing import CliRunner
from ruamel.yaml import YAML


def test_before_job():
    # We use OrderedDict to ensure the order of the keys
    result = OrderedDict(
        before_job(
            role="test",
            region="us-west-2",
            ami="ami-xxxxxxxxxxxxxxxxx",
            instance_type="t2.micro",
            home_dir="/home/ubuntu",
        )
    )
    expected = OrderedDict(
        {
            "start-aws-runner": {
                "runs-on": "ubuntu-latest",
                "permissions": {
                    "id-token": "write",
                    "contents": "read",
                },
                "outputs": {
                    "mapping": "${{ steps.aws-start.outputs.mapping }}",
                    "instances": "${{ steps.aws-start.outputs.instances }}",
                },
                "steps": [
                    {
                        "name": "Configure AWS credentials",
                        "uses": "aws-actions/configure-aws-credentials@v4",
                        "with": {
                            "role-to-assume": "test",
                            "aws-region": "us-west-2",
                        },
                    },
                    {
                        "name": "Start AWS runner",
                        "id": "aws-start",
                        "uses": "omsf-eco-infra/gha-runner@v0.3.0",
                        "with": {
                            "provider": "aws",
                            "action": "start",
                            "aws_image_id": "ami-xxxxxxxxxxxxxxxxx",
                            "aws_instance_type": "t2.micro",
                            "aws_region_name": "us-west-2",
                            "aws_home_dir": "/home/ubuntu",
                        },
                        "env": {
                            "GH_PAT": "${{ secrets.GH_PAT }}",
                        },
                    },
                ],
            }
        }
    )
    assert result == expected


def test_after_job():
    result = OrderedDict(after_job("test-job", "test", "us-west-2"))
    expected = OrderedDict(
        {
            "stop-aws-runner": {
                "runs-on": "ubuntu-latest",
                "permissions": {
                    "id-token": "write",
                    "contents": "read",
                },
                "needs": ["start-aws-runner", "test-job"],
                "if": "${{ always() }}",
                "steps": [
                    {
                        "name": "Configure AWS credentials",
                        "uses": "aws-actions/configure-aws-credentials@v4",
                        "with": {
                            "role-to-assume": "test",
                            "aws-region": "us-west-2",
                        },
                    },
                    {
                        "name": "Stop AWS runner",
                        "uses": "omsf-eco-infra/gha-runner@v0.3.0",
                        "with": {
                            "provider": "aws",
                            "action": "stop",
                            "instance_mapping": "${{ needs.start-aws-runner.outputs.mapping }}",
                            "aws_region_name": "us-west-2",
                        },
                        "env": {
                            "GH_PAT": "${{ secrets.GH_PAT }}",
                        },
                    },
                ],
            }
        }
    )
    assert result == expected


def test_read_file():
    runner = CliRunner()
    with runner.isolated_filesystem():
        input_file = "input_action.yml"
        with open(input_file, "w") as f:
            f.write(
                """
            name: test
            on: push
            jobs:
              test-job:
                runs-on: ubuntu-latest
                steps:
                  - name: Test
                    run: echo "Hello, World!"
            """
            )
        result = runner.invoke(
            read_file,
            [
                "--role",
                "test",
                "--region",
                "us-west-2",
                "--ami",
                "ami-xxxxxxxxxxxxxxxxx",
                "--instance-type",
                "t2.micro",
                "--home-dir",
                "/home/ubuntu",
                input_file,
            ],
        )
        expected = """
        name: test
        on: push
        jobs:
            start-aws-runner:
                runs-on: ubuntu-latest
                permissions:
                    id-token: write
                    contents: read
                outputs:
                    mapping: ${{ steps.aws-start.outputs.mapping }}
                    instances: ${{ steps.aws-start.outputs.instances }}
                steps:
                    - name: Configure AWS credentials
                      uses: aws-actions/configure-aws-credentials@v4
                      with:
                          role-to-assume: test
                          aws-region: us-west-2
                    - name: Start AWS runner
                      id: aws-start
                      uses: omsf-eco-infra/gha-runner@v0.3.0
                      with:
                          provider: aws
                          action: start
                          aws_image_id: ami-xxxxxxxxxxxxxxxxx
                          aws_instance_type: t2.micro
                          aws_region_name: us-west-2
                          aws_home_dir: /home/ubuntu
                      env:
                          GH_PAT: ${{ secrets.GH_PAT }}
            test-job:
                runs-on: ${{ fromJSON(needs.start-aws-runner.outputs.instances) }}
                steps:
                    - name: Test
                      run: echo "Hello, World!"
                needs:
                    - start-aws-runner
            stop-aws-runner:
                runs-on: ubuntu-latest
                permissions:
                    id-token: write
                    contents: read
                needs:
                    - start-aws-runner
                    - test-job
                if: ${{ always() }}
                steps:
                    - name: Configure AWS credentials
                      uses: aws-actions/configure-aws-credentials@v4
                      with:
                          role-to-assume: test
                          aws-region: us-west-2
                    - name: Stop AWS runner
                      uses: omsf-eco-infra/gha-runner@v0.3.0
                      with:
                          provider: aws
                          action: stop
                          instance_mapping: ${{ needs.start-aws-runner.outputs.mapping }}
                          aws_region_name: us-west-2
                      env:
                          GH_PAT: ${{ secrets.GH_PAT }}
        """
        assert result.exit_code == 0
        yaml = YAML()
        output = yaml.load(result.output)
        expected = yaml.load(expected)
        assert OrderedDict(output) == OrderedDict(expected)


def test_read_file_fail():
    runner = CliRunner()
    with runner.isolated_filesystem():
        input_file = "input_action.yml"
        with open(input_file, "w") as f:
            f.write(
                """
            name: test
            on: push
            jobs:
              test-job:
                runs-on: ubuntu-latest
                steps:
                  - name: Test
                    run: echo "Hello, World!"
              test-job-2:
                runs-on: ubuntu-latest
                steps:
                  - name: Test
                    run: echo "Hello, World!" 
            """
            )
        result = runner.invoke(
            read_file,
            [
                "--role",
                "test",
                "--region",
                "us-west-2",
                "--ami",
                "ami-xxxxxxxxxxxxxxxxx",
                "--instance-type",
                "t2.micro",
                "--home-dir",
                "/home/ubuntu",
                input_file,
            ],
        )
        assert result.exit_code == 1
