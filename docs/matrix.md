# Using a `matrix` with the `gha-runner` action.
Using a `matrix` with the `gha-runner` action requires some extra steps due to the need to reuse multiple dependent workflow steps. To achieve this, we recommend using [reusable workflows](https://docs.github.com/en/actions/sharing-automations/reusing-workflows). Reusable workflows allow you to group workflow steps together. For an example, see how we use it for integration testing in [reusable-gpu-test.yaml](.github/workflows/reusable-gpu-test.yaml) and [openmm-gpu-test.yaml](./github/workflows/openmm-gpu-test.yaml).

## Example
Take the workflow that we use in [our AWS docs](docs/aws.md).
```yaml
name: Test Self-Hosted Runner
on:
  workflow_dispatch:

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
          role-to-assume: <your-IAM-Role-ARN>
          aws-region: <your-region-here, for example us-east-1>
      - name: Create cloud runner
        id: aws-start
        uses: omsf-eco-infra/gha-runner@v0.3.0
        with:
          provider: "aws"
          action: "start"
          aws_image_id: <your-ami-here, for example ami-0d5079d9be06933e5>
          aws_instance_type: <your instance type here, for example g4dn.xlarge>
          aws_region_name: <your-region-here, for example us-east-1>
          aws_home_dir: /home/ubuntu
        env:
          GH_PAT: ${{ secrets.GH_PAT }}
  self-hosted-test:
    runs-on: ${{ fromJSON(needs.start-aws-runner.outputs.instances) }} # This ensures that you only run on the instances you just provisioned
    needs:
      - start-aws-runner
    steps:
      - uses: actions/checkout@v4
      - name: Print disk usage
        run: "df -h"
      - name: Print Docker details
        run: "docker version || true"
  stop-aws-runner:
    runs-on: ubuntu-latest
    permissions:
        id-token: write
        contents: read
    needs:
      - start-aws-runner
      - self-hosted-test
    if: ${{ always() }}
    steps:
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: <your-IAM-Role-ARN>
          aws-region: <your-region-here, for example us-east-1>
      - name: Stop instances
        uses: omsf-eco-infra/gha-runner@v0.3.0
        with:
          provider: "aws"
          action: "stop"
          instance_mapping: ${{ needs.start-aws-runner.outputs.mapping }}
          aws_region_name: <your-region-here, for example us-east-1>
        env:
          GH_PAT: ${{ secrets.GH_PAT }}
```

How would we go about converting this to handle a matrix of different machine configurations? We need to convert this workflow to use `workflow_call` instead of `workflow_dispatch` and add inputs that we reference in the jobs. It is important to note that we can remove the permissions section since we will have the job that calls this workflow set the permissions instead. _The caller is responsible for setting permissions_.
```yaml
name: Test Self-Hosted Runner - Reusable
on:
  workflow_call:
    inputs:
      instance_type: 
        required: true 
        type: string
jobs:
  start-aws-runner:
    runs-on: ubuntu-latest
    outputs:
      mapping: ${{ steps.aws-start.outputs.mapping }}
      instances: ${{ steps.aws-start.outputs.instances }}
    steps:
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: <your-IAM-Role-ARN>
          aws-region: <your-region-here, for example us-east-1>
      - name: Create cloud runner
        id: aws-start
        uses: omsf-eco-infra/gha-runner@v0.3.0
        with:
          provider: "aws"
          action: "start"
          aws_image_id: <your-ami-here, for example ami-0d5079d9be06933e5>
          aws_instance_type: ${{ inputs.instance_type }}
          aws_region_name: <your-region-here, for example us-east-1>
          aws_home_dir: /home/ubuntu
        env:
          GH_PAT: ${{ secrets.GH_PAT }}
  self-hosted-test:
    runs-on: ${{ fromJSON(needs.start-aws-runner.outputs.instances) }} # This ensures that you only run on the instances you just provisioned
    needs:
      - start-aws-runner
    steps:
      - uses: actions/checkout@v4
      - name: Print disk usage
        run: "df -h"
      - name: Print Docker details
        run: "docker version || true"
  stop-aws-runner:
    runs-on: ubuntu-latest
    needs:
      - start-aws-runner
      - self-hosted-test
    if: ${{ always() }}
    steps:
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: <your-IAM-Role-ARN>
          aws-region: <your-region-here, for example us-east-1>
      - name: Stop instances
        uses: omsf-eco-infra/gha-runner@v0.3.0
        with:
          provider: "aws"
          action: "stop"
          instance_mapping: ${{ needs.start-aws-runner.outputs.mapping }}
          aws_region_name: <your-region-here, for example us-east-1>
        env:
          GH_PAT: ${{ secrets.GH_PAT }}
```

Finally, we need to construct the matrix and reference the reusable workflow. To note, we use `secrets: inherit` so that all the secrets from the calling job gets passed into the reusable workflow. This is necessary because you can share reusable workflows across repos. We would then use it like so:
```yaml
name: Test Runner Matrix
on:
  workflow_dispatch:

jobs:
  run-matrix:
    name: Run Matrix
    strategy:
      fail-fast: false
      matrix:
        instance_type: ["g4dn.xlarge", "t3.large"]
    uses: <path to your resuable workflow here>
    permissions: # As you can see we set our permissions here.
      id-token: write
      contents: read
    with:
      instance_type: ${{ matrix.instance_type }}
    secrets: inherit # Bring in the secrets to the reused actions.
```

## References
- [Creating a reusable workflow](https://docs.github.com/en/actions/sharing-automations/reusing-workflows#creating-a-reusable-workflow)
- [Calling a reusable workflow](https://docs.github.com/en/actions/sharing-automations/reusing-workflows#calling-a-reusable-workflow)
