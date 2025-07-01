# main.py
import os
import subprocess

def shutdown_service(event, context):
    print("🚨 Budget threshold triggered. Shutting down COMDEX Cloud Run service...")
    
    service_name = "comdex-api"
    region = "us-central1"
    project_id = os.getenv("GCP_PROJECT", "swift-area-459514-d1")

    # 👇 This command sets traffic to 0%, disabling the service
    command = [
        "gcloud", "run", "services", "update-traffic", service_name,
        "--to-zero",
        "--region", region,
        "--project", project_id
    ]

    try:
        subprocess.run(command, check=True)
        print("✅ Service traffic set to 0% (shutdown successful).")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error shutting down service: {e}")