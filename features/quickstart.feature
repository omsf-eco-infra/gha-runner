Feature: Quickstart guide

    There should be a quick and easy way to set up workflows, and a simple
    demo workflow.

    # TODO: There should be a scenario here about documentation, maybe? or
    # is that another feature? Up-to-date getting started documentation.

    Scenario: Easy set-up of for first-time users
        Given I have AWS credentials
        And I have not previously set up AWS infra for this tool
        When I use the quickstart command
        Then I should have a working workflow

    Scenario: Up-to date documentation
        Given I have the latest version of the tool
        When I look at the documentation
        Then I should see up-to-date and tested information
