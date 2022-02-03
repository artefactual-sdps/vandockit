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

import csv
import pytest

# Local modules
from vandocs_converter.package_converter import (
    PackageConverter,
    VanDocsPackageConverter,
    VanDocsContainerConverter,
)

TRANSFER_ID = "123456"
TRANSFER_NAME = "VanDocs-" + TRANSFER_ID

PKG_MD_FILES = VanDocsPackageConverter.SUBMISSION_DOC_FILENAMES
CONTAINERS = ["01-2500-10_0000007"]
CONTAINER_MD_FILES = ["ContainerMetadata.xml"]

DOCUMENTS = [
    "DOC_2009_040165.PDF",
    "DOC_2009_016092.PDF",
]
DOC_MD_FILES = [
    "DOC_2009_040165_Metadata.xml",
    "DOC_2009_016092_Metadata.xml",
]

CONTAINER_FILES = CONTAINER_MD_FILES + DOCUMENTS + DOC_MD_FILES

CONTAINER_MD_XML = """
<ContainerMetadata>
    <Container>
        <Creator>Smith Family</Creator>
        <DateCreated>2022-02-15T12:00:00-08:00</DateCreated>
        <Department>Testing Department</Department>
        <RecordNumber>01-2500-10/0000007</RecordNumber>
        <RecordType>Series</RecordType>
        <TitleFreeTextPart>So many photos!</TitleFreeTextPart>
        <TitleStructuredPart>Family photos 2021</TitleStructuredPart>
    </Container>
</ContainerMetadata>
"""

MD5_HASHES = ["4d118b7297d8469c2833046fa48471cf", "7c0086cd150d36b1dac61c4a7f86d4eb"]
DOCUMENT_MD_XML = """
<ContainerDocumentMetadata>
    <Document>
        <Creator>Smith, Jane</Creator>
        <DateCreated>2021-11-15T08:12:34-08:00</DateCreated>
        <Home>01-2500-10/0000007</Home>
        <InternetMediaType>jpeg</InternetMediaType>
        <RecordNumber>DOC/2009/040165</RecordNumber>
        <RecordType>Image</RecordType>
        <Title>Baby Smith, one day old</Title>
        <MD5>{}</MD5>
    </Document>
</ContainerDocumentMetadata>
"""


@pytest.fixture
def test_package_no_ctr(tmp_path):
    package = tmp_path / TRANSFER_NAME
    package.mkdir()

    for name in PKG_MD_FILES:
        file = package / name
        file.touch()

    return package


@pytest.fixture
def test_container(tmp_path):
    container = tmp_path / CONTAINERS[0]
    container.mkdir()

    j = 0
    for i in range(len(CONTAINER_FILES)):
        file = container / CONTAINER_FILES[i]

        if "ContainerMetadata.xml" == file.name:
            file.write_text(CONTAINER_MD_XML)
        elif file.name in DOC_MD_FILES:
            # Write MD hash data to document metadata files
            file.write_text(DOCUMENT_MD_XML.format(MD5_HASHES[j]))
            j += 1
        else:
            file.touch()

    return container


@pytest.fixture
def test_package(test_package_no_ctr):
    package = test_package_no_ctr

    container = package / CONTAINERS[0]
    container.mkdir()

    for filename in CONTAINER_FILES:
        file = container / filename

        if "DOC_2009_040165_Metadata.xml" == filename:
            file.write_text(DOCUMENT_MD_XML)
        else:
            file.touch()

    return package


@pytest.fixture
def dest_dir(tmp_path):
    dest_dir = tmp_path / "dest"
    dest_dir.mkdir()

    return dest_dir


@pytest.fixture
def vd_package_converter(test_package):
    return VanDocsPackageConverter(test_package)


@pytest.fixture
def vd_container_converter(test_container, vd_package_converter):
    return VanDocsContainerConverter(test_container, vd_package_converter)


class TestPackageConverter:
    def test_has_errors_true(self, tmp_path):
        converter = PackageConverter(tmp_path)
        converter.errors = 1

        assert converter.has_errors()

    def test_has_errors_false(self, tmp_path):
        converter = PackageConverter(tmp_path)

        assert not converter.has_errors()

    def test_copy_files(self, tmp_path):
        filenames = ["test_file_01.txt", "test_file_02"]
        source_files = []

        source_dir = tmp_path / "test_source"
        source_dir.mkdir()
        dest_dir = tmp_path / "test_dest"
        dest_dir.mkdir()

        for filename in filenames:
            source_file = source_dir / filename
            source_file.touch()
            source_files.append(source_file)

        converter = PackageConverter(source_dir)
        converter.copy_files(source_files, dest_dir)

        assert [dest_dir / name for name in filenames] == [
            path for path in dest_dir.iterdir()
        ]

    def test_add_file(self, tmp_path):
        file = tmp_path / "DummyMetadata.xml"
        converter = PackageConverter(tmp_path)

        converter.add_file(PackageConverter.FT_SUBMISSION_DOC, file)

        assert [file] == converter.get_files_by_type(PackageConverter.FT_SUBMISSION_DOC)

    def test_add_file_no_duplicates(self, tmp_path):
        file = tmp_path / "DummyMetadata.xml"
        converter = PackageConverter(tmp_path)

        # Try adding file twice
        converter.add_file(PackageConverter.FT_SUBMISSION_DOC, file)
        converter.add_file(PackageConverter.FT_SUBMISSION_DOC, file)

        # Should only have one instance of file
        assert [file] == converter.get_files_by_type(PackageConverter.FT_SUBMISSION_DOC)

    def test_add_file_invalid_file_type(self, tmp_path):
        file = tmp_path / "DummyMetadata.xml"
        converter = PackageConverter(tmp_path)

        with pytest.raises(KeyError):
            converter.add_file("spam", file)


