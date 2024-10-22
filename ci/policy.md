This test policy is designed to guide the community in explaining the
Continuous Integration (CI) workflow defined in the `ci.yaml` file.
The workflow is triggered on push and pull request events on the `main`
branch, excluding changes in the `docs` directory and `README.md` file.
It can also be manually triggered using the `workflow_dispatch` event.

## Test Environment
The tests are run on the latest version of Ubuntu. The Python versions used for testing are the current supported Python versions.

## Test Steps

1. **Checkout Code**: The workflow checks out the latest code from the repository using the `actions/checkout@v4` action.
2. **Display Build Info**: The workflow displays additional information about the build environment,
including the operating system, disk usage, and system limits.
3. **Setup Python**: The workflow sets up the specified Python version using the `actions/setup-python@v5` action.
It also caches the pip dependencies to speed up future runs.
4. **Install Dependencies**: The workflow installs the necessary dependencies for the project, including upgrading pip, setuptools,
and wheel, and installing the test dependencies.
5. **List Versions**: The workflow lists the versions of the installed Python packages.
6. **Run Short Tests**: If the pull request is a draft, the workflow runs a subset of the tests that are not marked as slow.
It also generates a coverage report.
7. **Upload Coverage**: If the pull request is a draft, the workflow uploads the coverage report to Codecov using the `codecov/codecov-action@v4` action with the `unittests-fast` tag.
8. **Run All Tests**: If the pull request is not a draft, the workflow runs all tests and generates a coverage report.
9. **Upload Coverage**: If the pull request is not a draft, the workflow uploads the coverage report to Codecov using the `codecov/codecov-action@v4` action with the `unittests` tag.

## CodeCov tags
- `unittests`: The tag for ALL tests
- `unittests-fast`: The tag for all "not slow" tests.
