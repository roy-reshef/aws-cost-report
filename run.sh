#!/usr/bin/env bash
docker build -t reshef/cost_reporter .

docker run -e AWS_ACCESS_KEY_ID="${AWS_ACCESS_KEY_ID}" \
           -e AWS_SECRET_ACCESS_KEY="${AWS_SECRET_ACCESS_KEY}" \
           -e REGION_NAME="${REGION_NAME}" \
           -e LOGGING_LEVEL="${LOGGING_LEVEL}" \
           -v ~/cost_reports:/cost_reporter/generated-reports \
           --name=reshef_cost_reporter \
           --rm \
           reshef/cost_reporter
