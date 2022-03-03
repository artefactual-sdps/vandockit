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

import pytest
import time

# Local modules
import vandocs_validator.package_validator as validators

PKG_MD_FILES = ["TransferLog.txt"] + validators.VanDocsValidator.required_files
CONTAINERS = ["01-2500-10_0000007"]
CONTAINER_MD_FILES = ["ContainerMetadata.xml"]

DOCUMENTS = [
    "DOC_2009_016088.PDF",
    "DOC_2009_016092.PDF",
]
DOC_MD_FILES = [
    "DOC_2009_016088_Metadata.xml",
    "DOC_2009_016092_Metadata.xml",
]

CONTAINER_FILES = CONTAINER_MD_FILES + DOCUMENTS + DOC_MD_FILES

MD5_HASHES = ["4d118b7297d8469c2833046fa48471cf", "7c0086cd150d36b1dac61c4a7f86d4eb"]
DOCUMENT_MD_XML = """
<ContainerDocumentMetadata>
    <Document>
        <MD5>{}</MD5>
    </Document>
</ContainerDocumentMetadata>
"""


@pytest.fixture
def test_package_no_ctr(tmp_path):
    package = tmp_path / "Package_001"
    package.mkdir()

    for name in PKG_MD_FILES:
        file = package / name
        file.touch()

    return package


@pytest.fixture
def test_package(test_package_no_ctr):
    package = test_package_no_ctr

    for cname in CONTAINERS:
        container = package / cname
        container.mkdir()

        j = 0
        for i in range(len(CONTAINER_FILES)):
            file = container / CONTAINER_FILES[i]

            if file.name in DOC_MD_FILES:
                # Write MD hash data to document metadata files
                file.write_text(DOCUMENT_MD_XML.format(MD5_HASHES[j]))
                j += 1
            else:
                file.touch()

    return package


@pytest.fixture
def package_validator(test_package):
    validator = validators.PackageValidator("vandocs", test_package)

    return validator


@pytest.fixture
def vandocs_validator(test_package):
    validator = validators.PackageValidatorFactory.get_validator(
        "vandocs", test_package
    )

    return validator


@pytest.fixture
def vandocs_ctr_validator(test_package):
    package_validator = validators.PackageValidatorFactory.get_validator(
        "vandocs", test_package
    )
    validator = validators.VanDocsContainerValidator(
        "vandocs", test_package / CONTAINERS[0], package_validator
    )

    return validator


def mocktime(timestr):
    """Mock to replace time.time() with a deterministic epoch time set by an ISO
    "YYYY-MM-DD HH:MM:SS" string"""

    def f():
        return time.mktime(time.strptime(timestr, "%Y-%m-%d %H:%M:%S"))

    return f


class TestPackageValidatorFactory:
    def test_get_validator(self, vandocs_validator):
        assert isinstance(vandocs_validator, validators.VanDocsValidator)

    def test_get_unknown_validator(self, test_package):
        with pytest.raises(ValueError):
            validators.PackageValidatorFactory.get_validator("spam", test_package)


class TestPackageValidator:
    def test_set_path_not_found(self, test_package):
        validator = validators.PackageValidator("vandocs", test_package / "nodir")

        with pytest.raises(FileNotFoundError):
            validator.get_contents()

    def test_set_path_not_a_dir(self, test_package):
        validator = validators.PackageValidator(
            "vandocs", test_package / "manifest.txt"
        )

        with pytest.raises(NotADirectoryError):
            validator.get_contents()

    def test_get_name(self, package_validator):
        assert package_validator.get_name() == "Package_001"

    def test_has_errors(self, package_validator):
        package_validator.failed = 1

        assert package_validator.has_errors()

    def test_start_timer(self, monkeypatch, package_validator):
        monkeypatch.setattr(time, "time", mocktime("2022-02-11 12:00:00"))

        package_validator.start_timer("validation")

        assert (
            mocktime("2022-02-11 12:00:00")()
            == package_validator.timer["validation"]["start"]
        )

    def test_stop_timer(self, monkeypatch, package_validator):
        monkeypatch.setattr(time, "time", mocktime("2022-02-11 12:00:00"))
        package_validator.stop_timer("validation")

        assert (
            mocktime("2022-02-11 12:00:00")()
            == package_validator.timer["validation"]["end"]
        )

    def test_get_elapsed_time(self, monkeypatch, package_validator):
        monkeypatch.setattr(time, "time", mocktime("2022-02-11 12:00:00"))
        package_validator.start_timer("validation")

        monkeypatch.setattr(time, "time", mocktime("2022-02-11 12:00:01"))
        package_validator.stop_timer("validation")

        assert 1.0 == package_validator.get_elapsed_time("validation")

    def test_get_contents(self, package_validator):
        contents = package_validator.get_contents()

        # Diff sets so arbitrary file order doesn't break the test
        assert not set(x.name for x in contents) ^ set(CONTAINERS + PKG_MD_FILES)


