import machine
from machine import Pin
import time

# Prueba unitaria del Módulo Relé en el pin D26
machine.mem32[0x3FF480D4] = 0
rele = Pin(26, Pin.OUT)

print("Probando Rele en pin D26 (Cada 2 segundos conmuta)...")

while True:
    print("-> Rele ACTIVADO (0 / LOW)")
    rele.value(0)
    time.sleep(2)

    print("-> Rele DESACTIVADO (1 / HIGH)")
    rele.value(1)
    time.sleep(2)
