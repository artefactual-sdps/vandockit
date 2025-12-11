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

import logging
import time
from os import scandir
from pathlib import Path

# Local modules
from vandockit.metadata_xml_parser import DocumentXmlParser


class PackageValidatorFactory:
    def get_validator(type, path):
        if type.lower() == "vandocs":
            return PackageValidator(type, path)

        raise ValueError(f'No validator found for package type "{type}"')


class BaseValidator:
    required_files = []
    timer = {"validation": {"start": None, "end": None}}

    def __init__(self, type, path):
        self.failed = self.checked = 0
        self.type = type
        self.path = Path(path)

    def get_name(self):
        return self.path.name

    def context_prefix(self):
        return f'Package "{self.get_name()}" '

    def is_valid(self):
        # Return None if no validation checks have been done
        if self.checked > 0:
            return 0 == self.failed

    def has_errors(self):
        return self.failed > 0

    def start_timer(self, timer_name):
        self.timer[timer_name]["start"] = time.time()

    def stop_timer(self, timer_name):
        self.timer[timer_name]["end"] = time.time()

    def get_elapsed_time(self, timer_name, multi=1):
        if (
            self.timer[timer_name]
            and self.timer[timer_name]["start"]
            and self.timer[timer_name]["end"]
        ):
            elapsed = (
                self.timer[timer_name]["end"] - self.timer[timer_name]["start"]
            )

            return elapsed * multi

    def get_contents(self):
        if not self.path.exists():
            raise FileNotFoundError

        if not self.path.is_dir():
            raise NotADirectoryError

        return self.path.iterdir()

    def has_required_files(self):
        failed = False

        for filename in self.required_files:
            self.checked += 1

            if filename not in [x.name for x in self.get_contents()]:
                self.failed += 1
                failed = True

                logging.error(
                    self.context_prefix() + 'is missing required file "%s"',
                    filename,
                )

        if not failed:
            logging.info(self.context_prefix() + "has all required files")

        return not failed

    def get_summary_msg(self):
        if self.is_valid():
            msg = 'VALID: all {} checks for Package "{}" passed [{:.3}s]'

            return msg.format(
                self.checked,
                self.path.name,
                self.get_elapsed_time("validation", 1),
            )
        else:
            msg = 'INVALID: {} of {} checks for Package "{}" failed [{:.3}s]'

            return msg.format(
                self.failed,
                self.checked,
                self.path.name,
                self.get_elapsed_time("validation", 1),
            )

    def log_summary_msg(self):
        log_level = logging.INFO if self.is_valid() else logging.ERROR
        logging.log(level=log_level, msg=self.get_summary_msg())


class PackageValidator(BaseValidator):
    required_files = [
        "manifest.txt",
        "Location.xml",
        "TransferLog.txt",
        "VanDocsDispositionContainerDocumentMetadataSchema.xsd",
        "VanDocsDispositionContainerMetadataSchema.xsd",
        "VanDocsDispositionLocationMetadataSchema.xsd",
    ]

    def get_containers(self):
        containers = []

        with scandir(self.path) as contents:
            for item in contents:
                if item.is_dir():
                    containers.append(item.name)

        return containers

    def validate(self):
        self.start_timer("validation")
        self.has_required_files()
        self.has_empty_transfer_log()
        self.has_a_container()

        # Validate containers
        for name in self.get_containers():
            validator = ContainerValidator(self.type, self.path / name)
            validator.validate()

            # Add checked and failed stats from container validator
            self.failed += validator.failed
            self.checked += validator.checked

        self.stop_timer("validation")
        self.log_summary_msg()

        return 0 == self.failed

    def has_empty_transfer_log(self):
        self.checked += 1
        logpath = self.path / "TransferLog.txt"

        if not logpath.exists():
            # This is already flagged as an failure in has_required_files()
            return False

        if logpath.stat().st_size > 0:
            self.failed += 1
            logging.error(
                self.context_prefix()
                + "TransferLog.txt is present but not empty (%sB)",
                logpath.stat().st_size,
            )

            return False

        # Passed!
        logging.info(
            self.context_prefix() + "TransferLog.txt is present and empty (0B)"
        )

        return True

    def has_a_container(self):
        self.checked += 1
        passed = False

        if len(self.get_containers()) > 0:
            passed = True
            logging.info(self.context_prefix() + "has one or more containers")
        else:
            self.failed += 1
            logging.error(self.context_prefix() + "has no containers")

        return passed