class TestVanDocsValidator:
    def test_has_required_files(self, vandocs_validator):
        assert vandocs_validator.has_required_files()

    def test_not_has_required_files(self, test_package):
        manifest = test_package / "manifest.txt"
        manifest.unlink()
        validator = validators.VanDocsValidator("vandocs", test_package)

        assert not validator.has_required_files()

    def test_has_empty_transfer_log(self, vandocs_validator):
        assert vandocs_validator.has_empty_transfer_log()

    def test_not_has_empty_transfer_log(self, test_package):
        tlog = test_package / "TransferLog.txt"
        tlog.write_text("Not empty!")
        validator = validators.VanDocsValidator("vandocs", test_package)

        assert not validator.has_empty_transfer_log()

    def test_has_empty_transfer_log_missing_file(self, test_package):
        tlog = test_package / "TransferLog.txt"
        tlog.unlink()
        validator = validators.VanDocsValidator("vandocs", test_package)

        assert not validator.has_empty_transfer_log()

    def test_get_containers(self, vandocs_validator):
        assert not set(vandocs_validator.get_containers()) ^ set(CONTAINERS)

    def test_has_a_container(self, vandocs_validator):
        assert vandocs_validator.has_a_container()

    def test_not_has_a_container(self, test_package_no_ctr):
        validator = validators.VanDocsValidator("vandocs", test_package_no_ctr)

        assert not validator.has_a_container()

    def test_get_summary_msg(self, monkeypatch, vandocs_validator):
        monkeypatch.setattr(time, "time", mocktime("2022-02-11 12:00:01"))
        vandocs_validator.validate()

        assert (
            'VALID: all 12 checks for Package "Package_001" passed [0.0s]'
            == vandocs_validator.get_summary_msg()
        )

    def test_invalid_get_summary_msg(self, monkeypatch, test_package_no_ctr):
        validator = validators.VanDocsValidator("vandocs", test_package_no_ctr)
        monkeypatch.setattr(time, "time", mocktime("2022-02-11 12:00:01"))
        validator.validate()

        assert (
            'INVALID: 1 of 7 checks for Package "Package_001" failed [0.0s]'
            == validator.get_summary_msg()
        )


class TestVanDocsContainerValidator:
    def test_context_prefix(self, vandocs_ctr_validator):
        assert (
            'Container "Package_001/{}" '.format(CONTAINERS[0])
            == vandocs_ctr_validator.context_prefix()
        )

    def test_has_required_files(self, vandocs_ctr_validator):
        assert vandocs_ctr_validator.has_required_files()

    def test_has_not_required_files(self, test_package):
        metadata_file = test_package / CONTAINERS[0] / CONTAINER_FILES[0]
        metadata_file.unlink()
        package_validator = validators.PackageValidatorFactory.get_validator(
            "vandocs", test_package
        )
        validator = validators.VanDocsContainerValidator(
            "vandocs", test_package / CONTAINERS[0], package_validator
        )

        assert not validator.has_required_files()

    def test_split_object_and_metadata_filenames(self, vandocs_ctr_validator):
        (
            object_files,
            metadata_files,
        ) = vandocs_ctr_validator.split_object_and_metadata_filenames()

        # Use set diff to ignore list element order
        assert not set(DOCUMENTS) ^ set(object_files)
        assert not set(DOC_MD_FILES) ^ set(metadata_files)

    def test_has_objects(self, vandocs_ctr_validator):
        assert vandocs_ctr_validator.has_objects(["DOC_2009_016088.PDF"])

    def test_not_has_objects(self, vandocs_ctr_validator):
        assert not vandocs_ctr_validator.has_objects([])

    def test_has_one_metadata_file_per_object(self, vandocs_ctr_validator):
        assert vandocs_ctr_validator.has_one_metadata_file_per_object(
            ["DOC_2009_016088.PDF"], ["DOC_2009_016088_Metadata.xml"]
        )

    def test_not_has_one_metadata_file_per_object(self, vandocs_ctr_validator):
        assert not vandocs_ctr_validator.has_one_metadata_file_per_object(
            ["DOC_2009_016088.PDF"], []
        )

    def test_has_one_object_per_metadata_file(self, vandocs_ctr_validator):
        assert vandocs_ctr_validator.has_one_metadata_file_per_object(
            ["DOC_2009_016088.PDF"], ["DOC_2009_016088_Metadata.xml"]
        )

    def test_not_has_one_object_per_metadata_file(self, vandocs_ctr_validator):
        assert not vandocs_ctr_validator.has_one_object_per_metadata_file(
            [], ["DOC_2009_016088_Metadata.xml"]
        )

    def test_has_checksum_metadata(self, vandocs_ctr_validator):
        assert vandocs_ctr_validator.has_checksum_metadata(
            ["DOC_2009_016088_Metadata.xml"]
        )

    def test_not_has_checksum_metadata(self, test_package, vandocs_validator):
        # Delete checksum data
        md_file = test_package / "01-2500-10_0000007" / "DOC_2009_016092_Metadata.xml"
        md_file.write_text("")

        validator = validators.VanDocsContainerValidator(
            "vandocs", test_package / CONTAINERS[0], vandocs_validator
        )

        assert not validator.has_checksum_metadata(["DOC_2009_016092_Metadata.xml"])
