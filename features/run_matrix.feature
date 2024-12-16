Feature: Run a matrix build

    A user should be able to run a full build matrix (ideally in parallel).

    Scenario: Run a matrix
        Given a workflow that involves a complicated matrix
        When I run the workflow
        Then all builds in the matrix should complete
        # maybe this too:
        # And an instance should be launched for each job
        # And all jobs should run on different instances
