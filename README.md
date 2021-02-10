# aws-cost-report
AWS Costs report generation tool 

## Overview

AWS Costs report tool which leverages AWS cost explorer API to create single page HTML report.<br>

## Features
* Provides data for every linked account
* S3 persistence 
* Single or scheduled execution
* Configurable time windows
* Report data
  - Monthly total forecast
  - Last day cost
  - Daily cost chart
  - Monthly cost chart 
  - Services cost
  - Cost chart per requested tag

## Prerequisites

Python3 for running on machine
Docker in order to run inside container
make tool in order to execute Makefile targets

## Execution

You can execute report tool using Makefile targets or directly install / execute report tool (explained below)<br>
Please see Makefile for available targets (options)

### Machine
it is advisable to use [virtual environment](https://docs.python.org/3/library/venv.html)
* execute ```pip install -r requirements.txt``` to install project requirements<br>
* execute ```python run.py ```<br>

in this mode reports are generated in 'generated-reports' directory

### Docker
execute ```run_in_docker.sh``` script to build and run report generation inside docker<br>
reports will be available under <USER_HOME_DIR>/cost_reports


## ENV variables
    environment variables for both local and docker executions
aws credentials environment variables (required):
* AWS_ACCESS_KEY_ID 
* AWS_SECRET_ACCESS_KEY
* REGION_NAME

* LOGGING_LEVEL - optional. defaults to INFO

## Configuration
### Example Configuration File
```
{
  "report_title": "AWS Costs Report",
  "accounts" : {
    "1111": "Development",
    "2222": "staging",
    "3333": "Production"
  },
  "periods" : {
    "monthly_report_months_back": 6,
    "services_report_days_back": 30,
    "tags_report_days_back": 30,
    "daily_report_days_back": 30
  },
  "filtered_services": [
    "Tax",
    "AWS Elemental MediaStore",
    "Amazon QuickSight",
    "AWS Data Pipeline",
    "AWS Cost Explorer",
    "AWS Key Management Service"
  ],
  "filtered_costs": [
    "Credit",
    "Refund",
    "Upfront"
  ],
  "resource_tags": [
    "env"
  ],
  "destinations": {
    "s3": {
      "bucket_name": "<unique bucket name>",
      "object_name": ""
    }
  },
  "template_name": "default.html",
  "schedule": "*/5 * * * *",
  "use_cache": true
}
```
### Configuration Options
* **report_title** - as the name suggests :-)
* **accounts** -
* **periods** -
* **filtered_services** -
* **filtered_costs** -
* **resource_tags** -
* **destinations** -
* **template_name** -
* **schedule** -
* **use_cache** -

## Report Template
Report is generated from jinja template. alternative templates can be placed in report_templates
directory and configured in configuration file

## scheduling
cron based report scheduling can be specified by setting 'schedule' configuration option. <br>
for scheduling options please see [croniter](https://pypi.org/project/croniter/) documentation<br>
<b>Note:</b> seconds interval not supported
