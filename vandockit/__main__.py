#!/usr/bin/env python3

# This file is part of Vandockit.
#
# Copyright 2022 Artefactual Systems Inc. <http://artefactual.com>
#
# Vandockit is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Vandockit is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Vandockit.  If not, see <http://www.gnu.org/licenses/>.

import logging.config
import sys
from datetime import datetime
from pathlib import Path

import click

# Local modules
import vandockit
from vandockit.converters import PackageConverter
from vandockit.validators import PackageValidatorFactory

# Constants
SRC_PACKAGE_TYPE = "VanDocs"


def _config_logging(command, path):
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
    console_logger.setFormatter(
        logging.Formatter("[%(levelname)s] %(message)s")
    )
    logger.addHandler(console_logger)

    container_name = Path(path).stem.replace("VanDocs-", "")
    log_filename = "{}_{}_{}.log".format(
        container_name, command, datetime.now().strftime("%Y%m%d_%H%M%S")
    )
    log_path = logdir / log_filename

    file_logger = logging.FileHandler(log_path)
    file_logger.setLevel(logging.INFO)
    file_logger.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    )
    logger.addHandler(file_logger)


def _box_msg(msg):
    """Embed message in a 78 character width box"""

    return f"""
==============================================================================
{msg}
==============================================================================
"""


def _print_summary(msg, has_errors):
    """Print a formatted summary message"""

    color = "red" if has_errors else "green"
    click.echo(click.style("\n" + click.wrap_text(_box_msg(msg)), fg=color))


def _validate(path):
    try:
        validator = PackageValidatorFactory.get_validator(
            SRC_PACKAGE_TYPE, path
        )
        validator.validate()
    except Exception as exception:
        # Log and re-raise exceptions
        logging.critical(exception)
        raise exception

    return (validator.get_summary_msg(), validator.has_errors())


def _convert(source_path, dest_path):
    try:
        converter = PackageConverter(source_path)
        converter.convert(dest_path)
    except Exception as exception:
        # Log and re-raise exceptions
        logging.critical(exception)
        raise exception

    return (converter.get_summary_msg(), converter.has_errors())


@click.group()
@click.version_option(version=vandockit.__version__)
def main():
    """A Python toolkit for VanDocs transfer packages"""


@main.command("validate")
@click.argument("path", type=click.Path(exists=True))
def validate(path):
    """
    Validate that the VanDocs transfer package at PATH matches the expected
    structure and contents.
    """

    _config_logging("validate", path)

    # Log script invocation with arguments
    logging.info(" ".join(["Executing:"] + sys.argv))

    (summary_msg, has_errors) = _validate(path)

    _print_summary(summary_msg, has_errors)

    # Exit with error code 1 if source package isn't valid
    if has_errors:
        sys.exit("Validation failed with one or more errors")


@main.command("convert")
@click.argument(
    "source_path", type=click.Path(exists=True, file_okay=False, readable=True)
)
@click.argument("dest_path", type=click.Path())
def convert(source_path, dest_path):
    """
    Convert the VanDocs transfer package at SOURCE_PATH to one Archivematica
    standard transfer directory per container in DEST_PATH.  Validates the
    VanDocs package before conversion; validation failure prevents conversion.
    """

    _config_logging("convert", source_path)

    # Log script invocation with arguments
    logging.info(" ".join(["Executing:"] + sys.argv))

    (summary_msg, has_errors) = _validate(source_path)

    if not has_errors:
        (summary_msg, has_errors) = _convert(source_path, dest_path)

    _print_summary(summary_msg, has_errors)

    if has_errors:
        sys.exit("Conversion failed with one or more errors")


if __name__ == "__main__":
    main()
