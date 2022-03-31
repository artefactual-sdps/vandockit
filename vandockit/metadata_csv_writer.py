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


class AMMetadataCsvWriter:
    """Write Dublin Core (DCMI) metadata to a CSV file in Archivematica
    metadata.csv format"""

    COLUMNS = [
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
    ]

    def __init__(self, transfer_number):
        self.transfer_number = transfer_number
        self.rows = []

    def convert_dcmi_to_csv_keys(self, data):
        """Convert DCMI term names (e.g. "creator") to AM CSV column names
        (e.g. "dc.creator")"""
        csv_data = {}

        for term, value in data.items():
            csv_data["dc." + term] = value

        return csv_data

    def add_row_data(self, rel_path, data):
        """Add a row of data to be written to the CSV file.  The data must be a
        dict of format {"filename": value1, "dc.title": value2}"""

        # Add filename and transfer number to descriptive metadata
        data["filename"] = "objects/" + rel_path
        data["vandocs_transfer_number"] = self.transfer_number

        self.rows.append(data)

    def add_dcmi_row_data(self, rel_path, dcmi_data):
        csv_data = self.convert_dcmi_to_csv_keys(dcmi_data)

        self.add_row_data(rel_path, csv_data)

    def write_csv_file(self, path):
        with path.open("w") as fh:
            writer = csv.DictWriter(fh, dialect="unix", fieldnames=self.COLUMNS)
            writer.writeheader()

            for row in self.rows:
                writer.writerow(row)
