"""Testes do detector Garmin — usam fixtures em disco (tmp_path), sem depender
do relógio físico. O XML de fixture usa a mesma estrutura confirmada por
análise real de um GarminDevice.xml (namespace, tags e campos)."""
from pathlib import Path

import pytest

from integrations.garmin.detector import find_garmin_device, parse_device_xml
from integrations.garmin.exceptions import GarminDeviceXmlError

VALID_XML = """<?xml version="1.0" encoding="UTF-8"?>
<Device xmlns="http://www.garmin.com/xmlschemas/GarminDevice/v2">
  <Model>
    <PartNumber>006-B3076-00</PartNumber>
    <SoftwareVersion>1370</SoftwareVersion>
    <Description>Forerunner 245</Description>
  </Model>
  <Id>3324546267</Id>
</Device>
"""

INCOMPLETE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<Device xmlns="http://www.garmin.com/xmlschemas/GarminDevice/v2">
  <Id>3324546267</Id>
</Device>
"""


def _write_device_xml(root: Path, content: str) -> Path:
    garmin_dir = root / "Garmin"
    garmin_dir.mkdir(parents=True, exist_ok=True)
    xml_path = garmin_dir / "GarminDevice.xml"
    xml_path.write_text(content, encoding="utf-8")
    return xml_path


def test_parse_device_xml_reads_confirmed_fields(tmp_path):
    xml_path = _write_device_xml(tmp_path, VALID_XML)
    info = parse_device_xml(xml_path)
    assert info.device_id == "3324546267"
    assert info.model_description == "Forerunner 245"
    assert info.model_part_number == "006-B3076-00"
    assert info.software_version == "1370"
    assert info.mount_point == tmp_path
    assert info.garmin_root == tmp_path / "Garmin"


def test_parse_device_xml_rejects_missing_model(tmp_path):
    xml_path = _write_device_xml(tmp_path, INCOMPLETE_XML)
    with pytest.raises(GarminDeviceXmlError):
        parse_device_xml(xml_path)


def test_parse_device_xml_rejects_malformed_xml(tmp_path):
    xml_path = _write_device_xml(tmp_path, "<not-xml")
    with pytest.raises(GarminDeviceXmlError):
        parse_device_xml(xml_path)


def test_find_garmin_device_locates_across_search_roots(tmp_path):
    empty_root = tmp_path / "no_device"
    empty_root.mkdir()
    device_root = tmp_path / "with_device"
    _write_device_xml(device_root, VALID_XML)

    found = find_garmin_device(search_roots=[empty_root, device_root])
    assert found is not None
    assert found.device_id == "3324546267"


def test_find_garmin_device_returns_none_when_absent(tmp_path):
    empty_root = tmp_path / "no_device"
    empty_root.mkdir()
    assert find_garmin_device(search_roots=[empty_root]) is None


def test_find_garmin_device_skips_broken_xml_and_keeps_searching(tmp_path):
    broken_root = tmp_path / "broken"
    _write_device_xml(broken_root, INCOMPLETE_XML)
    good_root = tmp_path / "good"
    _write_device_xml(good_root, VALID_XML)

    found = find_garmin_device(search_roots=[broken_root, good_root])
    assert found is not None
    assert found.device_id == "3324546267"
