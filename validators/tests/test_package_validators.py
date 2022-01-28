import validators.package_validators as validators
import pytest
import xml.etree.ElementTree as ET

PKG_FILES = ["TransferLog.txt"] + validators.VanDocsValidator.required_files
CONTAINERS = ["01-2500-10_0000007"]

OBJECT_FILES = [
    "DOC_2009_016088.PDF",
    "DOC_2009_016092.PDF",
]
OBJECT_MD_FILES = [
    "DOC_2009_016088_Metadata.xml",
    "DOC_2009_016092_Metadata.xml",
]
CONTAINER_FILES = ["ContainerMetadata.xml"] + OBJECT_FILES + OBJECT_MD_FILES

DOCUMENT_MD_XML = """
<ContainerDocumentMetadata>
    <Document>
        <MD5>4d118b7297d8469c2833046fa48471cf</MD5>
    </Document>
</ContainerDocumentMetadata>"""


@pytest.fixture
def test_package_no_ctr(tmp_path):
    package = tmp_path / "Package_001"
    package.mkdir()

    for name in PKG_FILES:
        file = package / name
        file.touch()

    return package


@pytest.fixture
def test_package(test_package_no_ctr):
    package = test_package_no_ctr

    for name in CONTAINERS:
        dir = package / name
        dir.mkdir()

        for filename in CONTAINER_FILES:
            file = package / name / filename

            if "DOC_2009_016088_Metadata.xml" == filename:
                file.write_text(DOCUMENT_MD_XML)
            else:
                file.touch()

    return package


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
        package_validator, test_package / CONTAINERS[0]
    )

    return validator


class TestPackageValidatorFactory:
    def test_get_validator(self, vandocs_validator):
        assert isinstance(vandocs_validator, validators.VanDocsValidator)

    def test_get_unknown_validator(self, test_package):
        with pytest.raises(ValueError):
            validators.PackageValidatorFactory.get_validator("spam", test_package)


class TestPackageValidator:
    def test_context_prefix(self, vandocs_validator):
        assert 'Package "Package_001" ' == vandocs_validator.context_prefix()

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

    def test_get_contents(self, vandocs_validator):
        contents = vandocs_validator.get_contents()

        # Diff sets so arbitrary file order doesn't break the test
        assert not set(x.name for x in contents) ^ set(CONTAINERS + PKG_FILES)

    def test_get_name(self, vandocs_validator):
        assert vandocs_validator.get_name() == "Package_001"


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
            package_validator, test_package / CONTAINERS[0]
        )

        assert not validator.has_required_files()

    def test_split_object_and_metadata_filenames(self, vandocs_ctr_validator):
        (
            object_files,
            metadata_files,
        ) = vandocs_ctr_validator.split_object_and_metadata_filenames()

        # Use set diff to ignore list element order
        assert not set(OBJECT_FILES) ^ set(object_files)
        assert not set(OBJECT_MD_FILES) ^ set(metadata_files)

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

    def test_not_has_checksum_metadata(self, vandocs_ctr_validator):
        assert not vandocs_ctr_validator.has_checksum_metadata(
            ["DOC_2009_016092_Metadata.xml"]
        )

    def test_get_xml_md5_hash(self, vandocs_ctr_validator):
        assert (
            "4d118b7297d8469c2833046fa48471cf"
            == vandocs_ctr_validator.get_xml_md5_hash(ET.fromstring(DOCUMENT_MD_XML))
        )
