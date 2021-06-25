SHELL := /bin/bash

HEAD_SHA=`git rev-parse --short HEAD`
IMAGE_NAME='reshef/cost_reporter'
CONAINER_NAME='reshef_cost_reporter'

head-sha:
	echo $(HEAD_SHA)

install:
	pip install -r requirements-dev.txt

flake8:
	@flake8 costreport

docker-build:
	docker build -t $(IMAGE_NAME):$(HEAD_SHA) .

docker-run:
	docker run -e AWS_ACCESS_KEY_ID="${AWS_ACCESS_KEY_ID}" \
                      -e AWS_SECRET_ACCESS_KEY="${AWS_SECRET_ACCESS_KEY}" \
                      -e REGION_NAME="${REGION_NAME}" \
                      -e LOGGING_LEVEL="${LOGGING_LEVEL}" \
                      -v ~/cost_reports:/cost_reporter/generated-reports \
                      --name=reshef_cost_reporter \
                      --rm \
                      $(IMAGE_NAME):$(HEAD_SHA)

list-images:
	docker images $(IMAGE_NAME)

delete-images:
	docker images $(IMAGE_NAME) -a -q | xargs docker rmi

run:
	python run.py
