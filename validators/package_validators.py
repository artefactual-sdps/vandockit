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

from pathlib import Path

import logging
import xml.etree.ElementTree as ET

# Use the built-in version of scandir for Python 3.5+ otherwise use the scandir
# module version
try:
    from os import scandir
except ImportError:
    from scandir import scandir


class PackageValidatorFactory:
    def get_validator(type, path):
        if type.lower() == "vandocs":
            return VanDocsValidator(type, path)

        raise ValueError('No validator found for package type "{}"'.format(type))


class PackageValidator:
    required_files = []

    def context_prefix(self):
        return 'Package "{}" '.format(self.get_name())

    def __init__(self, type, path):
        self.failed = self.checked = 0
        self.type = type
        self.path = Path(path)

    def get_name(self):
        return self.path.name

    def get_contents(self):
        if not self.path.exists():
            raise FileNotFoundError

        if not self.path.is_dir():
            raise NotADirectoryError

        return self.path.iterdir()

    def has_required_files(self):
        self.checked += 1
        missing_files = []

        for filename in self.required_files:
            if filename not in [x.name for x in self.get_contents()]:
                missing_files.append(filename)

        if 0 == len(missing_files):
            logging.info(self.context_prefix() + "has all required metadata files")
        else:
            self.failed += 1
            logging.error(
                self.context_prefix() + "missing required metadata file(s) (%s)",
                ", ".join(missing_files),
            )

        return 0 == len(missing_files)


class VanDocsValidator(PackageValidator):
    required_files = ["manifest.txt", "Location.xml"]

    def get_containers(self):
        containers = []

        with scandir(self.path) as contents:
            for item in contents:
                if item.is_dir():
                    containers.append(item.name)

        return containers

    def validate(self):
        self.has_required_files()
        self.has_empty_transfer_log()
        self.has_a_container()

        # Validate containers
        for name in self.get_containers():
            validator = VanDocsContainerValidator(self, self.path / name)
            validator.validate()

            # Add checked and failed stats from container validator
            self.failed += validator.failed
            self.checked += validator.checked

        return 0 == self.failed

    def has_empty_transfer_log(self):
        self.checked += 1
        logpath = self.path / "TransferLog.txt"

        if not logpath.exists():
            self.failed += 1
            logging.error(self.context_prefix() + "TransferLog.txt is missing")

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


class VanDocsContainerValidator(PackageValidator):
    required_files = ["ContainerMetadata.xml"]

    def __init__(self, package, path):
        PackageValidator.__init__(self, package.type, path)

        self.package = package

    def context_prefix(self):
        return 'Container "{}/{}" '.format(self.package.get_name(), self.get_name())

    def validate(self):
        self.has_required_files()

        (
            object_filenames,
            metadata_filenames,
        ) = self.split_object_and_metadata_filenames()

        if not self.has_objects(object_filenames):
            return False

        self.has_one_metadata_file_per_object(object_filenames, metadata_filenames)
        self.has_one_object_per_metadata_file(object_filenames, metadata_filenames)
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
            self.context_prefix() + "has {} objects".format(len(object_filenames))
        )

        return True

    def has_one_metadata_file_per_object(self, object_filenames, metadata_filenames):
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

    def has_one_object_per_metadata_file(self, object_filenames, metadata_filenames):
        self.checked += 1
        failed = False

        for md_filename in metadata_filenames:
            found = False

            for filename in object_filenames:
                if self.get_metadata_basename(md_filename) == self.get_filename_stem(
                    filename
                ):
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
            xmltree = self.parse_doc_metadata_xml(md_filename)

            if xmltree:
                hash = self.get_xml_md5_hash(xmltree)

            if not (xmltree and hash):
                self.failed += 1
                failed = True

                logging.error(
                    self.context_prefix() + 'Couldn\'t read md5 hash from "%s"',
                    md_filename,
                )

        if not failed:
            logging.info(
                self.context_prefix() + "every metadata file has an MD5 hash value",
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

    def parse_doc_metadata_xml(self, filename):
        try:
            with open(self.path / filename) as file:
                xmltree = ET.parse(file)
        except (ET.ParseError, UnicodeDecodeError):
            return None

        return xmltree.getroot()

    def get_xml_md5_hash(self, xmltree):
        nodes = xmltree.findall("./Document/MD5")

        if 0 == len(nodes):
            return None

        return nodes[0].text
