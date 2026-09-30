"""Exceções do módulo de integração Garmin."""


class GarminIntegrationError(Exception):
    """Erro base de qualquer falha do módulo Garmin."""


class GarminDeviceXmlError(GarminIntegrationError):
    """GarminDevice.xml ausente, ilegível, ou sem a estrutura mínima esperada
    (Model + Id) para ser considerado um dispositivo Garmin válido."""
