import os
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

# --- Configuration ---
# Best practice: Use environment variables for sensitive info
# Set these in your environment or replace the default values below
INFLUXDB_URL = os.getenv("INFLUXDB_URL", "http://localhost:8086") # e.g., "http://localhost:8086" or "https://us-west-2-1.aws.cloud2.influxdata.com"
INFLUXDB_TOKEN = os.getenv("INFLUXDB_TOKEN", "mytoken")      # Replace with your InfluxDB API Token
INFLUXDB_ORG = os.getenv("INFLUXDB_ORG", "myorg")          # Replace with your InfluxDB Organization name/ID
INFLUXDB_BUCKET = os.getenv("INFLUXDB_BUCKET", "patients")    # Replace with your InfluxDB Bucket name

# --- Patient Data ---
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
        "condition": "Hypotension", # Corrected typo from "Hypotensio"
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

# --- InfluxDB Client and Writing ---

# Define the measurement name
measurement_name = "patient_metadata"

# Create a list to hold the data points
points = []

# Iterate through the patient data and create InfluxDB Points
for patient_id, data in PATIENTS.items():
    point = Point(measurement_name) \
        .tag("patient_id", patient_id) \
        .tag("patient_name", data["name"]) \
        .tag("condition", data["condition"]) \
        .field("bp_min", data["bp_range"][0]) \
        .field("bp_max", data["bp_range"][1]) \
        .field("spo2_min", data["spo2_range"][0]) \
        .field("spo2_max", data["spo2_range"][1]) \
        .field("pulse_min", data["pulse_range"][0]) \
        .field("pulse_max", data["pulse_range"][1]) \
        # Alternatively, omit .time() to use the server's current time upon ingestion

    points.append(point)

# Instantiate the InfluxDB client
# Use 'with' statement for automatic resource cleanup
try:
    with InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG) as client:
        # Instantiate the Write API
        # SYNCHRONOUS mode is simpler for scripts, waits for confirmation/error
        write_api = client.write_api(write_options=SYNCHRONOUS)

        print(f"Connecting to InfluxDB: {INFLUXDB_URL}, Org: {INFLUXDB_ORG}, Bucket: {INFLUXDB_BUCKET}")
        print(f"Attempting to write {len(points)} data points for patient metadata...")

        # Write the data points to the bucket
        write_api.write(bucket=INFLUXDB_BUCKET, org=INFLUXDB_ORG, record=points)

        print(f"Successfully wrote {len(points)} patient metadata points to bucket '{INFLUXDB_BUCKET}'.")

except Exception as e:
    print(f"Error writing to InfluxDB: {e}")
    print("Please check your InfluxDB URL, Token, Org, Bucket, and network connectivity.")