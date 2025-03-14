from pathlib import Path
from zipfile import ZipFile
from typing import Any, Optional

from lxml import etree


class TiliaMXLReader:
    def __init__(
        self,
        path: str,
        file_kwargs: Optional[dict[str, Any]] = None,
        reader_kwargs: Optional[dict[str, Any]] = None,
    ):
        self.path = Path(path)
        self.file_kwargs = file_kwargs or {}
        self.reader_kwargs = reader_kwargs or {}

    def _get_mxl_data(self):
        with (
            ZipFile(self.path) as zipfile,
            zipfile.open("META-INF/container.xml", **self.file_kwargs) as meta,
        ):
            full_path = (
                etree.parse(meta, **self.reader_kwargs)
                .findall(".//rootfile")[0]
                .get("full-path")
            )
            data = zipfile.open(full_path, **self.file_kwargs)
        return data

    def __enter__(self):

        if ".mxl" == self.path.suffix:
            self.file = self._get_mxl_data()
        else:
            self.file = open(self.path, **self.file_kwargs)

        parser = etree.XMLParser(remove_blank_text=True)
        self.tree = etree.parse(
            self.file, parser=parser, **self.reader_kwargs
        ).getroot()
        self.is_read = True

        if self.tree.tag == "score-timewise":
            self.tree = _convert_to_partwise(self.tree)
        elif self.tree.tag != "score-partwise":
            self.is_read = False

        if self.is_read:
            self.is_read = _validate_musicxml(self.tree)
        if not self.is_read:
            raise SyntaxError
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.file.close()


def _convert_to_partwise(element: etree._Element) -> etree._Element:
    xsl_path = Path(__file__).resolve().parent / "timewise_to_partwise.xsl"
    with open(str(xsl_path), "r", encoding="utf-8") as xsl:
        xsl_tree = etree.parse(xsl)

    transform = etree.XSLT(xsl_tree)
    return transform(element)


def _validate_musicxml(element: etree._Element) -> bool:
    xsd_path = Path(__file__).resolve().parent / "musicxml.xsd"
    with open(str(xsd_path), "r", encoding="utf-8") as xsd:
        xsd_schema = etree.XMLSchema(etree.parse(xsd))

    return xsd_schema.validate(element)


def _pretty_str_from_xml_element(element: etree._Element):
    return etree.tostring(element, pretty_print=True).decode("utf-8")
