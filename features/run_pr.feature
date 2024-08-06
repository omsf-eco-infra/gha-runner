Feature: Run on pull requests

    A user should be able to run a workflow on self-hosted runners prior to
    merging a pull request. NOTE: This will *not* use the normal
    pull_request trigger for workflows. Instead, this will be a
    workflow_dispatch caused by some external decision. This is because we
    don't expect to want to run expensive CI on every commit, but rather
    when an admin chooses to.

    Scenario: Choose to run a workflow on a PR
        Given I have a workflow generated with our tool
        And a pull request is open against that repository
        When I [trigger the workflow to run on the PR]  (how? TBD)
        Then the workflow runs on our runner using code in the PR
