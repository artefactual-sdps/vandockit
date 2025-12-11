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

import csv

import pytest

# Local modules
import vandockit.converters as vd_converters


@pytest.fixture
def dest_dir(tmp_path):
    dest_dir = tmp_path / "dest"
    dest_dir.mkdir()

    return dest_dir


@pytest.fixture
def vd_base_converter(tmp_path):
    return vd_converters.BaseConverter(tmp_path)


@pytest.fixture
def vd_package_converter(test_package):
    return vd_converters.PackageConverter(test_package)


@pytest.fixture
def vd_container_converter(
    test_package,
    test_container_data,
    vd_package_converter,
):
    return vd_converters.ContainerConverter(
        test_package / test_container_data["name"], vd_package_converter
    )


class TestBaseConverter:
    def test_has_errors_true(self, vd_base_converter):
        vd_base_converter.errors = 1

        assert vd_base_converter.has_errors()

    def test_has_errors_false(self, vd_base_converter):
        assert not vd_base_converter.has_errors()

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

        converter = vd_converters.BaseConverter(source_dir)
        converter.copy_files(source_files, dest_dir)

        assert {dest_dir / name for name in filenames} == set(
            dest_dir.iterdir()
        )

    def test_copy_files_os_error(self, dest_dir, tmp_path):
        dest_dir.chmod(0o555)  # make dest_dir unwritable
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        file = source_dir / "test_file.txt"
        file.touch()

        converter = vd_converters.BaseConverter(source_dir)

        with pytest.raises(OSError):
            converter.copy_files([file], dest_dir)

    def test_add_file(self, tmp_path, vd_base_converter):
        file = tmp_path / "DummyMetadata.xml"
        vd_base_converter.add_file(vd_base_converter.FT_SUBMISSION_DOC, file)

        assert {file} == vd_base_converter.get_files_by_type(
            vd_base_converter.FT_SUBMISSION_DOC
        )

    def test_add_file_no_duplicates(self, tmp_path, vd_base_converter):
        file = tmp_path / "DummyMetadata.xml"

        # Try adding file twice
        vd_base_converter.add_file(vd_base_converter.FT_SUBMISSION_DOC, file)
        vd_base_converter.add_file(vd_base_converter.FT_SUBMISSION_DOC, file)

        # Should only have one instance of file
        assert {file} == vd_base_converter.get_files_by_type(
            vd_base_converter.FT_SUBMISSION_DOC
        )

    def test_add_file_invalid_file_type(self, tmp_path, vd_base_converter):
        with pytest.raises(KeyError):
            vd_base_converter.add_file("spam", tmp_path / "DummyMetadata.xml")

    def test_get_files_by_type(self, tmp_path, vd_base_converter):
        test_file = tmp_path / "foo.txt"
        vd_base_converter.add_file(
            vd_base_converter.FT_PRESERVATION_OBJECT,
            test_file,
        )

        assert {test_file} == vd_base_converter.get_files_by_type(
            vd_base_converter.FT_PRESERVATION_OBJECT
        )

    def test_get_files_by_type_invalid_type(self, vd_base_converter):
        assert vd_base_converter.get_files_by_type("spam") is None

    def test_create_subdirs(self, dest_dir, vd_base_converter):
        vd_base_converter.create_subdirs(dest_dir, "spam")
        test_dir = dest_dir / "spam"

        assert test_dir.exists() and test_dir.is_dir()

    def test_create_two_subdirs(self, dest_dir, vd_base_converter):
        vd_base_converter.create_subdirs(dest_dir, "spam/eggs")
        dir1 = dest_dir / "spam"
        dir2 = dir1 / "eggs"

        assert dir1.exists() and dir1.is_dir()
        assert dir2.exists() and dir2.is_dir()

    def test_create_subdirs_existing_dir(self, dest_dir, vd_base_converter):
        sub_dir = dest_dir / "spam"
        sub_dir.mkdir()

        test_dir = vd_base_converter.create_subdirs(dest_dir, "spam")

        assert sub_dir == test_dir

    def test_create_subdirs_os_error(self, dest_dir, vd_base_converter):
        dest_dir.chmod(0o555)  # make dest_dir unwritable

        with pytest.raises(OSError):
            vd_base_converter.create_subdirs(dest_dir, "spam")

    def test_make_read_only(self, dest_dir, vd_base_converter):
        test_dir = dest_dir / "a_dir"
        test_dir.mkdir()
        test_subdir = test_dir / "a_subdir"
        test_subdir.mkdir()
        test_file = test_dir / "a_file.txt"
        test_file.touch()

        # Remove write permissions for directory and files
        vd_base_converter.make_read_only(test_dir)

        # Can't add a new file
        new_file = test_dir / "spam.txt"
        with pytest.raises(PermissionError):
            new_file.touch()

        # Can't write to an existing file
        with pytest.raises(PermissionError):
            test_file.write_text("foo")


