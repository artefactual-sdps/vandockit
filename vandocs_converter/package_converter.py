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

import logging
import shutil
import time
from pathlib import Path

# Local modules
from vandocs_parser.vandocs_xml_parser import (
    VanDocsContainerXmlParser,
    VanDocsDocumentXmlParser,
)
from archivematica_writer.metadata_csv_writer import AmMetadataCsvWriter


class PackageConverter:
    # Package file types
    FT_PRESERVATION_OBJECT = 1
    FT_CHECKSUM = 2
    FT_DESC_METADATA = 3
    FT_OTHER_METADATA = 4
    FT_SUBMISSION_DOC = 5

    # Output transfer types
    TRANSFER_TYPE_AM_STD = 1

    def __init__(self, path, parent=None):
        self.path = Path(path)
        self.name = self.path.name
        self.parent = parent

        self.errors = 0
        self.successes = 0
        self.timer = {"start": None, "end": None}

        self.files = {
            self.FT_PRESERVATION_OBJECT: [],
            self.FT_CHECKSUM: [],
            self.FT_DESC_METADATA: [],
            self.FT_OTHER_METADATA: [],
            self.FT_SUBMISSION_DOC: [],
        }

    def has_errors(self):
        return self.errors > 0

    def copy_files(self, files, dest_path):
        for file in files:
            shutil.copy(file, dest_path / file.name)

    def get_files_by_type(self, file_type):
        if file_type in self.files.keys():
            return self.files[file_type]

    def add_file(self, file_type, file):
        if file_type not in self.files.keys():
            raise KeyError('Invalid file_type "{}"'.format(file_type))

        # Prevent duplicate entries
        if file not in self.files[file_type]:
            self.files[file_type].append(file)

    def get_submission_docs(self):
        # Cache file paths to avoid multiple scans of the filesystem
        if not self.get_files_by_type(self.FT_SUBMISSION_DOC):
            for filename in self.SUBMISSION_DOC_FILENAMES:
                file = self.path / filename

                if file.exists():
                    self.add_file(self.FT_SUBMISSION_DOC, file)
                else:
                    self.errors += 1

                    raise FileNotFoundError('Required "{}" file not found')

        return self.get_files_by_type(self.FT_SUBMISSION_DOC)

    def create_subdirs(self, path, subdirs):
        """Recursively create nested subdirectories in path, if the subdir
        doesn't exist already, then return the full path to final subdir"""

        for subdir in subdirs.split("/"):
            path = path / subdir

            if not path.exists():
                path.mkdir()

        return path


class VanDocsPackageConverter(PackageConverter):
    SUBMISSION_DOC_FILENAMES = [
        "Location.xml",
    ]

    def __init__(self, path, parent=None):
        PackageConverter.__init__(self, path, parent)

        # VanDocs containers are sub-directories that group together a number of
        # related preservation objects and their metadata
        self.containers = []

    def get_transfer_number(self):
        # e.g "VanDocs-123456" -> "123456"
        return self.name.replace("VanDocs-", "")

    def get_containers(self):
        containers = []

        for item in self.path.iterdir():
            if item.is_dir():
                containers.append(item)

        return containers

    def get_summary_msg(self):
        if not self.has_errors():
            msg = (
                "SUCCESS: Converted {} VanDocs containers to Archivematica"
                + " standard transfers [{:.3}s]"
            )

            return msg.format(
                len(self.get_containers()),
                (self.timer["end"] - self.timer["start"]),
            )
        else:
            msg = "ERROR: Encountered {} errors converting {} containers [{:.3}s]"

            return msg.format(
                self.errors,
                len(self.get_containers()),
                (self.timer["end"] - self.timer["start"]),
            )

    def convert(self, dest_path):
        self.timer["start"] = time.time()

        for container in self.get_containers():
            converter = VanDocsContainerConverter(container, self)
            converter.write_am_std_transfer(self.create_subdirs(Path(), dest_path))
            self.errors += converter.errors

        self.timer["end"] = time.time()

        level = logging.ERROR if self.has_errors() else logging.INFO
        logging.log(level, self.get_summary_msg())


