Feature: Workflow should be able to set the GPU compute mode

    A given workflow should be able to use different GPU compute modes
    (e.g., EXCLUSIVE_PROCESS).
    [Mechanism: This might be either via machine selection or by setting
    mode in the workflow]

    Scenario: Run in EXCLUSIVE_PROCESS
        Given a workflow that should run with EXCLUSIVE_PROCESS set
        When I run the workflow
        Then my main process should take the GPU
        And any other process should error if it tries to use the GPU
