from ruamel.yaml import YAML
import click


def before_job(
    role: str, region: str, ami: str, instance_type: str, home_dir: str
):
    return {
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
                        "role-to-assume": role,
                        "aws-region": region,
                    },
                },
                {
                    "name": "Start AWS runner",
                    "id": "aws-start",
                    "uses": "omsf-eco-infra/gha-runner@v0.3.0",
                    "with": {
                        "provider": "aws",
                        "action": "start",
                        "aws_image_id": ami,
                        "aws_instance_type": instance_type,
                        "aws_region_name": region,
                        "aws_home_dir": home_dir,
                    },
                    "env": {
                        "GH_PAT": "${{ secrets.GH_PAT }}",
                    },
                },
            ],
        }
    }


def after_job(job: str, role: str, region: str):
    return {
        "stop-aws-runner": {
            "runs-on": "ubuntu-latest",
            "permissions": {
                "id-token": "write",
                "contents": "read",
            },
            "needs": ["start-aws-runner", job],
            "if": "${{ always() }}",
            "steps": [
                {
                    "name": "Configure AWS credentials",
                    "uses": "aws-actions/configure-aws-credentials@v4",
                    "with": {
                        "role-to-assume": role,
                        "aws-region": region,
                    },
                },
                {
                    "name": "Stop AWS runner",
                    "uses": "omsf-eco-infra/gha-runner@v0.3.0",
                    "with": {
                        "provider": "aws",
                        "action": "stop",
                        "instance_mapping": "${{ needs.start-aws-runner.outputs.mapping }}",
                        "aws_region_name": region,
                    },
                    "env": {
                        "GH_PAT": "${{ secrets.GH_PAT }}",
                    },
                },
            ],
        }
    }


@click.command()
@click.argument("input_file", type=click.File("r"))
@click.option("--role", required=True, type=str, help="AWS IAM role to assume")
@click.option("--region", required=True, type=str, help="AWS region")
@click.option("--ami", required=True, type=str, help="AWS AMI ID")
@click.option(
    "--instance-type", required=True, type=str, help="AWS instance type"
)
@click.option("--home-dir", required=True, type=str, help="AWS home directory")
def read_file(input_file, role, region, ami, instance_type, home_dir):
    yaml = YAML()
    yaml.default_flow_style = False
    # yaml.preserve_quotes = True
    data = yaml.load(input_file)
    jobs = data.get("jobs", {})
    job_name = ""
    for job in data["jobs"]:
        job_name = job
    new_job_list = {}
    before = before_job(role, region, ami, instance_type, home_dir)
    after = after_job(job_name, role, region)
    if len(jobs) > 1:
        print("Only one job is allowed")
        exit(1)
    for k, v in jobs.items():
        if k == job_name:
            new_job_list.update(before)
        v.update(
            {
                "runs-on": "${{ fromJSON(needs.start-aws-runner.outputs.instances) }}"
            }
        )
        v["needs"] = ["start-aws-runner"]
        new_job_list[k] = v
        if k == job_name:
            new_job_list.update(after)

    data["jobs"] = dict(new_job_list)

    yaml.dump(data, click.get_text_stream("stdout"))


if __name__ == "__main__":  # pragma: no cover
    read_file()
