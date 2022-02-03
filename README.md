# VanDocs-AM-packager

Copyright 2022 Artefactual Systems Inc. <http://artefactual.com>

Python command line scripts to validate a VanDocs transfer package and convert
it to multiple Archivematica standard transfer packages (one per VanDocs
container).

## Validate package

```
validate_package.py PATH
```

`validate_package.py` validates that the VanDocs transfer package at PATH meets
the expected directory and file structure.

Validation errors are echoed to STDOUT and the script exits with error code 1.
All validation check outcomes (pass or fail) are logged to `logs/`.

## Convert package

```
convert_package.py SOURCE_PATH TARGET_PATH
```

`convert_package.py` validates the VanDocs transfer package at SOURCE_PATH then,
if valid, converts the package to multiple Archivematica standard transfer
packages in TARGET_PATH. One Archivematica transfer is created, as a
sub-directory of TARGET_PATH, for each container in the VanDocs transfer.

Validation and conversion errors are echoed to STDOUT and the script exits with
error code 1. All validation check and conversion step outcomes (pass or fail)
are logged to `logs/`.
