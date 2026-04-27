<!-- markdownlint-disable MD024 -->
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.3.0] 2026-04-27

### Added

- A zip flag (--zip, -z) for the convert command that zips the created
  Archivematica standard transfers (#13)
- Github issue templates
- CHANGELOG.md

## [1.2.0] 2026-04-15

### Added

- a list of the AM transfers created by convert is written to standard out and
  log
- Github CI workflow to run tests and linter on pull request and merge to main

### Changed

- Remove personally identifying information (PII) from the Location.xml files
  written by convert
- Log file name to include the transfer number (#3)
- Upgrade dependencies: pygments, pytest

## [1.1.0] 2025-12-11

### Changed

- Switch to [ruff](https://github.com/astral-sh/ruff) for linting and update
  code to address linter warnings
- Move repo from Gitlab to Github, and update internal links
- Upgrade dev dependencies
- Upgrade [click](https://pypi.org/project/click/) from v8.0.3 to v8.3.1