class VanDocsContainerConverter(PackageConverter):
    SUBMISSION_DOC_FILENAMES = ["ContainerMetadata.xml"]

    def get_log_prefix(self):
        return 'Container "{}" '.format(self.name)

    def get_am_transfer_name(self):
        return "{}_{}".format(self.parent.get_transfer_number(), self.name)

    def create_am_transfer_dir(self, dest_path):
        """Create an Archivematica transfer directory using the name format
        [transfer_number]_[container_name]"""

        am_transfer_name = self.get_am_transfer_name()
        am_transfer_dir = dest_path / am_transfer_name

        if am_transfer_dir.exists():
            msg = (
                'Transfer "{}" already exists. Please move or delete the existing',
                "transfer directory to create a new transfer.",
            )

            self.errors += 1
            logging.error("\n".join(msg).format(am_transfer_name))

            return

        am_transfer_dir.mkdir()

        logging.info(
            self.get_log_prefix()
            + 'Created Archivematica standard transfer "{}"'.format(am_transfer_name)
        )

        return am_transfer_dir

    def copy_submission_docs(self, am_transfer_dir):
        """Copy relevant VanDocs processing files to submissionDocumentation
        directory"""

        # Create metadata/submissionDocumentation dir
        subdoc_dir = self.create_subdirs(
            am_transfer_dir, "metadata/submissionDocumentation"
        )

        docs = self.parent.get_submission_docs() + self.get_submission_docs()

        logging.info(
            self.get_log_prefix()
            + 'Copying {} submission documents to "{}"'.format(len(docs), subdoc_dir)
        )

        # Copy transfer & container submission docs to am_transfer_dir
        self.copy_files(docs, subdoc_dir)

    def get_preservation_objects(self):
        if not self.get_files_by_type(self.FT_PRESERVATION_OBJECT):
            for item in self.path.iterdir():
                # Skip submission docs and metadata files
                if (
                    item.name not in self.SUBMISSION_DOC_FILENAMES
                    and not item.name.endswith("_Metadata.xml")
                ):
                    self.add_file(self.FT_PRESERVATION_OBJECT, item)

        return self.get_files_by_type(self.FT_PRESERVATION_OBJECT)

    def get_md_filename(self, file):
        """Get corresponding metadata file name by stripping file's extension
        (if any) and adding the \"_Metadata.xml\" prefix"""

        parts = file.name.split(".")

        return parts[0] + "_Metadata.xml"

    def get_md5_hashes(self):
        """Return a list of tuples where each tuple is an md5 hash of the
        corresponding file contents"""
        hashes = []

        for file in self.get_preservation_objects():
            md_filename = self.get_md_filename(file)
            parser = VanDocsDocumentXmlParser(self.path / md_filename)
            hash = (parser.get_md5_hash(), "/".join((self.name, file.name)))
            hashes.append(hash)

        return hashes

    def write_am_checksum_file(self, am_transfer_dir):
        """Write an Archivematica checksum.md5 file to the metadata/ directory"""

        md_dir = self.create_subdirs(am_transfer_dir, "metadata")
        checksum_file = md_dir / "checksum.md5"

        logging.info(
            self.get_log_prefix() + 'Writing checksum file "{}"'.format(checksum_file)
        )

        with checksum_file.open("w") as fh:
            for item in self.get_md5_hashes():
                fh.write("{}  {}\n".format(*item))

    def get_container_metadata(self):
        parser = VanDocsContainerXmlParser(self.path / "ContainerMetadata.xml")

        return parser.get_dcmi_data()

    def get_document_metadata(self, file):
        md_filename = self.get_md_filename(file)
        parser = VanDocsDocumentXmlParser(self.path / md_filename)

        return parser.get_dcmi_data()

    def create_metadata_csv_file(self, am_transfer_dir):
        """Create an Archivematica metadata.csv file for descriptive metadata"""

        md_dir = self.create_subdirs(am_transfer_dir, "metadata")
        metadata_file = md_dir / "metadata.csv"

        return metadata_file

    def write_am_metadata(self, am_transfer_dir):
        """Write descriptive metadata for preservation objects to metadata.csv file"""

        csv_writer = AmMetadataCsvWriter(self.parent.get_transfer_number())
        csv_writer.add_dcmi_row_data(self.name, self.get_container_metadata())

        for file in self.get_preservation_objects():
            csv_writer.add_dcmi_row_data(
                "{}/{}".format(self.name, file.name), self.get_document_metadata(file)
            )

        csv_file = self.create_metadata_csv_file(am_transfer_dir)

        logging.info(
            self.get_log_prefix() + 'Writing metadata CSV file "{}"'.format(csv_file)
        )

        csv_writer.write_csv_file(csv_file)

    def copy_preservation_objects(self, am_transfer_dir):
        container_dir = self.create_subdirs(am_transfer_dir, self.name)
        objects = self.get_preservation_objects()

        logging.info(
            self.get_log_prefix()
            + 'Copying {} preservation objects to "{}"'.format(
                len(objects), container_dir
            )
        )

        self.copy_files(objects, container_dir)

    def write_am_std_transfer(self, dest_path):
        am_transfer_dir = self.create_am_transfer_dir(dest_path)

        # Skip this container if the target am_transfer_dir already exists
        if not am_transfer_dir:
            return

        self.copy_submission_docs(am_transfer_dir)
        self.write_am_checksum_file(am_transfer_dir)
        self.write_am_metadata(am_transfer_dir)
        self.copy_preservation_objects(am_transfer_dir)
