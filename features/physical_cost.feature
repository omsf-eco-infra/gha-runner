Feature: Track physical cost of running

    The amount of time that has been used (or ideally, the actual cost
    incurred) should be easily accessible.
    [Possible mechanisms: (1) Refer to AWS billing info; (2) use an API to
    extract stuff from AWS billing / CloudTrail; (3) have some custom
    cloud-independent approach -- probably (1) or (2)]

    Scenario: 
        # TODO: having trouble with this one because I feel like it depends
        # on the specific mechanism

    # WIP: I think this is the generic form of this information
    # the mechanism for tracking the cost is not specified here.
    Scenario: When I run a test, I can see how much it costs
        Given I have a test that runs for X amount of time
        And I have a cost of Y per unit time
        And I have a mechanism for tracking the cost
        When I run the test
        Then I receive a caclulated cost of running the test.