class ContainerValidator(BaseValidator):
    required_files = ["ContainerMetadata.xml"]

    def context_prefix(self):
        return f'Container "{self.get_name()}" '

    def validate(self):
        self.has_required_files()

        (
            object_filenames,
            metadata_filenames,
        ) = self.split_object_and_metadata_filenames()

        if not self.has_objects(object_filenames):
            return False

        self.has_one_metadata_file_per_object(
            object_filenames, metadata_filenames
        )
        self.has_one_object_per_metadata_file(
            object_filenames, metadata_filenames
        )
        self.has_checksum_metadata(metadata_filenames)

        return 0 == self.failed

    def split_object_and_metadata_filenames(self):
        object_filenames = []
        metadata_filenames = []

        for item in self.get_contents():
            if item.name in self.required_files:
                # Skip container metadata file
                continue

            if item.name.endswith("_Metadata.xml"):
                metadata_filenames.append(item.name)
            else:
                object_filenames.append(item.name)

        return object_filenames, metadata_filenames

    def has_objects(self, object_filenames):
        self.checked += 1

        if 0 == len(object_filenames):
            self.failed += 1
            logging.error(self.context_prefix() + "no objects in container")

            return False

        logging.info(
            self.context_prefix() + f"has {len(object_filenames)} objects"
        )

        return True

    def has_one_metadata_file_per_object(
        self, object_filenames, metadata_filenames
    ):
        self.checked += 1
        failed = False

        for filename in object_filenames:
            md_filename = self.get_filename_stem(filename) + "_Metadata.xml"

            if md_filename not in metadata_filenames:
                self.failed += 1
                failed = True

                logging.error(
                    self.context_prefix()
                    + '"%s" file has no corresponding "%s" metadata file',
                    filename,
                    md_filename,
                )

        if not failed:
            logging.info(
                self.context_prefix()
                + "every object file has a corresponding metadata file"
            )

        return not failed

    def has_one_object_per_metadata_file(
        self, object_filenames, metadata_filenames
    ):
        self.checked += 1
        failed = False

        for md_filename in metadata_filenames:
            found = False

            for filename in object_filenames:
                if self.get_metadata_basename(
                    md_filename
                ) == self.get_filename_stem(filename):
                    found = True

                    break

            if not found:
                self.failed += 1
                failed = True

                logging.error(
                    self.context_prefix()
                    + 'metadata file "%s" has no corresponding object file',
                    md_filename,
                )

        if not failed:
            logging.info(
                self.context_prefix()
                + "every metadata file has a corresponding object file"
            )

        return not failed

    def has_checksum_metadata(self, metadata_filenames):
        self.checked += 1
        failed = False

        for md_filename in metadata_filenames:
            hash = None
            parser = DocumentXmlParser(self.path / md_filename)

            try:
                hash = parser.get_md5_hash()
            except RuntimeError:
                logging.error(
                    self.context_prefix()
                    + 'Couldn\'t read md5 hash from "%s"',
                    md_filename,
                )

            if not hash:
                self.failed += 1
                failed = True

        if not failed:
            logging.info(
                self.context_prefix()
                + "every metadata file has an MD5 hash value",
            )

        return not failed

    def get_filename_stem(self, filename):
        # Remove any extensions (everything after the first period)
        parts = filename.split(".")

        return parts[0]

    def get_metadata_basename(self, filename):
        if filename.endswith("_Metadata.xml"):
            # Remove final 13 chars
            filename = filename[:-13]

        return filename
