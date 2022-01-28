#!/usr/bin/env python3

import click
from datetime import datetime
import logging
import logging.config
import os

# Local modules
import validators.package_validators as validators


def config_logging():
    logdir = "logs/"

    if not os.path.exists(logdir):
        os.mkdir(logdir, mode=0o755)

    logging.addLevelName(logging.INFO, "PASS")
    logging.addLevelName(logging.ERROR, "FAIL")

    logging.config.fileConfig(
        os.path.join("conf", "logging.conf"),
        defaults={
            "logname": os.path.join(
                "logs",
                "validate_package_{}.log".format(
                    datetime.now().strftime("%Y%m%d_%H%M%S")
                ),
            )
        },
    )


@click.command()
@click.argument("type")
@click.argument("path", type=click.Path(exists=True))
def main(type, path):
    """
    validate_package is a command line tool for validating the given directory
    matches the expected package structure

    To run:
    validate_package.py PACKAGE_TYPE PATH

    PACKAGE_TYPE only supports the "vandocs" type right now.

    PATH is the path of the directory to be validated.
    """
    config_logging()
    validator = validators.PackageValidatorFactory.get_validator(type, path)

    validator.validate()


if __name__ == "__main__":
    main()
