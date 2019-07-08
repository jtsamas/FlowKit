#
# Makefile for Flowkit.
#
# This is not needed to actually build anything in Flowkit, but it
# contains convenience targets to spin up or tear down individual
# Flowkit docker containers.
#
# For instance, run `make up` to spin up all docker containers, or
# `make flowapi-down` to tear down the docker container for flowapi
# only.
#
# By setting the variable DOCKER_SERVICES you can choose which services
# you'd like to use when running `make up`. Note that at most one flowdb
# service must be specified. Examples:
#
#     DOCKER_SERVICES="flowdb_synthetic_data flowapi flowmachine flowauth flowmachine_query_locker" make up
#     DOCKER_SERVICES="flowdb" make up
#     DOCKER_SERVICES="flowdb_testdata flowetl flowetl_db" make up
#
# flowmachine and flowapi will connected to the first flowdb service in the list.

DOCKER_COMPOSE_FILE ?= docker-compose.yml
DOCKER_COMPOSE_TESTDATA_FILE ?= docker-compose-testdata.yml
DOCKER_COMPOSE_SYNTHETICDATA_FILE ?= docker-compose-syntheticdata.yml
DOCKER_COMPOSE_FILE_BUILD ?= docker-compose-build.yml
DOCKER_SERVICES ?= flowdb_testdata flowapi flowmachine flowauth flowmachine_query_locker flowetl flowetl_db worked_examples

# Check that at most one flowdb service is present in DOCKER_SERVICES
NUM_SPECIFIED_FLOWDB_SERVICES=$(words $(filter flowdb%, $(DOCKER_SERVICES)))
ifneq ($(NUM_SPECIFIED_FLOWDB_SERVICES),0)
  ifneq ($(NUM_SPECIFIED_FLOWDB_SERVICES),1)
    $(error "At most one flowdb service must be specified in DOCKER_SERVICES, but found: $(filter flowdb%, $(DOCKER_SERVICES))")
  endif
endif

all:

up: flowdb-build
	docker-compose -f $(DOCKER_COMPOSE_FILE) -f $(DOCKER_COMPOSE_FILE_BUILD)  up -d --build $(DOCKER_SERVICES)

up-no_build:
	docker-compose -f $(DOCKER_COMPOSE_FILE) up -d $(DOCKER_SERVICES)

down:
	docker-compose -f $(DOCKER_COMPOSE_FILE) down -v


# Note: the targets below are repetitive and could be simplified by using
# a pattern rule as follows:
#
#   %-up: %-build
#       docker-compose -f $(DOCKER_COMPOSE_FILE) up -d --build $*
#
# The reason we are keeping the explicitly spelled-out versions is in order
# to increase discoverability of the available Makefile targets and to enable
# tab-completion of targets (which is not possible when using patterns).


flowdb-up: flowdb-build
	docker-compose -f $(DOCKER_COMPOSE_FILE) -f $(DOCKER_COMPOSE_FILE_BUILD) up -d --build flowdb

flowdb-down:
	docker-compose -f $(DOCKER_COMPOSE_FILE) rm -f -s -v flowdb

flowdb-build:
	docker-compose -f $(DOCKER_COMPOSE_FILE) -f $(DOCKER_COMPOSE_FILE_BUILD) build flowdb


flowdb_testdata-up: flowdb_testdata-build
	docker-compose -f $(DOCKER_COMPOSE_TESTDATA_FILE) -f $(DOCKER_COMPOSE_FILE_BUILD) up -d --build flowdb_testdata

flowdb_testdata-down:
	docker-compose -f $(DOCKER_COMPOSE_TESTDATA_FILE) rm -f -s -v flowdb_testdata

flowdb_testdata-build: flowdb-build
	docker-compose -f $(DOCKER_COMPOSE_TESTDATA_FILE) -f $(DOCKER_COMPOSE_FILE_BUILD) build flowdb_testdata


flowdb_synthetic_data-up: flowdb_synthetic_data-build
	docker-compose -f $(DOCKER_COMPOSE_SYNTHETICDATA_FILE) -f $(DOCKER_COMPOSE_FILE_BUILD) up -d --build flowdb_synthetic_data

flowdb_synthetic_data-down:
	docker-compose -f $(DOCKER_COMPOSE_SYNTHETICDATA_FILE) rm -f -s -v flowdb_synthetic_data

flowdb_synthetic_data-build: flowdb-build
	docker-compose -f $(DOCKER_COMPOSE_SYNTHETICDATA_FILE) -f $(DOCKER_COMPOSE_FILE_BUILD) build flowdb_synthetic_data


flowmachine-up:
	docker-compose -f $(DOCKER_COMPOSE_FILE) -f $(DOCKER_COMPOSE_FILE_BUILD) up -d --build flowmachine

flowmachine-down:
	docker-compose -f $(DOCKER_COMPOSE_FILE) rm -f -s -v flowmachine

flowmachine-build:
	docker-compose -f $(DOCKER_COMPOSE_FILE) -f $(DOCKER_COMPOSE_FILE_BUILD) build flowmachine


flowapi-up:
	docker-compose -f $(DOCKER_COMPOSE_FILE) -f $(DOCKER_COMPOSE_FILE_BUILD) up -d --build flowapi

flowapi-down:
	docker-compose -f $(DOCKER_COMPOSE_FILE) rm -f -s -v flowapi

flowapi-build:
	docker-compose -f $(DOCKER_COMPOSE_FILE) -f $(DOCKER_COMPOSE_FILE_BUILD) build flowapi


flowauth-up:
	docker-compose -f $(DOCKER_COMPOSE_FILE) -f $(DOCKER_COMPOSE_FILE_BUILD) up -d --build flowauth

flowauth-down:
	docker-compose -f $(DOCKER_COMPOSE_FILE) rm -f -s -v flowauth

flowauth-build:
	docker-compose -f $(DOCKER_COMPOSE_FILE) -f $(DOCKER_COMPOSE_FILE_BUILD) build flowauth


worked_examples-up: worked_examples-build
	docker-compose -f $(DOCKER_COMPOSE_FILE) -f $(DOCKER_COMPOSE_FILE_BUILD) up -d --build worked_examples

worked_examples-down:
	docker-compose -f $(DOCKER_COMPOSE_FILE) rm -f -s -v worked_examples

worked_examples-build:
	docker-compose -f $(DOCKER_COMPOSE_FILE) -f $(DOCKER_COMPOSE_FILE_BUILD) build worked_examples


flowmachine_query_locker-up:
	docker-compose -f $(DOCKER_COMPOSE_FILE) up -d flowmachine_query_locker

flowmachine_query_locker-down:
	docker-compose -f $(DOCKER_COMPOSE_FILE) rm -f -s -v flowmachine_query_locker

flowetl-up:
	docker-compose -f $(DOCKER_COMPOSE_FILE) -f $(DOCKER_COMPOSE_FILE_BUILD) up -d --build flowetl

flowetl-down:
	docker-compose -f $(DOCKER_COMPOSE_FILE) rm -f -s -v flowetl

flowetl-build:
	docker-compose -f $(DOCKER_COMPOSE_FILE) -f $(DOCKER_COMPOSE_FILE_BUILD) build flowetl

flowetl_db-up:
	docker-compose -f $(DOCKER_COMPOSE_FILE) -f $(DOCKER_COMPOSE_FILE_BUILD) up -d --build flowetl_db

flowetl_db-down:
	docker-compose -f $(DOCKER_COMPOSE_FILE) rm -f -s -v flowetl_db