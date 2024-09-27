Feature: Allow external contributors to use resources

    ...

    # NOTE: this is essentially the same as a scenario from the run_pr
    # feature; might not ever fill it in
    #Scenario: Authorized user permits a PR from unauthorized user to run

    Scenario: Adding a new authorized user
        Given an unauthorized user who should become authorized
        When I give the user committer access to the repository
        Then the user should have the ability to launch self-hosted workflows
