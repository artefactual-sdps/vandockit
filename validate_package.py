#!/usr/bin/env python3

# This file is part of VanDocs-AM-Packager.
#
# Copyright 2022 Artefactual Systems Inc. <http://artefactual.com>
#
# VanDocs-AM-Packager is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# VanDocs-AM-Packager is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with VanDocs-AM-Packager.  If not, see <http://www.gnu.org/licenses/>.

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