class TestVanDocsPackageConverter:
    def test_get_submission_docs(self, vd_package_converter):
        # Test symmetric set diff to avoid errors from mismatched list element
        # order.  Use list comprehension to convert libpath objects to strings.
        assert not set(PKG_MD_FILES) ^ set(
            i.name for i in vd_package_converter.get_submission_docs()
        )

    def test_get_submission_docs_file_not_found(self, vd_package_converter):
        vd_package_converter.SUBMISSION_DOC_FILENAMES.append("spam.xml")

        with pytest.raises(FileNotFoundError):
            assert vd_package_converter.get_submission_docs()

        # Because Python assigns objects by reference, we have to remove the
        # dummy file from the file list to prevent errors in subsequent tests
        vd_package_converter.SUBMISSION_DOC_FILENAMES.pop()

    def test_create_dest_dir(self, tmp_path, vd_package_converter):
        dest_dir = tmp_path / "foo"
        vd_package_converter.create_dest_dir(dest_dir)

        assert dest_dir.exists() and dest_dir.is_dir()

    def test_get_transfer_number(self, vd_package_converter):
        assert TRANSFER_ID == vd_package_converter.get_transfer_number()

    def test_get_containers(self, vd_package_converter):
        assert not set(CONTAINERS) ^ set(
            i.name for i in vd_package_converter.get_containers()
        )

    def test_get_summary_msg(self, vd_package_converter):
        vd_package_converter.timer = {"start": 1000.0, "end": 1001.11}
        check_msg = (
            "SUCCESS: Converted 1 VanDocs containers to Archivematica"
            + " standard transfers [1.11s]"
        )

        assert check_msg == vd_package_converter.get_summary_msg()

    def test_get_summary_msg_error(self, vd_package_converter):
        vd_package_converter.errors = 2
        vd_package_converter.timer = {"start": 1000.0, "end": 1001.11}
        check_msg = "ERROR: Encountered 2 errors converting 1 containers [1.11s]"

        assert check_msg == vd_package_converter.get_summary_msg()

    # def test_convert()


