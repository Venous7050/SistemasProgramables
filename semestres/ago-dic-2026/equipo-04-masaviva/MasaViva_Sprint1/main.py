import machine
from machine import Pin, ADC, PWM
import network
import dht
import time
import ubinascii
import ujson
import urequests
import ntptime
import gc
from umqtt.simple import MQTTClient

# ==============================================================================
# 1. DESACTIVAR DETECTOR DE BROWNOUT (Evita reinicios con Wi-Fi + Relé)
# ==============================================================================
machine.mem32[0x3FF480D4] = 0

# ==============================================================================
# 2. CONFIGURACIÓN DE WI-FI, MQTT Y FIREBASE
# ==============================================================================
WIFI_SSID = "Nothing Phone (3)"
WIFI_PASS = "123456789"

# --- Configuración de Firebase Realtime Database ---
FIREBASE_URL = "https://TU-PROYECTO-default-rtdb.firebaseio.com"
INTERVALO_FIREBASE_MS = 15000  # Guardar en Firebase cada 15 segundos

# --- Configuración de Bróker MQTT ---
MQTT_BROKER = "test.mosquitto.org"
MQTT_PORT   = 1883
CLIENT_ID   = b"masaviva_" + ubinascii.hexlify(machine.unique_id())
INTERVALO_MQTT_MS = 3000       # Publicar a MQTT cada 3 segundos

# Tópicos donde el ESP32 PUBLICA hacia tu celular
TOPIC_PUB_DHT         = b"masaviva/sensor/dht"
TOPIC_PUB_TEMP        = b"masaviva/sensor/temp"
TOPIC_PUB_HUM         = b"masaviva/sensor/hum"
TOPIC_PUB_LUZ         = b"masaviva/sensor/luz"
TOPIC_PUB_TAPA        = b"masaviva/sensor/tapa"
TOPIC_PUB_CRECIMIENTO = b"masaviva/sensor/crecimiento"
TOPIC_PUB_ESTADO      = b"masaviva/estado"

# Tópicos que el ESP32 ESCUCHA desde tu celular (Switches)
TOPIC_SUB_RELE        = b"masaviva/control/rele"
TOPIC_SUB_BUZZER      = b"masaviva/control/buzzer"

# ==============================================================================
# 3. CONFIGURACIÓN DE PINES (HARDWARE MASAVIVA)
# ==============================================================================
ldr = ADC(Pin(34))
ldr.atten(ADC.ATTN_11DB)
ldr.width(ADC.WIDTH_12BIT)

led_verde    = Pin(14, Pin.OUT)  # D14 -> Óptimo (24-28 °C)
led_amarillo = Pin(27, Pin.OUT)  # D27 -> Calentando (< 24 °C)
led_rojo     = Pin(12, Pin.OUT)  # D12 -> Alerta (> 28 °C o Tapa abierta)

RELE_ACTIVO_EN_BAJO = True
pin_rele = Pin(26, Pin.OUT)      # D26 -> IN1 del Relé

buzzer = PWM(Pin(25))            # D25 -> Buzzer
buzzer.duty(0)

sensor_dht = dht.DHT11(Pin(4, Pin.IN, Pin.PULL_UP))  # D4 -> DHT11

trig = Pin(5, Pin.OUT)           # D5  -> Trig HC-SR04
echo = Pin(18, Pin.IN)           # D18 -> Echo HC-SR04

# ==============================================================================
# 4. PARÁMETROS DE FERMENTACIÓN Y VARIABLES DE CONTROL
# ==============================================================================
TEMP_MIN = 24.0
TEMP_MAX = 28.0
UMBRAL_TAPA_LUZ = 75
DISTANCIA_FRASCO_VACIO = 16.0
DISTANCIA_MASA_LISTA   = 8.0

modo_rele = "AUTO"
calefactor_encendido = False


# ==============================================================================
# 5. FUNCIONES DE HARDWARE Y SENSORES
# ==============================================================================
def controlar_rele(encender):
    global calefactor_encendido
    calefactor_encendido = encender
    if RELE_ACTIVO_EN_BAJO:
        pin_rele.value(0 if encender else 1)
    else:
        pin_rele.value(1 if encender else 0)


def poner_leds(verde, amarillo, rojo):
    led_verde.value(1 if verde else 0)
    led_amarillo.value(1 if amarillo else 0)
    led_rojo.value(1 if rojo else 0)


def sonar_buzzer(frecuencia=1500, duracion_ms=150):
    buzzer.freq(frecuencia)
    buzzer.duty(512)
    time.sleep_ms(duracion_ms)
    buzzer.duty(0)


