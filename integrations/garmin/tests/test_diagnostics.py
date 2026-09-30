from pathlib import Path

from integrations.garmin.diagnostics import run_diagnostics

XML = """<?xml version="1.0" encoding="UTF-8"?>
<Device xmlns="http://www.garmin.com/xmlschemas/GarminDevice/v2">
  <Model>
    <PartNumber>006-B3076-00</PartNumber>
    <SoftwareVersion>1370</SoftwareVersion>
    <Description>Forerunner 245</Description>
  </Model>
  <Id>3324546267</Id>
</Device>
"""


def _fixture_device(tmp_path: Path) -> Path:
    root = tmp_path / "GARMIN"
    (root / "Garmin").mkdir(parents=True)
    (root / "Garmin" / "GarminDevice.xml").write_text(XML, encoding="utf-8")
    (root / "Garmin" / "Activity").mkdir()
    (root / "Garmin" / "Activity" / "activity_001.fit").write_bytes(b"FIT-FIXTURE")
    (root / "Garmin" / "Monitor").mkdir()
    (root / "Garmin" / "Monitor" / "sleep.dat").write_bytes(b"DATA")
    return root


def test_diagnostics_inventory_without_physical_device(tmp_path):
    root = _fixture_device(tmp_path)
    result = run_diagnostics([root])

    assert result.connected is True
    assert result.device_xml_valid is True
    assert result.model_description == "Forerunner 245"
    assert result.total_files == 3
    assert result.extensions[".fit"] == 1
    assert result.extensions[".dat"] == 1
    assert result.extensions[".xml"] == 1
    assert "Activity" in result.top_level_entries


def test_diagnostics_reports_missing_device(tmp_path):
    result = run_diagnostics([tmp_path / "does-not-exist"])

    assert result.connected is False
    assert result.device_xml_valid is False
    assert result.total_files == 0
    assert result.errors
