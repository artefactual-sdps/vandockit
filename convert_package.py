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
import logging.config
import sys
from datetime import datetime
from pathlib import Path

# Local modules
from vandocs_converter.package_converter import VanDocsPackageConverter
from vandocs_validator.package_validator import PackageValidatorFactory

# Constants
SRC_PACKAGE_TYPE = "VanDocs"


def config_logging():
    """Configure logging"""

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

    log_filename = "convert_package_{}.log".format(
        datetime.now().strftime("%Y%m%d_%H%M%S")
    )
    log_path = logdir / log_filename

    file_logger = logging.FileHandler(log_path)
    file_logger.setLevel(logging.INFO)
    file_logger.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    )
    logger.addHandler(file_logger)


def box_msg(msg):
    """Embed message in a 78 character width box"""

    return """
==============================================================================
{}
==============================================================================
""".format(
        msg
    )


def print_summary(msg, has_errors, box=False):
    """Print a formatted summary message"""

    color = "red" if has_errors else "green"
    if box:
        msg = box_msg(msg)

    click.echo(click.style("\n" + click.wrap_text(msg), fg=color))


def validate(path):
    """Validate the VanDocs package"""

    validator = PackageValidatorFactory.get_validator(SRC_PACKAGE_TYPE, path)
    validator.validate()

    if validator.is_valid():
        print_summary(validator.get_summary_msg(), False)
    else:
        print_summary(validator.get_summary_msg(), True, True)

        # Exit with error code 1 if source package isn't valid
        sys.exit("Validation failed with one or more errors")


def convert(source_path, dest_path):
    """Convert each VanDocs container to an Archivematica standard transfer"""

    converter = VanDocsPackageConverter(source_path)
    converter.convert(dest_path)

    print_summary(converter.get_summary_msg(), converter.has_errors(), True)

    if converter.errors:
        sys.exit("Conversion failed with one or more errors")


@click.command()
@click.argument(
    "source_path", type=click.Path(exists=True, file_okay=False, readable=True)
)
@click.argument("dest_path", type=click.Path())
def main(source_path, dest_path):
    """
    USAGE:
    convert_package.py SOURCE_PATH TARGET_PATH

    Validate the VanDocs package at SOURCE_PATH then, if validation succeeds,
    creates one Archivematica standard transfer directory for each VanDocs
    container as a sub-directory of TARGET_PATH.
    """

    config_logging()

    # Log script arguments
    logging.info(" ".join(["Executing:"] + sys.argv))

    validate(source_path)
    convert(source_path, dest_path)


if __name__ == "__main__":
    main()
