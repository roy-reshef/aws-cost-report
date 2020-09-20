# aws-cost-report
AWS Costs report generation tool 

## Overview

AWS Costs report tool which leverages AWS cost explorer API to create single page HTML report.<br>

The tool provides the following data per account (linked accounts):
* Monthly total forecast
* Last day cost
* Daily cost chart
* Monthly cost chart 
* AWS Services cost
* Cost chart per requested tag

## Prerequisites

Python3
Docker in order to run inside container

## Execution

### Local
it is advisable to use [virtual environment](https://docs.python.org/3/library/venv.html)
* execute ```pip install -r requirements.txt``` to install project requirements<br>
* execute ```python cost_report_generator.py ```<br>

in this mode reports are generated in 'generated-reports' directory

### Docker
execute ```run.sh``` script to run report generation inside docker<br>
reports will be available under <HOME_DIR>/generated-report


## ENV variables
    environment variables for both local and docker executions
aws credentials environment variables (required):
* AWS_ACCESS_KEY_ID 
* AWS_SECRET_ACCESS_KEY
* REGION_NAME

* LOGGING_LEVEL - optional. defaults to INFO

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
      "bucket_name": "linearb-aws-cost-reports",
      "object_name": ""
    }
  },
  "template_name": "default.html"
}
```

## Report Template
Report is generated from jinja template. alternative templates can be placed in report_templates 
directory and configured in configuration file

## artifacts
generated report file and partial reports like tag report files are generated in 'generated-reports' directory<br>
generated report is suffixed with execution date <br>
report can optionally be uploaded to S3 by providing s3 destination configuration (see example) 


