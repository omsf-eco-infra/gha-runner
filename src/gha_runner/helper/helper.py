import os


def output(name: str, value: str):
    with open(os.environ["GITHUB_OUTPUT"], "a") as output:
        output.write(f"{name}={value}\n")


def warning(title: str, message):
    print(f"::warning title={title}::{message}")


def error(title: str, message):
    print(f"::error title={title}::{message}")
