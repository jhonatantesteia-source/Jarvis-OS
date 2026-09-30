"""Nomes de eventos que o módulo Garmin publica no Event Bus do Jarvis.

Mantidos como constantes (em vez de strings soltas) para que agentes,
o HUD e futuros módulos possam se inscrever sem depender de literais
espalhados pelo código.
"""

DEVICE_CONNECTED = "garmin.device.connected"
DEVICE_DISCONNECTED = "garmin.device.disconnected"
