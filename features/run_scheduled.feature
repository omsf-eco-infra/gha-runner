Feature: Scheduled runs of the workflow

    A user should be able to run scheduled runs of a workflow

    Scenario: A scheduled run should run
        Given I have a workflow generated with our tool
        When I wait until after the scheduled run time
        Then the workflow should have completed a scheduled run

