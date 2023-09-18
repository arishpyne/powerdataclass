
PACKAGE_NAME?=powerdataclass

BUILDER_IMAGE?=pdc-builder
INTERACTIVE:=$(shell [ -t 0 ] && echo 1)
PYTHON_37_IMAGE?=python:3.7

DOCKER_USER_FLAG?=-u $(shell id -u)
DOCKER_FLAGS?=-t
ifeq ($(INTERACTIVE), 1)
DOCKER_FLAGS:=-it
endif


.PHONY: pytest pycodestyle build-builder-image build-and-publish-lib

build-builder-image:
	docker build -t ${BUILDER_IMAGE}:latest .

pytest: build-builder-image clean
	docker run $(DOCKER_USER_FLAG) --rm $(DOCKER_FLAGS) -v $(shell pwd):/build ${BUILDER_IMAGE} pytest -vvv

pycodestyle: build-builder-image clean
	docker run $(DOCKER_USER_FLAG) --rm $(DOCKER_FLAGS) -v $(shell pwd):/build ${BUILDER_IMAGE} pycodestyle --max-line-length=120 ${PACKAGE_NAME}

build-and-publish-lib: build-builder-image clean
	docker run $(DOCKER_USER_FLAG) --rm $(DOCKER_FLAGS) -e TWINE_USERNAME -e TWINE_PASSWORD -v $(shell pwd):/build $(BUILDER_IMAGE) bash build_and_publish_lib.sh

clean:
	rm -rf .pytest_cache
	rm -rf build
	rm -rf dist
	rm -rf *.egg-info