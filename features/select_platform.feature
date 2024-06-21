Feature: Select platform to run on

    A user should be able to select the hardware that suits the needs of
    their run.

    Scenario: Running with large memory
        Given a workflow that requires and requests a large-memory host
        When I run the workflow
        Then it should run on the appropriate large-memory host

    Scenario: Running with a single CUDA GPU
        Given a workflow that requires and requests a single CUDA GPU
        When I run the workflow
        Then it should run on hardware with a GPU
        And my software should be able to interact with the CUDA drivers

    Scenario: Running with multiple GPUs
        Given a workflow that requires and request multiple GPUs
        When I run the workflow
        Then it should run on hardware with multiple GPUs
        And my software should be able to interact with all requested GPUs

    Scenario: Running with smaller hardware
        Given a workflow that requests lower-cost hardware
        When I run the workflow
        Then it should run on the appropriate hardware

    Scenario: Running with preemptible instances
        Given a workflow that can run on preemptible hosts
        When I run the workflow
        Then it should run on a preemptible host
        # NOTE: anything about continuing from preemption is the
        # responsibility of the workflow writer

    Scenario: A run on a preemptible instance is preempted
        Given a workflow that can run on preemptible hosts
        And the workflow is running
        When the workflow is preempted
        Then the workflow should be retried (up to a specified retry limit)

    Scenario: True failures should not be retried on preemtible instances
        Given a workflow that can run on preemptible hosts
        And the workflow is running
        When the workflow fails
        Then the workflow should not be retried

    # NOTE: This is not an MVP requirement
    #Scenario: Running with ROCM stack
    #    Given a workflow that requires an ROCM stack
    #    When I run the workflow
    #    Then it should run on hardware with the appropriate ROCM stack 
    
    Scenario: Running with an inference stack with various hardware
        Given a workflow that requires an inference stack
        When I run the workflow
        Then it should run on hardware with the appropriate inference stack
        And my software should be able to interact with the inference stack

    Scenario: Running a small ML training run
        Given a workflow that requires an inference stack
        And the workflow is a small ML training run
        When I run the workflow
        Then it should run on hardware with the appropriate inference stack
