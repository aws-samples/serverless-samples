# Create Resources with Terraform

This folder contains a [Terraform](https://www.terraform.io/downloads) file that creates an [Amazon SQS](https://aws.amazon.com/sqs/) queue and stores its arn in [AWS Systems Manager Parameter Store](https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-parameter-store.html).

## Requirements

* You must have [Terraform](https://www.terraform.io/downloads) installed on your computer.
* You must have an [Amazon Web Services](http://aws.amazon.com/) (AWS) account.

## Set up credentials

Terraform uses [AWS access keys](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_access-keys.html) to provision and configure resources in your cloud environment.

  **Important:** For security purposes, we recommend that you use IAM users instead of the root account for AWS access.

  Setting your credentials for use by Terraform can be done in a number of ways, but here are the two recommended approaches:

  * Use the default credentials file:
  
    Set credentials in the AWS credentials profile file on your local system, located at:

    `~/.aws/credentials` on Linux, macOS, or Unix

    `C:\Users\USERNAME\.aws\credentials` on Windows

    This file should contain lines in the following format:

    ```bash
    [default]
    aws_access_key_id = <your_access_key_id>
    aws_secret_access_key = <your_secret_access_key>
    ```
    Substitute your own AWS credentials values for the values `<your_access_key_id>` and `<your_secret_access_key>`.

  * Use environment variables: 
  
    Set the `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` environment variables.

    To set these variables on Linux, macOS, or Unix, use `export`:

    ```bash
    export AWS_ACCESS_KEY_ID=<your_access_key_id>
    export AWS_SECRET_ACCESS_KEY=<your_secret_access_key>
    ```

    To set these variables on Windows, use `set`:

    ```bash
    set AWS_ACCESS_KEY_ID=<your_access_key_id>
    set AWS_SECRET_ACCESS_KEY=<your_secret_access_key>
    ```

## Deploy resources using Terraform

* Navigate to the Terraform working directory at `/terraform-sam-integration/terraform`.

* Initialize working directory.

  The first command that should be run after writing a new Terraform configuration is the `terraform init` command in order to initialize a working directory containing Terraform configuration files. It is safe to run this command multiple times.

  ```bash
  terraform init
  ```

* Validate the changes.

  Run command:

  ```bash
  terraform plan
  ```

* Deploy the changes.

  Run command:

  ```bash
  terraform apply
  ```

* Copy the queue URL.

  When the `terraform apply` command completes, use the AWS console, you should see the URL of the queue as an output. Make note of this URL.
    
* Deploy resources with SAM. 

  To complete this project, you may now follow the instructions in this [README](../sam/README.md) to deploy resources using SAM.

* Clean up.

  When you have finished with this project and you are ready to destroy your resources, run the command:

  ```bash
  terraform destroy
  ```
