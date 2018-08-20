Redshift manual snapshot manager Lambda function
=================================================

This script is for managing Redshift manual snapshots - Creating manual snapshots from latest automated snapshot and removing snapshots which are older than retention period specifies. 

Features
--------
#### Creating manual snapshots

The function for creating manual snapshots (`redshift_manual_snap`) will loop through all Redshift automated snapshots and will sort them by the most recent date. Then manual snapshot will be taken for the latest automated snapshot for each of the cluster in the AWS region.

#### Removing manual snapshots

The function for removing manual snapshots (`redshift_snapshot_remover`) will loop through all Redshift manual snapshots and will compare the snapshot creatin date with the retention period which is set up as environment variable (See below). If certain snapshots needs to persist, the function will need to be adjusted to exclude those snapshots, or in this case there is also environment variable called `max_back` which will specify the maximum time to look back for old snapshots, therefore if you need to persist snapshots taken months ago, set the value of `max_back` to for example 30 so the function will not remove any snapshots taken more than 30 days ago. 

#### SNS notifications on failures

The function to push message to SNS (`notify_devops`) will publish message to SNS topic, which needs to be set up as an environment variable. It is recommended to subscribe an email DL to this SNS or any other service (Http endpoint, SQS etc) so the correct team or service is notified if needed. The notification in this case will be for any failures when running the script. 

#### Logging

The function will put all logs to Cloudwatch Logs. There is no setup needed for this and the only requirements is to have Lambda configured with the correct role/permissions (See below). After the first run, new Log Group will be automatically created (Something like `/aws/lambda/YOURFUNCTIONNAME`) and logs will be added after each run. 

Initial Setup
-------------

#### Lambda Function

This Lambda function should be setup in the AWS region where the Redshift cluster exists and one wish to take the manual snapshots. The function should be set up as `Python 2.7` Runtime and the Handler should be the main function `lambda_function.lambda_handler`. In order for this function to work, proper IAM role needs to be attached - this IAM role needs to have access to Redshift as well as to Cloudwatch logs. Since the function needs to read/write data, it's recommended for the role to use AWS Managed policies `AmazonRedshiftFullAccess` and `CloudWatchLogsFullAccess`. It's also recommended to increase the Lambda Timeout based on the environment and number and size of Redshift clusters, but 30 seconds should be fine for most cases. 

#### Triggers

Amazon is taking automated Redshift cluster snapshots multiple times per day, usually every 8 hours or following every 5 GB of data change. This script is designed to take the manual snapshot of the latest automated snapshot for each cluster and WILL NOT take snapshots of EACH automated snapshot - if there is the need to take manual snapshot for each automated snapshot, this script will need to be re-written. Since this script is taking one manual snapshot a day, it is recommended to set up the Lambda trigger as Cloudwatch Events Schedule: For example `cron(0 4 * * ? *)` will invoke the function every day at 4 am GMT. 

#### Environment variables

The script requires 3 environment variables to be set up. The variables are to set Retention Period, SNS topic ARN and Maximum time to look back for any manual snapshots - this is to avoid deleting any old legacy snapshots which may be still needed in the future. An example of the variable's setup can be seen here (The key is required, values can be changed):

```json
{
  "ret_period":"7",
  "sns_topic":"arn:aws:sns:us-east-1:123456789101:topic_name",
  "max_back":"25"  
}
```

