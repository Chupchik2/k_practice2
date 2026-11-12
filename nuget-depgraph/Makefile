PYTHON ?= python3
CONFIG ?= config.example.json
export PYTHONPATH := src

.PHONY: run test

run:
	$(PYTHON) -m depgraph --config $(CONFIG)

test:
	$(PYTHON) -m unittest discover -s tests -v
