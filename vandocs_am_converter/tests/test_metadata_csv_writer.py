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
from vandocs_am_converter.metadata_csv_writer import AmMetadataCsvWriter


class TestAMMetadataCsvWriter:
    def test_convert_dcmi_to_csv_keys(self, test_csv_md_dict, test_document_data):

        writer = AmMetadataCsvWriter("123456")

        assert test_csv_md_dict == writer.convert_dcmi_to_csv_keys(
            test_document_data[0]["metadata"]
        )

    def test_add_row_data(self, test_csv_md_dict):
        writer = AmMetadataCsvWriter("123456")
        writer.add_row_data("01-2700-10_0000007/DOC_2021_040165.DOC", test_csv_md_dict)

        check_data = dict(test_csv_md_dict)
        check_data["filename"] = "objects/01-2700-10_0000007/DOC_2021_040165.DOC"
        check_data["vandocs_transfer_number"] = "123456"

        assert check_data == writer.rows.pop()

    def test_add_dcmi_row_data(self, test_document_data, test_csv_md_dict):
        writer = AmMetadataCsvWriter("123456")
        writer.add_dcmi_row_data(
            "01-2700-10_0000007/DOC_2021_040165.DOC", test_document_data[0]["metadata"]
        )

        check_data = dict(test_csv_md_dict)
        check_data["filename"] = "objects/01-2700-10_0000007/DOC_2021_040165.DOC"
        check_data["vandocs_transfer_number"] = "123456"

        assert check_data == writer.rows.pop()

    def test_write_csv_file(
        self,
        tmp_path,
        test_container_data,
        test_csv_data_full,
    ):
        csv_file = tmp_path / "metadata.csv"
        writer = AmMetadataCsvWriter("123456")
        writer.add_dcmi_row_data(
            "01-2500-10_0000007",
            test_container_data["metadata"],
        )
        writer.add_dcmi_row_data(
            "01-2500-10_0000007/DOC_2009_040165.PDF",
            test_container_data["documents"][0]["metadata"],
        )
        writer.write_csv_file(csv_file)

        csv_data_string = ""
        for row in test_csv_data_full:
            csv_data_string += '"' + '","'.join(row) + '"\n'

        assert csv_data_string == csv_file.read_text()
