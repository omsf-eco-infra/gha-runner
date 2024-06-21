Feature: Reproducible workflow environment

    Within a version of our tool and a specific cloud machine image, the
    starting environment for all workflows should be the same.

    Scenario: Reproducible workflow environment
        Given a fixed version of our tool and of a cloud machine image
        When I start the workflow
        Then the versions of important libraries should be as expected
        And the versions of important software tools should be as expected