class TestPackageConverter:
    def test_get_submission_docs(self, vd_package_converter):
        # compare sets to avoid false negatives due to ordering
        a = set(vd_package_converter.SUBMISSION_DOC_FILENAMES)
        b = {i.name for i in vd_package_converter.get_submission_docs()}
        assert a == b

    def test_get_submission_docs_file_not_found(self, vd_package_converter):
        vd_package_converter.SUBMISSION_DOC_FILENAMES.append("spam.xml")

        with pytest.raises(FileNotFoundError):
            vd_package_converter.get_submission_docs()

        # Because Python assigns objects by reference, we have to remove the
        # dummy file from the file list to prevent errors in subsequent tests
        vd_package_converter.SUBMISSION_DOC_FILENAMES.pop()

    def test_get_transfer_number(
        self,
        vd_package_converter,
        test_container_data,
    ):
        assert (
            test_container_data["transfer_number"]
            == vd_package_converter.get_transfer_number()
        )

    def test_get_containers(self, vd_package_converter):
        assert {"01-2500-10_0000007"} == {
            i.name for i in vd_package_converter.get_containers()
        }

    def test_get_am_transfers(
        self,
        vd_package_converter,
    ):
        vd_package_converter.containers = [
            vd_converters.ContainerConverter(
                vd_package_converter.path / "test-001", vd_package_converter
            ),
            vd_converters.ContainerConverter(
                vd_package_converter.path / "test-002", vd_package_converter
            ),
        ]
        want = [
            "123456_test-001",
            "123456_test-002",
        ]

        assert want == vd_package_converter.get_am_transfers()

    def test_get_summary_msg(self, vd_package_converter):
        vd_package_converter.containers = [
            vd_converters.ContainerConverter(
                vd_package_converter.path / "test-001", vd_package_converter
            ),
            vd_converters.ContainerConverter(
                vd_package_converter.path / "test-002", vd_package_converter
            ),
        ]
        vd_package_converter.timer = {"start": 1000.0, "end": 1001.11}
        check_msg = (
            f"Source transfer: {vd_package_converter.path}\n\n"
            "Number of SIPs created: 2\n"
            "Elapsed time: 1.11s\n\n"
            "123456_test-001\n"
            "123456_test-002"
        )

        assert check_msg == vd_package_converter.get_summary_msg()

    def test_get_summary_msg_error(self, vd_package_converter):
        vd_package_converter.get_containers()
        vd_package_converter.errors = 2
        vd_package_converter.timer = {"start": 1000.0, "end": 1001.11}

        assert (
            "ERROR: Encountered 2 errors converting 1 containers [1.11s]"
            == vd_package_converter.get_summary_msg()
        )

    def test_convert(self, vd_package_converter, dest_dir):
        vd_package_converter.convert(str(dest_dir))

        assert len(vd_package_converter.containers) == 1

        for transfer in vd_package_converter.get_am_transfers():
            transfer_path = dest_dir / transfer
            assert transfer_path.exists() and transfer_path.is_dir()