class TestVanDocsContainerConverter:
    def test_get_am_transfer_name(self, vd_container_converter):
        assert (
            TRANSFER_ID + "_" + CONTAINERS[0]
            == vd_container_converter.get_am_transfer_name()
        )

    def test_create_am_transfer_dir(self, dest_dir, vd_container_converter):
        vd_container_converter.create_am_transfer_dir(dest_dir)
        am_transfer_dirname = TRANSFER_ID + "_" + CONTAINERS[0]
        check_path = dest_dir / am_transfer_dirname

        assert check_path.exists() and check_path.is_dir()

    def test_create_am_transfer_dir_already_exists(
        self, dest_dir, vd_container_converter
    ):
        am_transfer_dirname = TRANSFER_ID + "_" + CONTAINERS[0]
        check_path = dest_dir / am_transfer_dirname
        check_path.mkdir()

        assert None == vd_container_converter.create_am_transfer_dir(dest_dir)

    def test_create_metadata_dir(self, dest_dir, vd_container_converter):
        vd_container_converter.create_metadata_dir(dest_dir)
        md_dir = dest_dir / "metadata"

        assert md_dir.exists() and md_dir.is_dir()

    def test_copy_submission_docs(self, dest_dir, vd_container_converter):
        subdocs_dir = dest_dir / "metadata" / "submissionDocumentation"
        vd_container_converter.copy_submission_docs(dest_dir)

        assert PKG_MD_FILES + CONTAINER_MD_FILES == [
            x.name for x in subdocs_dir.iterdir()
        ]

    def test_get_preservation_objects(self, vd_container_converter):
        assert not set(DOCUMENTS) ^ set(
            i.name for i in vd_container_converter.get_preservation_objects()
        )

    def test_get_md_filename(self, tmp_path, vd_container_converter):
        assert "test_file_Metadata.xml" == vd_container_converter.get_md_filename(
            tmp_path / "test_file.pdf"
        )

    def test_get_md5_hashes(self, vd_container_converter):
        assert [
            (
                "7c0086cd150d36b1dac61c4a7f86d4eb",
                CONTAINERS[0] + "/DOC_2009_016092.PDF",
            ),
            (
                "4d118b7297d8469c2833046fa48471cf",
                CONTAINERS[0] + "/DOC_2009_040165.PDF",
            ),
        ] == vd_container_converter.get_md5_hashes()

    def test_not_get_md5_hashes(self, tmp_path, test_container, vd_package_converter):
        converter = VanDocsContainerConverter(test_container, vd_package_converter)

        md_file = tmp_path / CONTAINERS[0] / "DOC_2009_040165_Metadata.xml"
        md_file.write_text(
            "<ContainerDocumentMetadata><Document></Document></ContainerDocumentMetadata>"
        )

        with pytest.raises(RuntimeError):
            converter.get_md5_hashes()

    def test_write_am_checksum_file(self, dest_dir, vd_container_converter):
        vd_container_converter.write_am_checksum_file(dest_dir)
        checksum_file = dest_dir / "metadata" / "checksum.md5"
        hashes = [
            "7c0086cd150d36b1dac61c4a7f86d4eb  {}/DOC_2009_016092.PDF\n",
            "4d118b7297d8469c2833046fa48471cf  {}/DOC_2009_040165.PDF\n",
        ]

        hash_text = "".join(hashes)
        hash_text = hash_text.format(CONTAINERS[0], CONTAINERS[0])

        assert hash_text == checksum_file.read_text()

    def test_get_container_metadata(self, vd_container_converter):
        assert {
            "creator": "Smith Family",
            "date": "2022-02-15T12:00:00-08:00",
            "description": "So many photos!",
            "identifier": "01-2500-10/0000007",
            "provenance": "Testing Department",
            "title": "Family photos 2021",
            "type": "Series",
        } == vd_container_converter.get_container_metadata()

    def test_get_document_metadata(self, tmp_path, vd_container_converter):
        assert {
            "creator": "Smith, Jane",
            "date": "2021-11-15T08:12:34-08:00",
            "format": "jpeg",
            "identifier": "DOC/2009/040165",
            "source": "01-2500-10/0000007",
            "title": "Baby Smith, one day old",
            "type": "Image",
        } == vd_container_converter.get_document_metadata(
            tmp_path / CONTAINERS[0] / "DOC_2009_040165.PDF"
        )

    def test_create_metadata_csv_file(self, dest_dir, vd_container_converter):
        check_file = dest_dir / "metadata" / "metadata.csv"

        assert check_file == vd_container_converter.create_metadata_csv_file(dest_dir)

    def test_write_am_metadata(self, dest_dir, vd_container_converter):
        check_csv_contents = [
            [
                "filename",
                "dc.title",
                "dc.creator",
                "dc.subject",
                "dc.description",
                "dc.publisher",
                "dc.contributor",
                "dc.date",
                "dc.type",
                "dc.format",
                "dc.identifier",
                "dc.source",
                "dc.language",
                "dc.relation",
                "dc.coverage",
                "dc.rights",
                "dc.provenance",
                "vandocs_transfer_number",
            ],
            [
                "objects/" + CONTAINERS[0],
                "Family photos 2021",
                "Smith Family",
                "",
                "So many photos!",
                "",
                "",
                "2022-02-15T12:00:00-08:00",
                "Series",
                "",
                "01-2500-10/0000007",
                "",
                "",
                "",
                "",
                "",
                "Testing Department",
                TRANSFER_ID,
            ],
            [
                "objects/" + CONTAINERS[0] + "/DOC_2009_016092.PDF",
                "Baby Smith, one day old",
                "Smith, Jane",
                "",
                "",
                "",
                "",
                "2021-11-15T08:12:34-08:00",
                "Image",
                "jpeg",
                "DOC/2009/040165",
                "01-2500-10/0000007",
                "",
                "",
                "",
                "",
                "",
                TRANSFER_ID,
            ],
        ]

        vd_container_converter.write_am_metadata(dest_dir)
        csv_file = dest_dir / "metadata" / "metadata.csv"

        with csv_file.open("r") as fh:
            csv_contents = [i for i in csv.reader(fh)]

        # Don't check the last row of csv_contents because it's a near duplicate
        # of the previous row
        assert check_csv_contents == csv_contents[:3]

    def test_make_container_dir(self, dest_dir, vd_container_converter):
        vd_container_converter.make_container_dir(dest_dir)
        check_path = dest_dir / CONTAINERS[0]

        assert check_path.exists() and check_path.is_dir()

    def test_copy_preservation_objects(self, dest_dir, vd_container_converter):
        vd_container_converter.copy_preservation_objects(dest_dir)

        object_dir = dest_dir / vd_container_converter.name

        assert not set(DOCUMENTS) ^ set(x.name for x in object_dir.iterdir())

    # def test_write_am_std_transfer(self, dest_dir, vd_container_converter):
