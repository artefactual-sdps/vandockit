# VanDocs-AM-packager

Python command line scripts to read and validate a VanDocs transfer directory,
and output an Archivematica compliant SIP.

## Validator

`validate_package.py` is a CLI entry point for validating that a directory meets
the expected VanDocs transfer directory and file structure. To validate a
VanDocs transfer, run:

```
./validate_package.py vandocs path/to/package/
```
