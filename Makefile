# Do not:
# o  use make's built-in rules and variables
#    (this increases performance and avoids hard-to-debug behaviour);
# o  print "Entering directory ...";
MAKEFLAGS += -rR --no-print-directory --warn-undefined-variables -O 

REPO := $(notdir $(abspath .))
REPO := ${REPO:docker-%=%}
REPO := ${USER}/${REPO}

TAGS := latest yakkety xenial trusty
TAG ?= $(firstword ${TAGS})

all: build

ifneq ("$(wildcard Makefile.deps)","")
include Makefile.deps
endif

##
## Single
##

.PHONY: bash bash-verbose bash-debug bash-trace

RUN_CMDS := bash bash-verbose bash-debug bash-trace

${RUN_CMDS}: TAGS = ${TAG}
${RUN_CMDS}: CMD = bash
${RUN_CMDS}: run

export ENTRYPOINT_DEBUG ENTRYPOINT_VERBOSE ENTRYPOINT_TRACE
bash-debug: 	ENTRYPOINT_DEBUG=1
bash-verbose: ENTRYPOINT_VERBOSE=1
bash-trace: 	ENTRYPOINT_TRACE=1

RUN_CMD ?= docker run -it --rm -v ${PWD}:/app

run: build
	${RUN_CMD} \
		-e ENTRYPOINT_VERBOSE=${ENTRYPOINT_VERBOSE} \
		-e ENTRYPOINT_DEBUG=${ENTRYPOINT_DEBUG} \
		-e ENTRYPOINT_TRACE=${ENTRYPOINT_TRACE} \
		"${REPO}:build-${TAG}" \
		${CMD}


##
## Lifecycle
##

.PHONY: ${TAGS}
.PHONY: all clean deps build test tag push ${TAGS}

deps: ${DEPS}

build: ${TAGS}

test: build
	(for TAG in ${TAGS}; do \
		BUILD_TAG=build-$$TAG; \
		${MAKE} -C tests "PARENT_TAG=$$BUILD_TAG"; \
	done)

tag: build
	(for TAG in ${TAGS}; do \
		BUILD_TAG=build-$$TAG; \
		docker tag "${REPO}:$$BUILD_TAG" "${REPO}:$$TAG"; \
	done)

push: tag
	(for TAG in ${TAGS}; do \
		BUILD_TAG=build-$$TAG; \
		docker push "${REPO}:$$TAG"; \
	done)

clean:
	rm -rf $(addprefix Dockerfile.,${TAGS})

distclean: clean
	rm -rf ${DEPS}


.SECONDEXPANSION:

Dockerfile.%: Dockerfile
	sed -e 's/^\(FROM .*\)\(:.*\|\)$$/\1:$*/' $^ > $@

${TAGS}: Dockerfile.$$@ deps
	docker build -f "$(firstword $^)" -t "${REPO}:build-$@" .


