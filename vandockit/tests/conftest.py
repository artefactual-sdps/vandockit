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

import pytest

# Local modules
import vandockit.converters as vd_converters
import vandockit.validators as vd_validators


@pytest.fixture(scope="package")
def test_container_data(test_document_data):
    return {
        "transfer_number": "123456",
        "transfer_name": "VanDocs-123456",
        "name": "01-2500-10_0000007",
        "md_filename": "ContainerMetadata.xml",
        "metadata": {
            "creator": "Smith Family",
            "date": "2022-02-15T12:00:00-08:00",
            "description": "The list of our current eBooks",
            "identifier": "01-2500-10/0000007",
            "provenance": "The Internet",
            "title": "eBook Library",
            "type": "Series",
        },
        "documents": test_document_data,
    }


@pytest.fixture(scope="package")
def test_document_data():
    return [
        {
            "name": "DOC_2009_040165.PDF",
            "md_filename": "DOC_2009_040165_Metadata.xml",
            "metadata": {
                "creator": "Smith, Jane",
                "date": "2021-11-15T08:12:34-08:00",
                "format": "pdf",
                "identifier": "DOC/2009/040165",
                "source": "01-2500-10/0000007",
                "title": "Book 1",
                "type": "Document",
            },
            "MD5hash": "4d118b7297d8469c2833046fa48471cf",
        }
    ]


@pytest.fixture(scope="package")
def test_container_md_xml(test_container_data):
    return """
    <ContainerMetadata>
        <Container>
            <Creator>{creator}</Creator>
            <DateCreated>{date}</DateCreated>
            <Department>{provenance}</Department>
            <RecordNumber>{identifier}</RecordNumber>
            <RecordType>{type}</RecordType>
            <TitleFreeTextPart>{description}</TitleFreeTextPart>
            <TitleStructuredPart>{title}</TitleStructuredPart>
        </Container>
    </ContainerMetadata>""".format(
        **test_container_data["metadata"]
    )


@pytest.fixture(scope="package")
def test_csv_md_dict():
    return {
        "dc.creator": "Smith, Jane",
        "dc.date": "2021-11-15T08:12:34-08:00",
        "dc.format": "pdf",
        "dc.identifier": "DOC/2009/040165",
        "dc.source": "01-2500-10/0000007",
        "dc.title": "Book 1",
        "dc.type": "Document",
    }


@pytest.fixture(scope="package")
def test_document_md_xml(test_document_data):
    xml_string = """
<ContainerDocumentMetadata>
    <Document>
        <Creator>{creator}</Creator>
        <DateCreated>{date}</DateCreated>
        <Home>{source}</Home>
        <InternetMediaType>{format}</InternetMediaType>
        <RecordNumber>{identifier}</RecordNumber>
        <RecordType>{type}</RecordType>
        <Title>{title}</Title>
        <MD5>{MD5hash}</MD5>
    </Document>
</ContainerDocumentMetadata>"""

    return [
        xml_string.format(**doc["metadata"], MD5hash=doc["MD5hash"])
        for doc in test_document_data
    ]


@pytest.fixture(scope="package")
def test_csv_data_full(test_container_data, test_document_data):
    header = [
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

    container_row = [
        "objects/" + test_container_data["name"],
        test_container_data["metadata"]["title"],
        test_container_data["metadata"]["creator"],
        "",
        test_container_data["metadata"]["description"],
        "",
        "",
        test_container_data["metadata"]["date"],
        test_container_data["metadata"]["type"],
        "",
        test_container_data["metadata"]["identifier"],
        "",
        "",
        "",
        "",
        "",
        test_container_data["metadata"]["provenance"],
        test_container_data["transfer_number"],
    ]

    document_row = [
        "objects/{}/{}".format(
            test_container_data["name"], test_document_data[0]["name"]
        ),
        test_document_data[0]["metadata"]["title"],
        test_document_data[0]["metadata"]["creator"],
        "",
        "",
        "",
        "",
        test_document_data[0]["metadata"]["date"],
        test_document_data[0]["metadata"]["type"],
        test_document_data[0]["metadata"]["format"],
        test_document_data[0]["metadata"]["identifier"],
        test_document_data[0]["metadata"]["source"],
        "",
        "",
        "",
        "",
        "",
        test_container_data["transfer_number"],
    ]

    return [header, container_row, document_row]


# test_package must be in "function" scope to match tmp_path's scope, which
# prevents filesystem cross-effects between tests
@pytest.fixture
def test_package(
    tmp_path, test_container_data, test_container_md_xml, test_document_md_xml
):
    package = tmp_path / test_container_data["transfer_name"]
    package.mkdir()

    for name in vd_validators.PackageValidator.required_files:
        file = package / name
        file.touch()

    container = package / test_container_data["name"]
    container.mkdir()

    con_md_file = container / test_container_data["md_filename"]
    con_md_file.write_text(test_container_md_xml)

    for i, doc in enumerate(test_container_data["documents"]):
        doc_file = container / doc["name"]
        doc_file.touch()

        md_file = container / doc["md_filename"]
        md_file.write_text(test_document_md_xml[i])

    return package