class TestContainerConverter:
    def test_get_am_transfer_name(
        self,
        vd_container_converter,
        test_container_data,
    ):
        check_name = "{}_{}".format(
            test_container_data["transfer_number"], test_container_data["name"]
        )

        assert check_name == vd_container_converter.get_am_transfer_name()

    def test_create_am_transfer_dir(
        self, dest_dir, vd_container_converter, test_container_data
    ):
        vd_container_converter.create_am_transfer_dir(dest_dir)
        check_path = dest_dir / "{}_{}".format(
            test_container_data["transfer_number"], test_container_data["name"]
        )

        assert check_path.exists() and check_path.is_dir()

    def test_create_am_transfer_dir_already_exists(
        self, dest_dir, vd_container_converter, test_container_data
    ):
        check_path = dest_dir / "{}_{}".format(
            test_container_data["transfer_number"], test_container_data["name"]
        )
        check_path.mkdir()

        assert vd_container_converter.create_am_transfer_dir(dest_dir) is None

    def test_copy_submission_docs(
        self,
        dest_dir,
        vd_container_converter,
        vd_package_converter,
        test_container_data,
    ):
        subdocs_dir = dest_dir / "metadata" / "submissionDocumentation"
        vd_container_converter.copy_submission_docs(dest_dir)

        assert set(
            vd_package_converter.SUBMISSION_DOC_FILENAMES
            + [test_container_data["md_filename"]]
        ) == {i.name for i in subdocs_dir.iterdir()}

    def test_get_preservation_objects(
        self, vd_container_converter, test_container_data
    ):
        assert {doc["name"] for doc in test_container_data["documents"]} == {
            i.name for i in vd_container_converter.get_preservation_objects()
        }

    def test_get_md_filename(self, tmp_path, vd_container_converter):
        path = tmp_path / "test_file.pdf"
        name = vd_container_converter.get_md_filename(path)
        assert "test_file_Metadata.xml" == name

    def test_get_md5_hashes(self, vd_container_converter, test_container_data):
        hashes = []
        for doc in test_container_data["documents"]:
            hashes.append(
                (
                    doc["MD5hash"],
                    "{}/{}".format(test_container_data["name"], doc["name"]),
                )
            )

        assert hashes == vd_container_converter.get_md5_hashes()

    def test_not_get_md5_hashes(self, tmp_path):
        container_path = tmp_path / "foo"
        container_path.mkdir()

        converter = vd_converters.ContainerConverter(container_path)

        test_doc = container_path / "DOC_2009_040165.PDF"
        test_doc.touch()

        md_file = container_path / "DOC_2009_040165_Metadata.xml"
        md_file.write_text(
            "<ContainerDocumentMetadata>"
            "<Document></Document>"
            "</ContainerDocumentMetadata>"
        )

        with pytest.raises(RuntimeError):
            converter.get_md5_hashes()

    def test_write_am_checksum_file(
        self, dest_dir, vd_container_converter, test_container_data
    ):
        vd_container_converter.write_am_checksum_file(dest_dir)
        checksum_file = dest_dir / "metadata" / "checksum.md5"

        hash_text = "{}  {}/{}\n".format(
            test_container_data["documents"][0]["MD5hash"],
            test_container_data["name"],
            test_container_data["documents"][0]["name"],
        )

        assert hash_text == checksum_file.read_text()

    def test_get_container_metadata(
        self,
        vd_container_converter,
        test_container_data,
    ):
        assert (
            test_container_data["metadata"]
            == vd_container_converter.get_container_metadata()
        )

    def test_get_document_metadata(
        self,
        tmp_path,
        vd_container_converter,
        test_container_data,
    ):
        test_data = test_container_data["documents"][0]["metadata"]
        assert test_data == vd_container_converter.get_document_metadata(
            tmp_path
            / test_container_data["name"]
            / test_container_data["documents"][0]["name"]
        )

    def test_get_metadata_csv_path(self, dest_dir, vd_container_converter):
        assert (
            dest_dir / "metadata" / "metadata.csv"
            == vd_container_converter.get_metadata_csv_path(dest_dir)
        )

    def test_write_am_metadata(
        self, dest_dir, vd_container_converter, test_csv_data_full
    ):
        vd_container_converter.write_am_metadata(dest_dir)
        csv_file = dest_dir / "metadata" / "metadata.csv"

        with csv_file.open("r") as fh:
            csv_contents = list(csv.reader(fh))

        # Don't check the last row of csv_contents because it's a near
        # duplicate of the previous row
        assert test_csv_data_full == csv_contents[:3]

    def test_copy_preservation_objects(
        self, dest_dir, vd_container_converter, test_container_data
    ):
        vd_container_converter.copy_preservation_objects(dest_dir)
        object_dir = dest_dir / vd_container_converter.name

        assert {doc["name"] for doc in test_container_data["documents"]} == {
            i.name for i in object_dir.iterdir()
        }

    def test_get_desc_md_files(
        self,
        vd_container_converter,
        test_container_data,
    ):
        assert {
            doc["md_filename"] for doc in test_container_data["documents"]
        } == {i.name for i in vd_container_converter.get_desc_md_files()}

    def test_copy_desc_md_files(
        self, dest_dir, vd_container_converter, test_container_data
    ):
        vd_container_converter.copy_desc_md_files(dest_dir)
        sd_dir = dest_dir / "metadata" / "submissionDocumentation"

        assert {
            doc["md_filename"] for doc in test_container_data["documents"]
        } == {i.name for i in sd_dir.glob("*_Metadata.xml")}
