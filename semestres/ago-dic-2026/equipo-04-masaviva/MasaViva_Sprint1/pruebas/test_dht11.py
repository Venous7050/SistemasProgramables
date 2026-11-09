from machine import Pin
import dht
import time

# Prueba unitaria del sensor DHT11 en el pin D4
pin_datos = Pin(4, Pin.IN, Pin.PULL_UP)
sensor = dht.DHT11(pin_datos)

print("Probando sensor DHT11 en el pin D4...")
time.sleep(1)

while True:
    try:
        sensor.measure()
        temp = sensor.temperature()
        hum = sensor.humidity()
        print(f"Lectura correcta -> Temperatura: {temp} °C | Humedad: {hum} %")
    except OSError:
        print("Error de lectura (Revisa que DATA este en D4, + en 3V3 y - en GND)")

    time.sleep(2)
