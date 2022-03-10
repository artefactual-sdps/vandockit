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

# Local modules
from vandocs_am_converter.metadata_xml_parser import (
    BaseXmlParser,
    ContainerXmlParser,
    DocumentXmlParser,
)


@pytest.fixture
def container_md_file(tmp_path, test_container_md_xml):
    file = tmp_path / "ContainerMetadata.xml"
    file.write_text(test_container_md_xml)

    return file


@pytest.fixture
def document_md_file(tmp_path, test_document_md_xml):
    file = tmp_path / "DOC_2009_040165_Metadata.xml"
    file.write_text(test_document_md_xml[0])

    return file


class TestBaseXmlParser:
    def test_get_xml_root(self, container_md_file):
        parser = BaseXmlParser(container_md_file)
        xml_root = parser.get_xml_root()

        assert "ContainerMetadata" == xml_root.tag

    def test_fail_get_xml_root(self, tmp_path):
        empty_file = tmp_path / "empty.xml"
        empty_file.touch()

        parser = BaseXmlParser(empty_file)

        with pytest.raises(RuntimeError) as excinfo:
            parser.get_xml_root()

            assert "Couldn't parse XML tree" in str(excinfo.value)


class TestContainerXmlParser:
    def test_get_value(self, container_md_file):
        parser = ContainerXmlParser(container_md_file)

        assert "Smith Family" == parser.get_value("Creator")

    def test_get_value_not_found(self, container_md_file):
        parser = ContainerXmlParser(container_md_file)

        with pytest.raises(RuntimeError) as excinfo:
            parser.get_value("foo")

            assert 'XML element "foo" not found' in str(excinfo.value)

    def test_get_dcmi_data(self, container_md_file, test_container_data):
        parser = ContainerXmlParser(container_md_file)

        assert test_container_data["metadata"] == parser.get_dcmi_data()


class TestDocumentXmlParser:
    def test_get_value(self, document_md_file):
        parser = DocumentXmlParser(document_md_file)

        assert "Smith, Jane" == parser.get_value("Creator")

    def test_get_dcmi_data(self, document_md_file, test_document_data):
        parser = DocumentXmlParser(document_md_file)

        assert test_document_data[0]["metadata"] == parser.get_dcmi_data()

    def test_get_md5_hash(self, document_md_file):
        parser = DocumentXmlParser(document_md_file)

        assert "4d118b7297d8469c2833046fa48471cf" == parser.get_md5_hash()
