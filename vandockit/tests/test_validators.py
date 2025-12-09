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

import time

import pytest

# Local modules
import vandockit.validators as vd_validators


@pytest.fixture
def test_package_no_ctr(tmp_path, test_container_data):
    package = tmp_path / test_container_data["transfer_name"]
    package.mkdir()

    transfer_log = package / "TransferLog.txt"
    transfer_log.touch()

    for filename in vd_validators.PackageValidator.required_files:
        file = package / filename
        file.touch()

    return package


@pytest.fixture
def vd_base_validator(test_package):
    validator = vd_validators.BaseValidator("vandocs", test_package)

    return validator


@pytest.fixture
def vd_package_validator(test_package):
    validator = vd_validators.PackageValidatorFactory.get_validator(
        "vandocs", test_package
    )

    return validator


@pytest.fixture
def vd_container_validator(test_package, test_container_data):
    validator = vd_validators.ContainerValidator(
        "vandocs", test_package / test_container_data["name"]
    )

    return validator


def mocktime(timestr):
    """Mock to replace time.time() with a deterministic epoch time set by an
    ISO "YYYY-MM-DD HH:MM:SS" string"""

    def f():
        return time.mktime(time.strptime(timestr, "%Y-%m-%d %H:%M:%S"))

    return f


class TestPackageValidatorFactory:
    def test_get_validator(self, vd_package_validator):
        assert isinstance(vd_package_validator, vd_validators.PackageValidator)

    def test_get_unknown_validator(self, test_package):
        with pytest.raises(ValueError):
            vd_validators.PackageValidatorFactory.get_validator(
                "spam", test_package
            )


class TestBaseValidator:
    def test_set_path_not_found(self, test_package):
        validator = vd_validators.BaseValidator(
            "vandocs", test_package / "nodir"
        )

        with pytest.raises(FileNotFoundError):
            validator.get_contents()

    def test_set_path_not_a_dir(self, test_package):
        validator = vd_validators.BaseValidator(
            "vandocs", test_package / "manifest.txt"
        )

        with pytest.raises(NotADirectoryError):
            validator.get_contents()

    def test_get_name(self, vd_base_validator):
        assert vd_base_validator.get_name() == "VanDocs-123456"

    def test_has_errors(self, vd_base_validator):
        vd_base_validator.failed = 1

        assert vd_base_validator.has_errors()

    def test_start_timer(self, monkeypatch, vd_base_validator):
        monkeypatch.setattr(time, "time", mocktime("2022-02-11 12:00:00"))

        vd_base_validator.start_timer("validation")

        assert (
            mocktime("2022-02-11 12:00:00")()
            == vd_base_validator.timer["validation"]["start"]
        )

    def test_stop_timer(self, monkeypatch, vd_base_validator):
        monkeypatch.setattr(time, "time", mocktime("2022-02-11 12:00:00"))
        vd_base_validator.stop_timer("validation")

        assert (
            mocktime("2022-02-11 12:00:00")()
            == vd_base_validator.timer["validation"]["end"]
        )

    def test_get_elapsed_time(self, monkeypatch, vd_base_validator):
        monkeypatch.setattr(time, "time", mocktime("2022-02-11 12:00:00"))
        vd_base_validator.start_timer("validation")

        monkeypatch.setattr(time, "time", mocktime("2022-02-11 12:00:01"))
        vd_base_validator.stop_timer("validation")

        assert 1.0 == vd_base_validator.get_elapsed_time("validation")

    def test_get_contents(self, vd_base_validator, test_container_data):
        contents = vd_base_validator.get_contents()

        # Compare sets so arbitrary file order doesn't cause false negatives
        assert {x.name for x in contents} == set(
            [test_container_data["name"], "TransferLog.txt"]
            + vd_validators.PackageValidator.required_files
        )


