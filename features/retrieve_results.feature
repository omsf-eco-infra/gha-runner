Feature: Retrieve results of a benchmarking run

    A user may generate data during a run that they want to save somewhere
    long-term. This will require that the user explicitly store that data
    somewhere; in this, we will test that we can store it.

    Scenario: Store results to an S3 bucket
        Given a workflow that intends to upload a file to an S3 bucket
        When I run the workflow
        Then the file should be uploaded to the S3 bucket

    Scenario: Store results to Dropbox
        # we do a separate test for Dropbox just to ensure that there's
        # nothing special happening because S3 and EC2 are both AWS
        Given a workflow that intends to upload a file to Dropbox
        When I run the workflow
        Then the file should be uploaded to Dropbox
