# MasaViva: Incubadora Inteligente para Masa Madre (IoT) — Sprint 1

> **Tecnología + Pan = Mejor fermentación**  
> Sistema embebido e IoT basado en **ESP32** para el control térmico automatizado (24–28 °C), monitoreo de crecimiento por ultrasonido, detección de apertura de tapa y telemetría en tiempo real mediante **MQTT** y **Firebase Realtime Database**.

---

##  Datos del Proyecto

- **Materia:** Sistemas Programables
- **Institución:** Tecnológico Nacional de México / Instituto Tecnológico de León
- **Carrera:** Ingeniería en Sistemas Computacionales
- **Estudiante:** - **Estudiante:** Diego Alejandro Morales Vega, Juan Pablo Mateo Vazquez Ortega, Christopher Leonardo Troncoso Ponce
- **Docente:** Ma. Verónica Tapia Ibarra
- **Entrega:** Sprint 1 — Integración de Sensores, Actuadores, Control Térmico y Telemetría IoT

---

##  Problema que Resuelve

La masa madre necesita una temperatura estable (**24 °C – 28 °C**), humedad adecuada y utilizarse en el momento exacto de máximo crecimiento. En casa o en pequeñas panaderías artesanales, la temperatura ambiente varía constantemente y es difícil saber cuándo la masa duplicó su volumen, provocando panes que no suben o masa sobrefermentada.

**MasaViva** automatiza el proceso dentro de una cámara aislada controlada por un **ESP32 DevKit** y monitoreada desde el teléfono móvil.

---

##  Topología de Hardware y Mapa de Pines (Pinout ESP32 DevKit)

| Componente | Tipo | Pin del Módulo | Pin en ESP32 DevKit | Función en el Sistema |
| :--- | :--- | :--- | :--- | :--- |
| **Sensor DHT11** | Entrada Digital | `VCC` / `DATA` / `GND` | `3V3` / **`GPIO 4 (D4)`** / `GND` | Mide temperatura (°C) y humedad relativa (%) dentro de la incubadora. |
| **Ultrasónico HC-SR04** | Entrada Digital | `VCC` / `Trig` / `Echo` / `GND` | `VIN (5V)` / **`GPIO 5 (D5)`** / **`GPIO 18 (D18)`** / `GND` | Mide la distancia hacia la superficie de la masa para calcular el `%` de crecimiento. |
| **Módulo LDR** | Entrada Analógica | `VCC` / `AO` / `GND` | `3V3` / **`GPIO 34 (D34)`** / `GND` | Detecta entrada brusca de luz cuando se abre la tapa de la incubadora. |
| **Módulo Relé (Canal J1)** | Salida Digital | `VCC` / `IN1` / `GND` | `VIN (5V)` / **`GPIO 26 (D26)`** / `GND` | Enciende/apaga el foco o resistencia calefactora para mantener `24–28 °C`. |
| **Buzzer** | Salida PWM | `+` / `-` | **`GPIO 25 (D25)`** / `GND` | Emite alertas sonoras cuando la masa está lista o si hay alerta térmica/tapa abierta. |
| **LED Verde** | Salida Digital | Ánodo (`+`) / Cátodo (`-`) | **`GPIO 14 (D14)`** / `GND` | Indica estado óptimo de fermentación (`24 °C – 28 °C`). |
| **LED Amarillo** | Salida Digital | Ánodo (`+`) / Cátodo (`-`) | **`GPIO 27 (D27)`** / `GND` | Indica calefactor encendido subiendo temperatura (`< 24 °C`). |
| **LED Rojo** | Salida Digital | Ánodo (`+`) / Cátodo (`-`) | **`GPIO 12 (D12)`** / `GND` | Indica alerta por exceso de temperatura (`> 28 °C`) o tapa abierta. |

---

##  Arquitectura de Comunicación IoT (MQTT + Firebase)

### 1. Tópicos MQTT (`test.mosquitto.org:1883`)

| Dirección | Tópico MQTT | Ejemplo de Payload | Descripción |
| :--- | :--- | :--- | :--- |
| **Publicación** | `masaviva/sensor/dht` | `"26 C \| 60 %"` | Lectura combinada de temperatura y humedad |
| **Publicación** | `masaviva/sensor/temp` | `"26"` | Temperatura actual en `°C` |
| **Publicación** | `masaviva/sensor/hum` | `"60"` | Humedad relativa actual en `%` |
| **Publicación** | `masaviva/sensor/luz` | `"15%"` | Porcentaje de iluminación interna (LDR) |
| **Publicación** | `masaviva/sensor/tapa` | `"CERRADA"` / `"ABIERTA"` | Estado de la puerta/tapa de la incubadora |
| **Publicación** | `masaviva/sensor/crecimiento` | `"50% (12.0 cm)"` | Nivel de crecimiento de la masa madre |
| **Publicación** | `masaviva/estado` | `"FERMENTACION OPTIMA (24-28C)"` | Estado operativo del sistema |
| **Suscripción** | `masaviva/control/rele` | `"ON"`, `"OFF"`, `"AUTO"` | Control manual o automático del calefactor desde el celular |
| **Suscripción** | `masaviva/control/buzzer` | `"ON"`, `"OFF"` | Prueba o silenciamiento remoto del buzzer |

### 2. Almacenamiento en Firebase Realtime Database
Cada 15 segundos el sistema envía un objeto JSON vía REST (`HTTPS PUT / POST`) a:
- `/masaviva/estado_actual.json`: Estado en vivo de la incubadora.
- `/masaviva/historial.json`: Bitácora histórica con marca de tiempo (`NTP UTC-6`).

---

##  Estructura del Repositorio (Sprint 1)

```text
MasaViva_Sprint1
 ┣  pruebas
 ┃ ┣  test_dht11.py        # Prueba unitaria del sensor de temperatura y humedad DHT11 (Pin D4)
 ┃ ┣  test_rele.py         # Prueba unitaria de conmutación del módulo Relé (Pin D26)
 ┃ ┗  test_ultrasonico.py  # Prueba unitaria de medición de distancia HC-SR04 (Pines D5 y D18)
 ┣  main.py                # Firmware principal integrado (Sensores + Actuadores + MQTT + Firebase)
 ┗  README.md              # Documentación técnica del Sprint 1
```