class TestPackageValidator:
    def test_has_required_files(self, vd_package_validator):
        assert vd_package_validator.has_required_files()

    def test_not_has_required_files(self, test_package):
        manifest = test_package / "manifest.txt"
        manifest.unlink()
        validator = vd_validators.PackageValidator("vandocs", test_package)

        assert not validator.has_required_files()

    def test_has_empty_transfer_log(self, vd_package_validator):
        assert vd_package_validator.has_empty_transfer_log()

    def test_not_has_empty_transfer_log(self, test_package):
        tlog = test_package / "TransferLog.txt"
        tlog.write_text("Not empty!")
        validator = vd_validators.PackageValidator("vandocs", test_package)

        assert not validator.has_empty_transfer_log()

    def test_has_empty_transfer_log_missing_file(self, test_package):
        tlog = test_package / "TransferLog.txt"
        tlog.unlink()
        validator = vd_validators.PackageValidator("vandocs", test_package)

        assert not validator.has_empty_transfer_log()

    def test_get_containers(self, vd_package_validator, test_container_data):
        assert set(vd_package_validator.get_containers()) == {
            test_container_data["name"]
        }

    def test_has_a_container(self, vd_package_validator):
        assert vd_package_validator.has_a_container()

    def test_not_has_a_container(self, test_package_no_ctr):
        validator = vd_validators.PackageValidator(
            "vandocs", test_package_no_ctr
        )

        assert not validator.has_a_container()

    def test_get_summary_msg(self, monkeypatch, vd_package_validator):
        monkeypatch.setattr(time, "time", mocktime("2022-02-11 12:00:01"))
        vd_package_validator.validate()

        assert (
            'VALID: all 13 checks for Package "VanDocs-123456" passed [0.0s]'
            == vd_package_validator.get_summary_msg()
        )

    def test_invalid_get_summary_msg(self, monkeypatch, test_package_no_ctr):
        validator = vd_validators.PackageValidator(
            "vandocs", test_package_no_ctr
        )
        monkeypatch.setattr(time, "time", mocktime("2022-02-11 12:00:01"))
        validator.validate()

        assert (
            'INVALID: 1 of 8 checks for Package "VanDocs-123456" failed [0.0s]'
            == validator.get_summary_msg()
        )


class TestContainerValidator:
    def test_context_prefix(self, vd_container_validator, test_container_data):
        assert (
            'Container "{}" '.format(test_container_data["name"])
            == vd_container_validator.context_prefix()
        )

    def test_has_required_files(self, vd_container_validator):
        assert vd_container_validator.has_required_files()

    def test_has_not_required_files(self, test_package, test_container_data):
        metadata_file = (
            test_package
            / test_container_data["name"]
            / test_container_data["md_filename"]
        )
        metadata_file.unlink()

        validator = vd_validators.ContainerValidator(
            "vandocs", test_package / test_container_data["name"]
        )

        assert not validator.has_required_files()

    def test_split_object_and_metadata_filenames(
        self, vd_container_validator, test_container_data
    ):
        (
            object_files,
            metadata_files,
        ) = vd_container_validator.split_object_and_metadata_filenames()

        # Use set diff to ignore list element order
        assert {
            doc["name"] for doc in test_container_data["documents"]
        } == set(object_files)
        assert {
            doc["md_filename"] for doc in test_container_data["documents"]
        } == set(metadata_files)

    def test_has_objects(self, vd_container_validator):
        assert vd_container_validator.has_objects(["DOC_2009_040165.PDF"])

    def test_not_has_objects(self, vd_container_validator):
        assert not vd_container_validator.has_objects([])

    def test_has_one_metadata_file_per_object(self, vd_container_validator):
        assert vd_container_validator.has_one_metadata_file_per_object(
            ["DOC_2009_040165.PDF"], ["DOC_2009_040165_Metadata.xml"]
        )

    def test_not_has_one_metadata_file_per_object(
        self, vd_container_validator
    ):
        assert not vd_container_validator.has_one_metadata_file_per_object(
            ["DOC_2009_040165.PDF"], []
        )

    def test_has_one_object_per_metadata_file(self, vd_container_validator):
        assert vd_container_validator.has_one_metadata_file_per_object(
            ["DOC_2009_040165.PDF"], ["DOC_2009_040165_Metadata.xml"]
        )

    def test_not_has_one_object_per_metadata_file(
        self, vd_container_validator
    ):
        assert not vd_container_validator.has_one_object_per_metadata_file(
            [], ["DOC_2009_040165_Metadata.xml"]
        )

    def test_has_checksum_metadata(self, vd_container_validator):
        assert vd_container_validator.has_checksum_metadata(
            ["DOC_2009_040165_Metadata.xml"]
        )

    def test_not_has_checksum_metadata(
        self, test_package, test_container_data
    ):
        # Delete checksum data
        md_file = (
            test_package
            / test_container_data["name"]
            / "DOC_2009_016092_Metadata.xml"
        )
        md_file.write_text("")

        validator = vd_validators.ContainerValidator(
            "vandocs", test_package / test_container_data["name"]
        )

        assert not validator.has_checksum_metadata(
            ["DOC_2009_016092_Metadata.xml"]
        )
