import machine
from machine import Pin
import time

# Prueba unitaria del sensor ultrasónico HC-SR04 (Trig=D5, Echo=D18)
trig = Pin(5, Pin.OUT)
echo = Pin(18, Pin.IN)

print("Probando sensor ultrasonico HC-SR04 (Trig=D5, Echo=D18)...")

while True:
    trig.value(0)
    time.sleep_us(2)
    trig.value(1)
    time.sleep_us(10)
    trig.value(0)

    duracion = machine.time_pulse_us(echo, 1, 30000)

    if duracion < 0:
        print("Sin eco (Revisa que VCC este en VIN/5V, Trig en D5 y Echo en D18)")
    else:
        distancia_cm = round((duracion * 0.0343) / 2, 1)
        print(f"Distancia medida: {distancia_cm} cm")

    time.sleep(0.5)