def leer_luz_ldr():
    lectura_raw = ldr.read()
    porcentaje_luz = int((4095 - lectura_raw) * 100 / 4095)
    return max(0, min(100, porcentaje_luz))


def medir_distancia_cm():
    try:
        trig.value(0)
        time.sleep_us(2)
        trig.value(1)
        time.sleep_us(10)
        trig.value(0)
        duracion = machine.time_pulse_us(echo, 1, 30000)
        if duracion < 0:
            return None
        return round((duracion * 0.0343) / 2.0, 1)
    except Exception:
        return None


def leer_dht11():
    try:
        sensor_dht.measure()
        return sensor_dht.temperature(), sensor_dht.humidity()
    except Exception:
        return None, None


def obtener_fecha_hora():
    t = time.localtime(time.time() - 6 * 3600)
    return "{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(t[0], t[1], t[2], t[3], t[4], t[5])


# ==============================================================================
# 6. ENVÍO DE REGISTROS A FIREBASE REALTIME DATABASE
# ==============================================================================
def guardar_en_firebase(temp, hum, luz_pct, tapa_abierta, distancia_cm, crecimiento_pct, estado):
    if "TU-PROYECTO" in FIREBASE_URL:
        print("ℹ️ Firebase pendiente: pon tu link en FIREBASE_URL para guardar en la nube.")
        return

    gc.collect()
    registro = {
        "fecha_hora": obtener_fecha_hora(),
        "temperatura_c": temp,
        "humedad_pct": hum,
        "luz_pct": luz_pct,
        "tapa": "ABIERTA" if tapa_abierta else "CERRADA",
        "distancia_cm": distancia_cm if distancia_cm is not None else -1,
        "crecimiento_pct": crecimiento_pct,
        "calefactor_rele": "ON" if calefactor_encendido else "OFF",
        "modo_rele": modo_rele,
        "estado": estado
    }
    datos_json = ujson.dumps(registro)

    try:
        url_actual = f"{FIREBASE_URL}/masaviva/estado_actual.json"
        res1 = urequests.put(url_actual, data=datos_json)
        res1.close()

        url_historial = f"{FIREBASE_URL}/masaviva/historial.json"
        res2 = urequests.post(url_historial, data=datos_json)
        res2.close()

        print(f"🔥 Guardado en Firebase -> [{registro['fecha_hora']}] Temp:{temp}C | Masa:{crecimiento_pct}%")
    except Exception as e:
        print("⚠️ Error al guardar en Firebase:", e)
    finally:
        gc.collect()


# ==============================================================================
# 7. CONEXIÓN WI-FI Y MQTT
# ==============================================================================
def conectar_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print(f"Conectando a Wi-Fi '{WIFI_SSID}'...", end="")
        wlan.connect(WIFI_SSID, WIFI_PASS)
        intentos = 0
        while not wlan.isconnected() and intentos < 30:
            print(".", end="")
            time.sleep(0.5)
            intentos += 1
    if wlan.isconnected():
        print("\n✅ Wi-Fi Conectado! IP:", wlan.ifconfig()[0])
        try:
            ntptime.settime()
            print("🕒 Hora sincronizada por internet:", obtener_fecha_hora())
        except Exception:
            print("⚠️ No se pudo sincronizar la hora NTP, usando reloj interno.")
        return True
    else:
        print("\n❌ No se pudo conectar al Wi-Fi. Revisa SSID y contraseña.")
        return False


def al_recibir_mqtt(topico, mensaje):
    global modo_rele
    msg = mensaje.decode("utf-8").strip().upper()
    print(f"📩 Comando desde celular -> Tópico: {topico.decode()} | Mensaje: {msg}")

    if topico == TOPIC_SUB_RELE:
        if msg in ["ON", "1"]:
            modo_rele = "ON"
            controlar_rele(True)
        elif msg in ["OFF", "0"]:
            modo_rele = "OFF"
            controlar_rele(False)
        else:
            modo_rele = "AUTO"

    elif topico == TOPIC_SUB_BUZZER:
        if msg in ["ON", "1"]:
            sonar_buzzer(1800, 300)
        else:
            buzzer.duty(0)


def conectar_mqtt():
    client = MQTTClient(CLIENT_ID, MQTT_BROKER, port=MQTT_PORT, keepalive=60)
    client.set_callback(al_recibir_mqtt)
    client.connect()
    client.subscribe(TOPIC_SUB_RELE)
    client.subscribe(TOPIC_SUB_BUZZER)
    print("✅ Conectado al bróker MQTT y suscrito a controles del celular!")
    return client


