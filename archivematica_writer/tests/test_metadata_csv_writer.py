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
from archivematica_writer.metadata_csv_writer import AmMetadataCsvWriter


@pytest.fixture
def test_dcmi_data():
    return {
        "creator": "Smith, Jane",
        "date": "2021-11-15T08:12:34-08:00",
        "format": "jpeg",
        "identifier": "DOC/2021/040165",
        "source": "01-2700-10/0000007",
        "title": "Baby Smith, one day old",
        "type": "Image",
    }


@pytest.fixture
def test_csv_data():
    return {
        "dc.creator": "Smith, Jane",
        "dc.date": "2021-11-15T08:12:34-08:00",
        "dc.format": "jpeg",
        "dc.identifier": "DOC/2021/040165",
        "dc.source": "01-2700-10/0000007",
        "dc.title": "Baby Smith, one day old",
        "dc.type": "Image",
    }


class TestAmMetadataCsvWriter:
    def test_convert_dcmi_to_csv_keys(self, test_dcmi_data, test_csv_data):

        writer = AmMetadataCsvWriter("123456")

        assert test_csv_data == writer.convert_dcmi_to_csv_keys(test_dcmi_data)

    def test_add_row_data(self, test_csv_data):
        writer = AmMetadataCsvWriter("123456")
        writer.add_row_data("01-2700-10_0000007/DOC_2021_040165.DOC", test_csv_data)

        check_data = dict(test_csv_data)
        check_data["filename"] = "objects/01-2700-10_0000007/DOC_2021_040165.DOC"
        check_data["vandocs_transfer_number"] = "123456"

        assert check_data == writer.rows.pop()

    def test_add_dcmi_row_data(self, test_dcmi_data, test_csv_data):
        writer = AmMetadataCsvWriter("123456")
        writer.add_dcmi_row_data(
            "01-2700-10_0000007/DOC_2021_040165.DOC", test_dcmi_data
        )

        check_data = dict(test_csv_data)
        check_data["filename"] = "objects/01-2700-10_0000007/DOC_2021_040165.DOC"
        check_data["vandocs_transfer_number"] = "123456"

        assert check_data == writer.rows.pop()

    def test_write_csv_file(self, tmp_path, test_dcmi_data):
        csv_file = tmp_path / "metadata.csv"
        writer = AmMetadataCsvWriter("123456")
        writer.add_dcmi_row_data(
            "01-2700-10_0000007/DOC_2021_040165.DOC", test_dcmi_data
        )
        writer.write_csv_file(csv_file)

        check_csv_contents = (
            '"filename","dc.title","dc.creator","dc.subject","dc.description","dc.publisher","dc.contributor","dc.date","dc.type","dc.format","dc.identifier","dc.source","dc.language","dc.relation","dc.coverage","dc.rights","dc.provenance","vandocs_transfer_number"',
            '"objects/01-2700-10_0000007/DOC_2021_040165.DOC","Baby Smith, one day old","Smith, Jane","","","","","2021-11-15T08:12:34-08:00","Image","jpeg","DOC/2021/040165","01-2700-10/0000007","","","","","","123456"',
        )

        assert "\n".join(check_csv_contents) + "\n" == csv_file.read_text()
