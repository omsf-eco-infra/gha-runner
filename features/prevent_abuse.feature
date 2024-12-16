Feature: Safeguards to prevent abuse of self-hosted runners

    Compute resources should be protected from use outside of intended runs,
    either due to accidental triggering or due to intential abuse by
    malicious actors. This includes preventing forks from accessing our
    resources and includes preventing runs on untrusted PRs.

    Scenario: Forks should not be able to use our runners
        # This should be guaranteed by the fact that secrets don't propagate
        # to forks.
        Given a fork of a repository with a self-hosted workflow
        When the fork owner tries to run (within fork) using workflow dispatch
        Then the workflow should give an error due to authorization
        And the workflow should fail to start instances on AWS

    Scenario: Pull requests from first-time contributors should not start runners
        # With default repo settings, first-time contributors should require
        # approval to run CI at all.
        Given a fork of a repository with a self-hosted workflow
        And the fork owner has not previously contributed to the repository
        And the fork owner has changed our workflow to run on PRs
        When the fork owner creates a pull request to our repository
        Then the workflow should give an error due to authorization
        And the workflow should fail to start instances on AWS

    Scenario: Pull requests from previous contributors should not start runners
        # With default repo settings, an external contributor who has
        # previously contributed no longer requires approval for CI to run.
        # However, this should be guaranteed because PRs from forks don't
        # have access to secrets.
        Given a fork of a repository with a self-hosted workflow
        And the fork owner has previously contributed to the repository
        And the fork owner has changed our workflow to run on PRs
        When the fork owner creates a pull request to our repository
        Then the workflow should give an error due to authorization
        And the workflow should fail to start instances on AWS

    # Non-tested scenario: AWS tokens (as secrets) should not leak in PRs
    # from forks because forks don't see secrets. (Leaking AWS tokens is
    # a different attack vector from the ones described above.)
