import os
import time
import random
from datetime import datetime
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

# --- Konfiguráció ---

INFLUXDB_URL = os.getenv("INFLUXDB_URL", "http://localhost:8086") # Pl.: "http://localhost:8086" vagy a felhős URL
INFLUXDB_TOKEN = os.getenv("INFLUXDB_TOKEN", "mytoken")      # Cseréld le a saját InfluxDB API Tokenedre
INFLUXDB_ORG = os.getenv("INFLUXDB_ORG", "myorg")          # Cseréld le a saját InfluxDB Organization nevedre/ID-re
INFLUXDB_BUCKET = os.getenv("INFLUXDB_BUCKET", "patients") # Az InfluxDB Bucket neve, ahova írni szeretnél

# Szimuláció gyakorisága másodpercben
SIMULATION_INTERVAL_SECONDS = 5

# --- Betegek alapadatai ---
PATIENTS = {
    "P001": {
        "name": "Patient1",
        "condition": "Hypertonia",
        "bp_range": (140, 190),  # Systolic range (example)
        "spo2_range": (92, 98),
        "pulse_range": (80, 120)
    },
    "P002": {
        "name": "Patient2",
        "condition": "Hypotension", # Javítottam
        "bp_range": (80, 100),   # Systolic range (example)
        "spo2_range": (96, 99),
        "pulse_range": (50, 70)
    },
    "P003": {
        "name": "Patient3",
        "condition": "Pneumonia",
        "bp_range": (110, 130),  # Systolic range (example)
        "spo2_range": (85, 93),  # Lower SpO2 expected
        "pulse_range": (90, 130) # Often elevated pulse
    },
    "P004": {
        "name": "Patient4",
        "condition": "Bradycardia",
        "bp_range": (120, 140),  # Systolic range (example)
        "spo2_range": (97, 99),
        "pulse_range": (40, 55)   # Lower pulse expected
    },
    "P005": {
        "name": "Patient5",
        "condition": "Tachycardia",
        "bp_range": (130, 150),  # Systolic range (example)
        "spo2_range": (95, 98),
        "pulse_range": (120, 160) # Higher pulse expected
    }
}

# --- Szimulációs Függvény ---

def simulate_vitals(patient_info):
    """
    Generál szimulált élettani adatokat a beteg információi alapján.
    Visszaad egy dictionary-t: {'pulse': int, 'spo2': int, 'bp_systolic': int, 'bp_diastolic': int}
    """
    pulse_min, pulse_max = patient_info["pulse_range"]
    spo2_min, spo2_max = patient_info["spo2_range"]
    bp_sys_min, bp_sys_max = patient_info["bp_range"] # Ezt most szisztolésnak vesszük

    # Gauss (normális) eloszlást használunk a középérték körüli szimulációhoz
    # -> random.gauss(mu, sigma) ahol mu a középérték, sigma a szórás

    # Pulzus szimuláció
    pulse_mu = (pulse_min + pulse_max) / 2
    pulse_sigma = (pulse_max - pulse_min) / 6
    pulse = int(random.gauss(pulse_mu, pulse_sigma))
    # Ésszerű határok közé szorítás
    pulse = max(30, min(220, pulse))

    # SpO2 szimuláció
    spo2_mu = (spo2_min + spo2_max) / 2
    spo2_sigma = (spo2_max - spo2_min) / 4 # Kisebb szórás az SpO2-nél
    spo2 = int(random.gauss(spo2_mu, spo2_sigma))
    # Ésszerű határok közé szorítás
    spo2 = max(70, min(100, spo2)) # SpO2 nem lehet 100 felett

    # Vérnyomás szimuláció (Szisztolés/Diasztolés)
    # Egyszerűsített logika: Diasztolés általában a szisztolés egy része
    bp_sys_mu = (bp_sys_min + bp_sys_max) / 2
    bp_sys_sigma = (bp_sys_max - bp_sys_min) / 6
    bp_systolic = int(random.gauss(bp_sys_mu, bp_sys_sigma))
    bp_systolic = max(70, min(250, bp_systolic)) # Ésszerű határok

    # Diasztolés becslése a szisztolés alapján
    # Pl. a szisztolés 60-75%-a + kis véletlenszerűség
    diastolic_ratio = random.uniform(0.6, 0.75)
    bp_diastolic = int(bp_systolic * diastolic_ratio + random.gauss(0, 5)) # Kis zaj hozzáadása
    bp_diastolic = max(40, min(bp_systolic - 10, 150)) # Ésszerű határok, és legyen kisebb a szisztolésnál

    # Finomhangolás az állapot alapján (Opcionális, de realisztikusabbá teszi)
    condition = patient_info["condition"]
    if condition == "Pneumonia" and random.random() < 0.1: # 10% eséllyel rosszabb SpO2
        spo2 = max(70, spo2 - random.randint(3, 8))
    elif condition == "Hypertonia" and random.random() < 0.1: # 10% eséllyel magasabb BP
        bp_systolic = min(250, bp_systolic + random.randint(10, 25))
        bp_diastolic = min(150, bp_diastolic + random.randint(5, 15))
    elif condition == "Hypotension" and random.random() < 0.1: # 10% eséllyel alacsonyabb BP
        bp_systolic = max(70, bp_systolic - random.randint(10, 20))
        bp_diastolic = max(40, bp_diastolic - random.randint(5, 10))
    elif condition == "Bradycardia" and random.random() < 0.1: # 10% eséllyel alacsonyabb BP
        bp_systolic = max(70, bp_systolic - random.randint(10, 20))
        bp_diastolic = max(40, bp_diastolic - random.randint(5, 10))
    elif condition == "Tachycardia" and random.random() < 0.1: # 10% eséllyel alacsonyabb BP
        bp_systolic = max(70, bp_systolic - random.randint(10, 20))
        bp_diastolic = max(40, bp_diastolic - random.randint(5, 10))


    return {
        "pulse": pulse,
        "spo2": spo2,
        "bp_systolic": bp_systolic,
        "bp_diastolic": bp_diastolic
    }

# --- Fő Ciklus ---

print("--- Kórházi Szenzor Szimulátor Indítása ---")
print(f"InfluxDB URL: {INFLUXDB_URL}")
print(f"InfluxDB Org: {INFLUXDB_ORG}")
print(f"InfluxDB Bucket: {INFLUXDB_BUCKET}")
print(f"Szimulációs időköz: {SIMULATION_INTERVAL_SECONDS} másodperc")
print("-----------------------------------------")

# Measurement név InfluxDB-ben
measurement_name = "patient_vitals"


# InfluxDB kliens inicializálása
with InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG) as client:
    write_api = client.write_api(write_options=SYNCHRONOUS)
    print("Sikeres kapcsolat az InfluxDB-vel.")

    while True:
        points_to_write = []

        print(f"\n--- Új szimulációs ciklus: {datetime.now()} ---")

        for patient_id, patient_data in PATIENTS.items():
            # Élettani adatok generálása
            vitals = simulate_vitals(patient_data)

            # InfluxDB Point létrehozása
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

            # Adatpontok kötegelt írása InfluxDB-be

        if points_to_write:
            write_api.write(bucket=INFLUXDB_BUCKET, org=INFLUXDB_ORG, record=points_to_write)
            print(f"-> Sikeresen elküldve {len(points_to_write)} adatpont az InfluxDB-be ('{INFLUXDB_BUCKET}' bucket).")

        time.sleep(SIMULATION_INTERVAL_SECONDS)
