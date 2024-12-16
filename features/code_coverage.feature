Feature: Code coverage

    Our workflow should be able to report code coverage to external
    services. (For testing, we'll just be sure we can integrate with
    CodeCov.)

    Scenario: Report default coverage
        # Note that this is probably NOT what most users will want. Imagine
        # that our runner, because it is on GPU, runs more code paths than
        # the basic runs, and runs less frequently. This means that PRs (not
        # using our runner) will see spurious decrease in coverage.
        Given a workflow that uses CodeCov for coverage
        When I run the workflow
        Then coverage should successfully be updated on CodeCov
    
    Scenario: Report coverage with CodeCov flags
        # Using CodeCov flags may help solve the problem mentioned in the
        # default coverage scenario, but we should play with it a bit to
        # determine a recommended practice. (Out of scope for MVP.)
        Given a workflow that uses CodeCov flags for coverage
        When I run then workflow
        Then the correct flag should be updated on CodeCov
