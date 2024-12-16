Feature: Manual runs of the workflow

    A user should be able to manually launch a workflow from the web UI.
    [Mechanism: workflow_dispatch and run workflow]

    Scenario: Authorized users should see the run workflow button
        Given I have a workflow generated with our tool
        And I am logged in as an authorized user
        When I load the workflow's page
        Then I should see the Run Workflow button

    Scenario: Unauthorized users should not see the run worklow button
        Given I have a workflow generated with our tool
        And I am logged in as an unauthorized user
        When I load the workflow's page
        Then I should not see the Run Workflow button

    Scenario: Running the Run Workflow button should run the workflow
        Given I have a workflow generated with our tool
        And I am logged in as an authorized user
        When I load the workflow's page
        And I press the Run Workflow button
        Then the workflow should complete a manual run



