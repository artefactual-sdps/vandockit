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
import shutil
import time
import xml.etree.ElementTree as ET
from pathlib import Path

# Local modules
from vandockit.metadata_csv_writer import AMMetadataCsvWriter
from vandockit.metadata_xml_parser import ContainerXmlParser
from vandockit.metadata_xml_parser import DocumentXmlParser


class BaseConverter:
    # Package file types
    FT_PRESERVATION_OBJECT = 1
    FT_CHECKSUM = 2
    FT_DESC_METADATA = 3
    FT_OTHER_METADATA = 4
    FT_SUBMISSION_DOC = 5

    # Output transfer types
    TRANSFER_TYPE_AM_STD = 1

    # Personally identifiable information tags that should be removed from
    # Location.xml
    PII_TAGS = (
        "LogsInAs",
        "IDNumber",
        "InternetEmailAddress",
        "Notes",
    )

    def __init__(self, path, parent=None):
        self.errors = self.successes = 0
        self.path = Path(path)
        self.parent = parent
        self.timer = {"start": None, "end": None}

        self.files = {
            self.FT_PRESERVATION_OBJECT: set(),
            self.FT_CHECKSUM: set(),
            self.FT_DESC_METADATA: set(),
            self.FT_OTHER_METADATA: set(),
            self.FT_SUBMISSION_DOC: set(),
        }

    @property
    def name(self):
        return self.path.name

    def has_errors(self):
        return self.errors > 0

    def get_log_prefix(self):
        return f"{self.name} "

    def copy_files(self, files, dest_path):
        for file in files:
            try:
                shutil.copy(file, dest_path / file.name)
            except OSError as err:
                logging.critical(
                    self.get_log_prefix()
                    + f"Couldn't copy '{file}' to '{dest_path}'"
                )

                # Halt script
                raise err

    def add_file(self, file_type, file):
        try:
            self.files[file_type].add(file)
        except KeyError as err:
            raise KeyError(f'Invalid file_type "{file_type}"') from err

    def get_files_by_type(self, file_type):
        try:
            return self.files[file_type]
        except KeyError:
            pass

    def get_submission_docs(self):
        # Cache file paths to avoid multiple scans of the filesystem
        if not self.get_files_by_type(self.FT_SUBMISSION_DOC):
            for filename in self.SUBMISSION_DOC_FILENAMES:
                file = self.path / filename

                if file.exists():
                    self.add_file(self.FT_SUBMISSION_DOC, file)
                else:
                    raise FileNotFoundError('Required "{}" file not found')

        return self.get_files_by_type(self.FT_SUBMISSION_DOC)

    def create_subdirs(self, path, subdirs):
        """Recursively create nested subdirectories in path, if the subdir
        doesn't exist already, then return the full path to final subdir"""

        for subdir in subdirs.split("/"):
            path = path / subdir

            if path.exists():
                continue

            try:
                path.mkdir()
            except OSError as err:
                msg = (
                    self.get_log_prefix()
                    + f"Couldn't create sub-directory {path}', please make"
                    " sure you have write permissions"
                )

                logging.critical(msg)

                # Halt script
                raise err

        return path

    def make_read_only(self, path):
        """
        Remove write permissions from the file or directory at path to prevent
        modification. If path is a directory, recursively remove write
        permissions from all of its contents.
        """

        if path.is_dir():
            for item in path.iterdir():
                self.make_read_only(item)

            path.chmod(0o555)
        else:
            path.chmod(0o444)


class PackageConverter(BaseConverter):
    SUBMISSION_DOC_FILENAMES = [
        "VanDocsDispositionContainerDocumentMetadataSchema.xsd",
        "VanDocsDispositionContainerMetadataSchema.xsd",
        "VanDocsDispositionLocationMetadataSchema.xsd",
    ]

    def __init__(self, path, parent=None):
        BaseConverter.__init__(self, path, parent)

        # VanDocs containers are sub-directories that group together a number
        # of related preservation objects and their metadata
        self.containers = []

    def get_transfer_number(self):
        # e.g "VanDocs-123456" -> "123456"
        return self.name.replace("VanDocs-", "")

    def get_containers(self):
        for item in self.path.iterdir():
            if item.is_dir():
                container = ContainerConverter(item, self)
                self.containers.append(container)

        return self.containers

    def get_am_transfers(self):
        return sorted(
            [container.get_am_transfer_name() for container in self.containers]
        )

    def get_summary_msg(self):
        elapsed = self.timer["end"] - self.timer["start"]
        if self.has_errors():
            return (
                f"ERROR: Encountered {self.errors} errors converting"
                f" {len(self.containers)} containers [{elapsed:.3}s]"
            )

        msg = (
            f"Source transfer: {self.path}\n\n"
            f"Number of SIPs created: {len(self.containers)}\n"
            f"Elapsed time: {elapsed:.3}s\n\n"
        )
        msg += "\n".join(self.get_am_transfers())

        return msg

    def convert(self, dest_path, **kwargs):
        self.timer["start"] = time.time()
        dest_path = Path(dest_path)

        for container in self.get_containers():
            container.write_am_std_transfer(dest_path, **kwargs)

            if container.has_errors():
                self.errors += container.errors

        self.timer["end"] = time.time()

        level = logging.ERROR if self.has_errors() else logging.INFO
        logging.log(level, self.get_summary_msg())


