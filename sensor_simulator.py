import random
import time
import logging
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS


# Konfiguráció
INFLUXDB_URL = "http://localhost:8086"
INFLUXDB_TOKEN = "mytoken"
INFLUXDB_ORG = "myorg"
INFLUXDB_BUCKET = "hospital"

# Betegprofilok
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
        "condition": "Hypotensio",
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

# Naplózás beállítása
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('patient_monitor.log'),
        logging.StreamHandler()
    ]
)


class PatientMonitor:
    def __init__(self):
        self.client = InfluxDBClient(
            url=INFLUXDB_URL,
            token=INFLUXDB_TOKEN,
            org=INFLUXDB_ORG
        )
        self.write_api = self.client.write_api(write_options=SYNCHRONOUS)

    def _generate_vitals(self, patient_id):
        """Valósághű vitalis jelek generálása"""
        profile = PATIENTS[patient_id]

        # Vérnyomás számítás
        systolic = random.randint(*profile["bp_range"])
        diastolic = int(systolic * 0.6 + random.uniform(-5, 5))

        # Oxigénszint szimuláció
        spo2 = random.uniform(*profile["spo2_range"])
        if random.random() < 0.1 and profile["condition"] == "Pneumonia":
            spo2 = max(70, spo2 - random.uniform(5, 15))

        # Pulzus generálás
        pulse = random.randint(*profile["pulse_range"])
        if profile["condition"] == "Tachycardia" and random.random() < 0.3:
            pulse += random.randint(10, 20)
        elif profile["condition"] == "Bradycardia" and random.random() < 0.3:
            pulse -= random.randint(5, 15)

        # Adatvalidáció
        vitals = {
            "systolic": max(70, min(250, systolic)),
            "diastolic": max(50, min(150, diastolic)),
            "spo2": round(max(70, min(100, spo2)), 1),
            "pulse": max(30, min(200, pulse)),
            "condition": profile["condition"]
        }

        return vitals

    def _create_influx_point(self, patient_id, vitals):
        """InfluxDB pont létrehozása"""
        return (
            Point("patient_vitals")
            .tag("patient_id", patient_id)
            .tag("patient_name", PATIENTS[patient_id]["name"])
            .tag("condition", vitals["condition"])
            .field("systolic", vitals["systolic"])
            .field("diastolic", vitals["diastolic"])
            .field("spo2", vitals["spo2"])
            .field("pulse", vitals["pulse"])
        )

    def send_data(self):
        """Adatküldés ciklus"""
        try:
            while True:
                for patient_id in PATIENTS:
                    vitals = self._generate_vitals(patient_id)
                    point = self._create_influx_point(patient_id, vitals)

                    self.write_api.write(
                        bucket=INFLUXDB_BUCKET,
                        record=point
                    )

                    logging.info(
                        f"{patient_id} ({PATIENTS[patient_id]['name']}) - "
                        f"SYS: {vitals['systolic']}, DIA: {vitals['diastolic']}, "
                        f"SpO2: {vitals['spo2']}%, Pulse: {vitals['pulse']} bpm"
                    )

                time.sleep(10)

        except KeyboardInterrupt:
            logging.info("Monitoring leállítva")
        except Exception as e:
            logging.error(f"Hiba történt: {str(e)}")
        finally:
            self.client.close()


if __name__ == "__main__":
    monitor = PatientMonitor()
    logging.info("Páciens monitorozás elindult...")
    monitor.send_data()
