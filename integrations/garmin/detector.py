"""Detecção de um relógio Garmin conectado via USB (modo Mass Storage).

Estratégia validada na análise do Garmin.zip: o próprio dispositivo grava
`Garmin/GarminDevice.xml` na raiz da unidade quando montado — é a mesma
assinatura que softwares oficiais Garmin usam para reconhecê-lo. Não
dependemos de WMI/pywin32 nesta etapa; a varredura de letras de unidade
é suficiente e testável sem hardware físico via `search_roots`.
"""
from __future__ import annotations

import string
import xml.etree.ElementTree as ET
from pathlib import Path

from integrations.garmin.exceptions import GarminDeviceXmlError
from integrations.garmin.models import GarminDeviceInfo

_XML_NAMESPACE = "{http://www.garmin.com/xmlschemas/GarminDevice/v2}"
_DEVICE_XML_RELATIVE_PATH = Path("Garmin") / "GarminDevice.xml"


def _tag(name: str) -> str:
    return f"{_XML_NAMESPACE}{name}"


def list_removable_roots() -> list[Path]:
    """Enumera raízes de unidade candidatas (A:\\ a Z:\\) no Windows.

    Fora do Windows isto naturalmente não encontra nada — os testes
    unitários não dependem desta função, e injetam `search_roots`
    explicitamente em `find_garmin_device`.
    """
    return [root for letter in string.ascii_uppercase if (root := Path(f"{letter}:/")).exists()]


def parse_device_xml(xml_path: Path) -> GarminDeviceInfo:
    """Lê um GarminDevice.xml e extrai apenas os campos confirmados por análise real:
    Model/PartNumber, Model/SoftwareVersion, Model/Description e Id.

    Levanta GarminDeviceXmlError se o arquivo não puder ser lido/parseado,
    ou se não tiver a estrutura mínima (Model + Id) para ser considerado válido.
    """
    try:
        root = ET.parse(xml_path).getroot()
    except ET.ParseError as exc:
        raise GarminDeviceXmlError(f"XML inválido em {xml_path}: {exc}") from exc
    except OSError as exc:
        raise GarminDeviceXmlError(f"Não foi possível ler {xml_path}: {exc}") from exc

    model = root.find(_tag("Model"))
    device_id = root.findtext(_tag("Id"))
    if model is None or not device_id:
        raise GarminDeviceXmlError(f"GarminDevice.xml sem <Model> ou <Id> em {xml_path}")

    return GarminDeviceInfo(
        mount_point=xml_path.parents[1],
        garmin_root=xml_path.parent,
        device_id=device_id,
        model_description=model.findtext(_tag("Description")) or "",
        model_part_number=model.findtext(_tag("PartNumber")) or "",
        software_version=model.findtext(_tag("SoftwareVersion")) or "",
    )


def find_garmin_device(search_roots: list[Path] | None = None) -> GarminDeviceInfo | None:
    """Procura um relógio Garmin entre as raízes informadas (ou detectadas no Windows).

    Retorna o primeiro dispositivo válido encontrado, ou None se nenhuma
    unidade contiver um Garmin/GarminDevice.xml legível. Uma unidade com
    XML corrompido não interrompe a busca nas demais.
    """
    roots = search_roots if search_roots is not None else list_removable_roots()
    for root in roots:
        xml_path = root / _DEVICE_XML_RELATIVE_PATH
        if not xml_path.is_file():
            continue
        try:
            return parse_device_xml(xml_path)
        except GarminDeviceXmlError:
            continue
    return None
