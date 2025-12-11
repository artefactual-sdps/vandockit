# Vandockit

Copyright 2022 Artefactual Systems Inc. <http://artefactual.com>

A Python toolkit for VanDocs transfer packages

Tools:

- **validate**: Validate a VanDocs transfer package
- **convert**: Convert a VanDocs transfer package to multiple Archivematica
  standard transfer packages (one per VanDocs container)

## Installation

Clone the repository:

```bash
git clone git@gitlab.artefactual.com:clients/cva/vandockit.git
```

Change to the cloned directory and install with pip:

```bash
cd vandockit/
pip install .
```

## validate

```bash
vandockit validate PATH
```

Validates that the VanDocs transfer package at PATH meets the expected directory
and file structure.

Validation errors are echoed to STDOUT and the script exits with error code 1.
All validation check outcomes (pass or fail) are logged to `logs/`.

## convert

```bash
vandockit convert SOURCE_PATH DEST_PATH
```

Convert the VanDocs transfer package at SOURCE_PATH to one Archivematica
standard transfer directory per container in DEST_PATH.  Validates the
VanDocs package before conversion; validation failure prevents conversion.

Validation and conversion errors are echoed to STDOUT and the script exits with
error code 1. All validation check and conversion step outcomes (pass or fail)
are logged to `logs/`.

## make commands

Make is used to provide some utility scripts for Vandockit.

```bash
make init
```

Install Python production dependencies with pip.  If you installed Vandockit
with `pip install .` the production dependencies are already installed.

```bash
make init-dev
```

Install Python *development* dependencies (e.g. black, pytest) with pip.

```bash
make test
```

Run tests with Pytest. Requires `pytest` to be installed with `make init-dev` or
manually.

```bash
make test-cov
```

Run tests and display a coverage report in the terminal. Requires `pytest` and
`pytest-cov`, which are included in the development dependencies.
