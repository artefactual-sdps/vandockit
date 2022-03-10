#!/usr/bin/env python3

# This file is part of VanDocs=AM=Packager.
#
# Copyright 2022 Artefactual Systems Inc. <http://artefactual.com>
#
# VanDocs=AM=Packager is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# VanDocs=AM=Packager is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with VanDocs=AM=Packager.  If not, see <http://www.gnu.org/licenses/>.

import click
import logging
import logging.config
import sys
from datetime import datetime
from pathlib import Path

# Local modules
from vandocs_am_converter.package_validator import PackageValidatorFactory


def config_logging():
    logdir = Path("logs/")

    if not logdir.exists():
        logdir.mkdir(0o755)

    logging.addLevelName(logging.INFO, "PASS")
    logging.addLevelName(logging.ERROR, "FAIL")

    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    logger.propagate = 0

    console_logger = logging.StreamHandler()
    console_logger.setLevel(logging.ERROR)
    console_logger.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    logger.addHandler(console_logger)

    log_filename = "validate_package_{}.log".format(
        datetime.now().strftime("%Y%m%d_%H%M%S")
    )
    log_path = logdir / log_filename

    file_logger = logging.FileHandler(log_path)
    file_logger.setLevel(logging.INFO)
    file_logger.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    )
    logger.addHandler(file_logger)


@click.command()
@click.argument("path", type=click.Path(exists=True))
def main(path):
    """
    USAGE:
    validate_package.py PATH

    Validate that the VanDocs transfer package at PATH matches the expected
    structure and contents.
    """
    config_logging()

    validator = PackageValidatorFactory.get_validator("VanDocs", path)
    valid = validator.validate()

    print_validation_summary(validator)

    if not valid:
        sys.exit(1)


def print_validation_summary(validator):
    color = "green" if validator.is_valid() else "red"

    box78 = """
==============================================================================
{}
==============================================================================
"""

    click.echo(
        click.style(
            click.wrap_text(box78.format(validator.get_summary_msg())),
            fg=color,
        )
    )


if __name__ == "__main__":
    main()
