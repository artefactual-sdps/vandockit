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

import xml.etree.ElementTree as ET


class BaseXmlParser:
    def __init__(self, xml_file):
        self.xml_file = xml_file
        self.xml_root = None

    def get_xml_root(self):
        if not self.xml_root:
            try:
                xml_tree = ET.parse(self.xml_file)
                self.xml_root = xml_tree.getroot()
            except ET.ParseError as err:
                raise RuntimeError(
                    f'Couldn\'t parse XML tree in "{self.xml_file}"'
                ) from err

        return self.xml_root

    def get_value(self, name):
        xml_root = self.get_xml_root()
        nodes = xml_root.findall("./" + self.ITEM_WRAPPER + "/" + name)

        if 0 == len(nodes):
            raise RuntimeError(
                f'XML element "{name}" not found in "{self.xml_file}"'
            )

        return nodes[0].text

    def get_dcmi_data(self):
        """Get DCMI (https://www.dublincore.org/specifications/dublin-core/dcmi-terms/)
        data as a dict"""
        data = {}

        for xml_element_name, dcmi_term_name in self.DCMI_DATA_MAP.items():
            data[dcmi_term_name] = self.get_value(xml_element_name)

        return data


class ContainerXmlParser(BaseXmlParser):
    ITEM_WRAPPER = "Container"

    # Map XML elements to DCMI terms {xml_element_name: dcmi_term_name}
    DCMI_DATA_MAP = {
        "Creator": "creator",
        "DateCreated": "date",
        "Department": "provenance",
        "RecordNumber": "identifier",
        "RecordType": "type",
        "TitleFreeTextPart": "description",
        "TitleStructuredPart": "title",
    }


class DocumentXmlParser(BaseXmlParser):
    ITEM_WRAPPER = "Document"

    # Map XML elements to DCMI terms {xml_element_name: dcmi_term_name}
    DCMI_DATA_MAP = {
        "Creator": "creator",
        "DateCreated": "date",
        "Home": "source",
        "InternetMediaType": "format",
        "RecordNumber": "identifier",
        "RecordType": "type",
        "Title": "title",
    }

    def get_md5_hash(self):
        return self.get_value("MD5")