# ==============================================================================
# 8. PROGRAMA PRINCIPAL
# ==============================================================================
def main():
    controlar_rele(False)
    poner_leds(True, False, False)
    time.sleep(0.3)
    poner_leds(False, True, False)
    time.sleep(0.3)
    poner_leds(False, False, True)
    sonar_buzzer(1800, 120)
    time.sleep(0.3)
    poner_leds(False, False, False)

    conectar_wifi()

    client = None
    try:
        client = conectar_mqtt()
    except Exception as e:
        print("⚠️ Error conectando a MQTT:", e)

    ultimo_envio_mqtt     = time.ticks_ms()
    ultimo_envio_firebase = time.ticks_ms()
    temp, hum = 0, 0

    print("\n🚀 MasaViva en ejecución (MQTT cada 3s | Firebase cada 15s)...\n")

    while True:
        try:
            if client:
                client.check_msg()

            ahora = time.ticks_ms()

            if time.ticks_diff(ahora, ultimo_envio_mqtt) >= INTERVALO_MQTT_MS:
                ultimo_envio_mqtt = ahora

                luz_pct = leer_luz_ldr()
                t_leida, h_leida = leer_dht11()
                if t_leida is not None:
                    temp, hum = t_leida, h_leida

                distancia_cm = medir_distancia_cm()
                tapa_abierta = luz_pct >= UMBRAL_TAPA_LUZ

                if distancia_cm is not None:
                    rango = DISTANCIA_FRASCO_VACIO - DISTANCIA_MASA_LISTA
                    avance = DISTANCIA_FRASCO_VACIO - distancia_cm
                    crecimiento_pct = int(max(0, min(100, (avance / rango) * 100)))
                    masa_lista = distancia_cm <= DISTANCIA_MASA_LISTA
                    str_crecimiento = f"{crecimiento_pct}% ({distancia_cm} cm)"
                else:
                    crecimiento_pct = 0
                    masa_lista = False
                    str_crecimiento = "Sin lectura"

                if tapa_abierta:
                    if modo_rele == "AUTO":
                        controlar_rele(False)
                    poner_leds(False, False, True)
                    sonar_buzzer(2000, 80)
                    estado = "ALERTA: TAPA ABIERTA"
                elif masa_lista:
                    if modo_rele == "AUTO":
                        controlar_rele(False)
                    poner_leds(True, False, False)
                    sonar_buzzer(1500, 150)
                    estado = "MASA LISTA PARA HORNEAR"
                elif temp < TEMP_MIN:
                    if modo_rele == "AUTO":
                        controlar_rele(True)
                    poner_leds(False, True, False)
                    estado = "CALENTANDO (<24C)"
                elif TEMP_MIN <= temp <= TEMP_MAX:
                    if modo_rele == "AUTO":
                        controlar_rele(False)
                    poner_leds(True, False, False)
                    estado = "FERMENTACION OPTIMA (24-28C)"
                else:
                    if modo_rele == "AUTO":
                        controlar_rele(False)
                    poner_leds(False, False, True)
                    sonar_buzzer(2500, 150)
                    estado = "EXCESO DE TEMP (>28C)"

                str_tapa = "ABIERTA" if tapa_abierta else "CERRADA"
                str_dht  = f"{temp} C | {hum} %"

                print(f"📡 MQTT -> Temp/Hum: {str_dht} | Luz: {luz_pct}% ({str_tapa}) | Masa: {str_crecimiento} | {estado}")

                if client:
                    client.publish(TOPIC_PUB_DHT, str_dht)
                    client.publish(TOPIC_PUB_TEMP, str(temp))
                    client.publish(TOPIC_PUB_HUM, str(hum))
                    client.publish(TOPIC_PUB_LUZ, f"{luz_pct}%")
                    client.publish(TOPIC_PUB_TAPA, str_tapa)
                    client.publish(TOPIC_PUB_CRECIMIENTO, str_crecimiento)
                    client.publish(TOPIC_PUB_ESTADO, estado)

                if time.ticks_diff(ahora, ultimo_envio_firebase) >= INTERVALO_FIREBASE_MS:
                    ultimo_envio_firebase = ahora
                    guardar_en_firebase(
                        temp, hum, luz_pct, tapa_abierta, distancia_cm, crecimiento_pct, estado
                    )

            time.sleep_ms(50)

        except Exception as e:
            print("⚠️ Reconectando MQTT...", e)
            time.sleep(2)
            try:
                client = conectar_mqtt()
            except Exception:
                pass


main()
