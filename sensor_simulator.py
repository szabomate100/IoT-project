import os
import time
import random
from datetime import datetime
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS


INFLUXDB_URL = os.getenv("INFLUXDB_URL", "http://localhost:8086") # Pl.: "http://localhost:8086" vagy a felhős URL
INFLUXDB_TOKEN = os.getenv("INFLUXDB_TOKEN", "mytoken")      # Cseréld le a saját InfluxDB API Tokenedre
INFLUXDB_ORG = os.getenv("INFLUXDB_ORG", "myorg")          # Cseréld le a saját InfluxDB Organization nevedre/ID-re
INFLUXDB_BUCKET = os.getenv("INFLUXDB_BUCKET", "patients") # Az InfluxDB Bucket neve, ahova írni szeretnél

SIMULATION_INTERVAL_SECONDS = 5

#  Betegek alapadatai
PATIENTS = {
    "P001": {
        "name": "Patient1",
        "condition": "Hypertonia",
        "bp_range": (140, 190),
        "spo2_range": (92, 98),
        "pulse_range": (80, 120)
    },
    "P002": {
        "name": "Patient2",
        "condition": "Hypotension",
        "bp_range": (80, 100),
        "spo2_range": (96, 99),
        "pulse_range": (50, 70)
    },
    "P003": {
        "name": "Patient3",
        "condition": "Pneumonia",
        "bp_range": (110, 130),
        "spo2_range": (85, 93),
        "pulse_range": (90, 130)
    },
    "P004": {
        "name": "Patient4",
        "condition": "Bradycardia",
        "bp_range": (120, 140),
        "spo2_range": (97, 99),
        "pulse_range": (40, 55)
    },
    "P005": {
        "name": "Patient5",
        "condition": "Tachycardia",
        "bp_range": (130, 150),
        "spo2_range": (95, 98),
        "pulse_range": (120, 160)
    }
}

#  Szimulációs Függvény

def simulate_vitals(patient_info):

    pulse_min, pulse_max = patient_info["pulse_range"]
    spo2_min, spo2_max = patient_info["spo2_range"]
    bp_sys_min, bp_sys_max = patient_info["bp_range"]

    # random.gauss(mu, sigma) ahol mu a középérték, sigma a szórás

    # Pulzus szimuláció
    pulse_mu = (pulse_min + pulse_max) / 2
    pulse_sigma = (pulse_max - pulse_min) / 6
    pulse = int(random.gauss(pulse_mu, pulse_sigma))
    # Ésszerű határok közé szorítás
    pulse = max(30, min(220, pulse)) #Pulzus nem lehet 220 felett és 30 alatt

    # SpO2 szimuláció
    spo2_mu = (spo2_min + spo2_max) / 2
    spo2_sigma = (spo2_max - spo2_min) / 4
    spo2 = int(random.gauss(spo2_mu, spo2_sigma))
    # Ésszerű határok közé szorítás
    spo2 = max(70, min(100, spo2)) # SpO2 nem lehet 100 felett és 70 alatt

    # Vérnyomás szimuláció (Szisztolés/Diasztolés)
    bp_sys_mu = (bp_sys_min + bp_sys_max) / 2
    bp_sys_sigma = (bp_sys_max - bp_sys_min) / 6
    bp_systolic = int(random.gauss(bp_sys_mu, bp_sys_sigma))
    # Ésszerű határok közé szorítás
    bp_systolic = max(70, min(250, bp_systolic)) # BP nem lehet 250 felett és 70 alatt

    # Diasztolés becslése a szisztolés alapján a szisztolés 60-75%-a + kis véletlenszerűség
    diastolic_ratio = random.uniform(0.6, 0.75)
    bp_diastolic = int(bp_systolic * diastolic_ratio + random.gauss(0, 5))
    # Ésszerű határok közé szorítás
    bp_diastolic = max(40, min(bp_systolic - 10, 150)) # Kisebb a szisztolésnál illetve minimum 40 maximum 150


    return {
        "pulse": pulse,
        "spo2": spo2,
        "bp_systolic": bp_systolic,
        "bp_diastolic": bp_diastolic
    }


print("--- Kórházi Szenzor Szimulátor Indítása ---")
print(f"InfluxDB URL: {INFLUXDB_URL}")
print(f"InfluxDB Org: {INFLUXDB_ORG}")
print(f"InfluxDB Bucket: {INFLUXDB_BUCKET}")
print(f"Szimulációs időköz: {SIMULATION_INTERVAL_SECONDS} másodperc")
print("-----------------------------------------")

measurement_name = "patient_vitals"


with InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG) as client:
    write_api = client.write_api(write_options=SYNCHRONOUS)
    print("Sikeres kapcsolat az InfluxDB-vel.")

    while True:
        points_to_write = []

        print(f"\n--- Új szimulációs ciklus: {datetime.now()} ---")

        for patient_id, patient_data in PATIENTS.items():

            vitals = simulate_vitals(patient_data)
            point = Point(measurement_name) \
                    .tag("patient_id", patient_id) \
                    .tag("patient_name", patient_data["name"]) \
                    .tag("condition", patient_data["condition"]) \
                    .field("pulse", vitals["pulse"]) \
                    .field("spo2", vitals["spo2"]) \
                    .field("bp_systolic", vitals["bp_systolic"]) \
                    .field("bp_diastolic", vitals["bp_diastolic"]) \
                    .time(datetime.utcnow(), WritePrecision.NS)
            points_to_write.append(point)

            print(f"  {patient_data['name']} ({patient_id}): "
                      f"Pulse={vitals['pulse']}, SpO2={vitals['spo2']}%, "
                      f"BP={vitals['bp_systolic']}/{vitals['bp_diastolic']} mmHg")

        if points_to_write:
            write_api.write(bucket=INFLUXDB_BUCKET, org=INFLUXDB_ORG, record=points_to_write)
            print(f"-> Sikeresen elküldve {len(points_to_write)} adatpont az InfluxDB-be ('{INFLUXDB_BUCKET}' bucket).")

        time.sleep(SIMULATION_INTERVAL_SECONDS)
