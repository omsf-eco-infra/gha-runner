# gha-runner
A simple GitHub Action for creating self-hosted runners. Currently, this only supports AWS and x86_64 Linux AMIs. This runner is heavily inspired by [ec2-github-runner](https://github.com/machulav/ec2-github-runner) but rewritten for the molecular software community as well as changes to support additional cloud providers.

## Inputs
| Name | Description | Required | Default |
| ---- | ----------- | -------- | ------- |
| aws_iam_role | The optional AWS IAM role to assume for provisioning your runner. | false |  |
| aws_tags | The AWS tags to use for your runner, formatted as a JSON list. See `README` for more details. | false |  |
| extra_gh_labels | Any extra GitHub lables to tag your runners with. Passed as a comma-seperated list with no spaces. | false |  |
| action | Whether to start or stop. Options: "start", "stop" | true |  |
| aws_region_name | The AWS region name to use for your runner. Will not start if not specified. | false |  |
| instance_count | The number of instances to create, defaults to 1 | false | 1 |
| instance_mapping | A JSON object mapping instance ids to unique GitHub runner labels. Required to stop created instances. | false |  |
| aws_home_dir | The AWS AMI home directory to use for your runner. Will not start if not specified. For example: `/home/ec2-user` | false |  |
| aws_image_id | The machine AMI to use for your runner. This AMI can be a default but should have docker installed in the AMI. Will not start if not specified. | false |  |
| aws_instance_type | The type of instance to use for your runner. For example: t2.micro, t4g.nano, etc.. Will not start if not specified. | false |  |
| provider | The cloud provider to use to provision a runner. Will not start if not set. Example: "aws" | true |  |
| aws_security_group_id | The AWS security group ID to use for your runner. Will use the account default security group if not specified. | false |  |
| aws_subnet_id | The AWS subnet ID to use for your runner. Will use the account default subnet if not specified. | false |  |
| gh_pat | The GHA Personal Access Token (PAT) | true |  |
| repo | The repo to run against. Will use the the current repo if not specified. | false |  |

## Outputs
| Name | Description |
| ---- | ----------- |
| mapping | A JSON object mapping instance IDs to unique GitHub runner labels. This is used in conjection with the the `instance_mapping` input when stopping. |

## Using the action
Setup the following GitHub Action for to provision instances on AWS:
```yaml
name: Testing
on: [push]

jobs:
  hello_world_job:
    runs-on: ubuntu-latest
    name: Test the gha_runner
    steps:
      - name: Checkout
        uses: actions/checkout@v4
      - name: Local runner run
        id: aws_start
        uses: omsf-eco-infra/gha-runner@latest # This is pending publishing of this action
        with:
          repo: "<the repo name in terms of org/name, if not provided the current repo will be used>"
          provider: "aws"
          action: "start"
          instance_count: <the number of instances, if not provided, defaults to 1>
          aws_image_id: <the AWS image AMI to use for your runner>
          aws_instance_type: <the AWS instance type>
          aws_subnet_id: <the AWS subnet ID, will use default by default, optional>
          aws_security_group_id: <the AWS security group ID, will use default by default, optional>
          aws_iam_role: <the AWS IAM role to use, optional>
          aws_region_name: <AWS region name, required>
          aws_home_dir: <the ec2 instance home directory, for Amazon Linux 2023/Amazon Linux 2 this is /home/ec2-user>
          aws_labels: <labels provided to AWS to be added to the GitHub runner>
          # NOTE: aws_tags are provided as a list of key-values as seen below
          aws_tags: >
            [
              {"Key": "Name", "Value": "test"}
              {"Key": "Other", "Value": "item"}
            ]
        env:
          GH_PAT: ${{ secrets.GH_PAT }} # Your GH PAT access token with enough scope to create runners
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }} # Your AWS access key id
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }} # You AWS secret access key
      - name: Your test here
        id: test
        runs-on: self-hosted
      - name: Stop instances
        needs:
          - aws_start
          - test
        if: ${{ always() }}
        uses: omsf-eco-infra/gha-runner@latest # This is pending publishing of this action
        with:
          repo: "<the repo name in terms of org/name, if not provided the current repo will be used>"
          provider: "aws"
          action: "stop"
          # NOTE: The output below is a JSON formatted mapping of AWS instance IDs to runner names. Below is the recommended usage.
          instance_mapping: ${{ steps.aws_start.outputs.mapping }}
          aws_region_name: <AWS region name, required>
        env:
          GH_PAT: ${{ secrets.GH_PAT }}
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}


```

## Testing the action in development
Testing the action was primarily done using [nektos/act]("https://github.com/nektos/act") to test locally. To do a test run with some basic defaults:
```yaml
name: Testing
on: [push]

jobs:
  hello_world_job:
    runs-on: ubuntu-latest
    name: Test the gha_runner
    steps:
      # To use this repository's private action,
      # you must check out the repository
      - name: Checkout
        uses: actions/checkout@v4
      - name: Local runner run
        id: aws_start
        uses: ./ # Uses an action in the root directory
        with:
          repo: "testing/testing"
          provider: "aws"
          action: "start"
          aws_image_id: <use an image here that has docker installed>
          aws_instance_type: t2.micro
          instance_count: 2
          aws_region_name: us-east-1
          aws_home_dir: /home/ec2-user
          aws_labels: testing
        env:
          GH_PAT: ${{ secrets.GH_PAT }}
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
      - name: Stop instances
        uses: ./
        with:
          repo: "testing/testing"
          provider: "aws"
          action: "stop"
          instance_mapping: ${{ steps.aws_start.outputs.mapping }}
          aws_region_name: us-east-1
        env:
          GH_PAT: ${{ secrets.GH_PAT }}
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}


```
_NOTE: For guidelines on setting secrets view the act docs found [here](https://nektosact.com/usage/index.html?highlight=Secrets#secrets)_
This file was placed in a `test-worklows` directory.

Then it was run using the following:
```sh
act -W test-workflows/ --verbose
```

For testing on M-series Macs, use the following command instead:
```sh
act --container-architecture linux/arm64 -W test-workflows/ --verbose
```

## Acknowledgements
This action was heavily inspired by the [ec2-github-runner](https://github.com/machulav/ec2-github-runner). This action takes much of its structure and inspiration around architecture from the `ec2-github-runner` itself. Thank you to the authors of that action for providing a solid foundation to build upon.