class ContainerConverter(BaseConverter):
    SUBMISSION_DOC_FILENAMES = ["ContainerMetadata.xml"]

    def get_log_prefix(self):
        return f'Container "{self.name}" '

    def get_am_transfer_name(self):
        return f"{self.parent.get_transfer_number()}_{self.name}"

    def transfer_exists(self, dest_path):
        """Check if a transfer directory or zip file with the same name already
        exists in the destination path."""

        transfer_name = self.get_am_transfer_name()

        if (dest_path / transfer_name).exists() or (
            dest_path / f"{transfer_name}.zip"
        ).exists():
            return True

        return False

    def create_am_transfer_dir(self, dest_path):
        """Create an Archivematica transfer directory using the name format
        [transfer_number]_[container_name]"""

        am_transfer_name = self.get_am_transfer_name()
        am_transfer_dir = dest_path / am_transfer_name

        self.create_subdirs(dest_path, am_transfer_name)

        logging.info(
            self.get_log_prefix()
            + f'Created Archivematica standard transfer "{am_transfer_name}"'
        )

        return am_transfer_dir

    def copy_submission_docs(self, am_transfer_dir):
        """Copy relevant VanDocs processing files to submissionDocumentation
        directory"""

        # Create metadata/submissionDocumentation dir
        subdoc_dir = self.create_subdirs(
            am_transfer_dir, "metadata/submissionDocumentation"
        )

        # docs is the union of the parent and self submission doc sets
        docs = self.parent.get_submission_docs() | self.get_submission_docs()

        logging.info(
            self.get_log_prefix()
            + f'Copying {len(docs)} submission documents to "{subdoc_dir}"'
        )

        # Copy transfer & container submission docs to am_transfer_dir
        self.copy_files(docs, subdoc_dir)

    def write_location_file(self, am_transfer_dir):
        """Remove personally identifiable information from Location.xml and
        write the sanitized file to the submissionDocumentation directory."""

        # Create metadata/submissionDocumentation dir
        subdoc_dir = self.create_subdirs(
            am_transfer_dir, "metadata/submissionDocumentation"
        )

        logging.info(
            self.get_log_prefix()
            + f'Writing Location.xml file to "{subdoc_dir}"'
        )

        tree = ET.parse(self.parent.path / "Location.xml")
        root = tree.getroot()

        # Remove personally identifiable data
        for el in root.findall("Location"):
            for tag in self.PII_TAGS:
                for child in el.findall(tag):
                    el.remove(child)

        tree.write(
            subdoc_dir / "Location.xml", encoding="utf-8", xml_declaration=True
        )

    def get_preservation_objects(self):
        if not self.get_files_by_type(self.FT_PRESERVATION_OBJECT):
            for item in self.path.iterdir():
                # Skip submission docs and metadata files
                if (
                    item.name not in self.SUBMISSION_DOC_FILENAMES
                    and item.name != "Location.xml"
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
            parser = DocumentXmlParser(self.path / md_filename)
            hash = (parser.get_md5_hash(), "/".join((self.name, file.name)))
            hashes.append(hash)

        return hashes

    def write_am_checksum_file(self, am_transfer_dir):
        """Write an Archivematica checksum.md5 file to the metadata/
        directory"""

        md_dir = self.create_subdirs(am_transfer_dir, "metadata")
        checksum_file = md_dir / "checksum.md5"

        logging.info(
            f'{self.get_log_prefix()} Writing checksum file "{checksum_file}"'
        )

        with checksum_file.open("w") as fh:
            for item in self.get_md5_hashes():
                fh.write("{}  {}\n".format(*item))

    def get_container_metadata(self):
        parser = ContainerXmlParser(self.path / "ContainerMetadata.xml")

        return parser.get_dcmi_data()

    def get_document_metadata(self, file):
        md_filename = self.get_md_filename(file)
        parser = DocumentXmlParser(self.path / md_filename)

        return parser.get_dcmi_data()

    def get_metadata_csv_path(self, am_transfer_dir):
        """Get an Archivematica metadata.csv file for descriptive metadata"""

        md_dir = self.create_subdirs(am_transfer_dir, "metadata")
        metadata_file = md_dir / "metadata.csv"

        return metadata_file

    def write_am_metadata(self, am_transfer_dir):
        """Write descriptive metadata for preservation objects to metadata.csv
        file"""

        csv_writer = AMMetadataCsvWriter(self.parent.get_transfer_number())
        csv_writer.add_dcmi_row_data(self.name, self.get_container_metadata())

        for file in self.get_preservation_objects():
            csv_writer.add_dcmi_row_data(
                f"{self.name}/{file.name}",
                self.get_document_metadata(file),
            )

        csv_path = self.get_metadata_csv_path(am_transfer_dir)

        logging.info(
            self.get_log_prefix() + f'Writing metadata CSV file "{csv_path}"'
        )

        csv_writer.write_csv_file(csv_path)

    def copy_preservation_objects(self, am_transfer_dir):
        container_dir = self.create_subdirs(am_transfer_dir, self.name)
        objects = self.get_preservation_objects()

        logging.info(
            self.get_log_prefix()
            + f"Copying {len(objects)} preservation objects to"
            f' "{container_dir}"'
        )

        self.copy_files(objects, container_dir)

    def get_desc_md_files(self):
        """Get a list of descriptive metadata file names in the source
        container"""

        if not self.get_files_by_type(self.FT_DESC_METADATA):
            self.files[self.FT_DESC_METADATA] = list(
                self.path.glob("*_Metadata.xml")
            )

        return self.get_files_by_type(self.FT_DESC_METADATA)

    def copy_desc_md_files(self, am_transfer_dir):
        """Copy the descriptive metadata files from source container to the
        target am_transfer_dir"""

        dmd_files = self.get_desc_md_files()
        subdoc_dir = self.create_subdirs(
            am_transfer_dir, "metadata/submissionDocumentation"
        )

        logging.info(
            self.get_log_prefix()
            + f"Copying {len(dmd_files)} document metadata files to"
            f' "{subdoc_dir}"'
        )

        self.copy_files(dmd_files, subdoc_dir)

    def zip_dir(self, path):
        """
        Zip the directory at path and return the zip file's path. The original
        directory is deleted after the zip file is created.
        """

        try:
            zip_path = shutil.make_archive(
                path,
                "zip",
                path.parent,
                path.name,
            )
        except OSError:
            logging.critical(
                self.get_log_prefix()
                + f"Couldn't create zip file '{path.name}.zip' from dir"
                f" '{path}'"
            )

            # Halt script
            raise

        # Delete the unzipped transfer directory after creating the zip file
        try:
            shutil.rmtree(path)
        except OSError:
            logging.critical(
                self.get_log_prefix() + f"Couldn't delete '{path}'"
            )

            # Halt script
            raise

        return Path(zip_path)

    def write_am_std_transfer(self, dest_path, **kwargs):
        # Skip this container if the transfer already exists
        if self.transfer_exists(dest_path):
            self.errors += 1
            logging.error(
                f'Transfer "{self.get_am_transfer_name()}" already exists.'
                + " Please move or delete the existing transfer to create a"
                + " new transfer."
            )

            return

        transfer_path = self.create_am_transfer_dir(dest_path)

        self.copy_submission_docs(transfer_path)
        self.write_location_file(transfer_path)
        self.write_am_checksum_file(transfer_path)

        # 2022-03-10: At CVA's request disable the creation of metadata.csv
        # because the current VanDocs data doesn't map accurately to Dublin
        # Core
        #
        # self.write_am_metadata(transfer_path)

        self.copy_preservation_objects(transfer_path)
        self.copy_desc_md_files(transfer_path)

        # Zip the transfer directory if the --zip option was specified.
        if kwargs.get("zip", False):
            transfer_path = self.zip_dir(transfer_path)

        self.make_read_only(transfer_path)

        return transfer_path
