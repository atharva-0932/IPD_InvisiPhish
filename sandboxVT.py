import requests
import time
import os

virustotal_api_key = os.getenv('VIRUSTOTAL_API_KEY')  # Now reads from .env file
FILE_PATH = "sample_file.pdf" #Add file path for testing code

if not virustotal_api_key:
    print("[-] VirusTotal API key not found in environment variables")
    exit(1)

url = "https://www.virustotal.com/api/v3/files"
headers = {
  "x-apikey": virustotal_api_key
}

print("[*] Uploading file to VirusTotal...")
with open(FILE_PATH, "rb") as f:
  files = {
    "file": (FILE_PATH, f)
  }
  response = requests.post(url, headers=headers, files=files)

if response.status_code != 200:
  print("[-] Upload failed:", response.status_code, response.text)
  exit(1)

response_json = response.json()
analysis_id = response_json.get("data", {}).get("id")

if not analysis_id:
  print("[-] Failed to get analysis ID.")
  exit(1)

print(f"[*] File submitted. Analysis ID: {analysis_id}")

print("[*] Waiting for analysis to complete...")
result_url = f"https://www.virustotal.com/api/v3/analyses/{analysis_id}"
MAX_WAIT_TIME = 150
POLL_INTERVAL = 10
elapsed_time = 0

while elapsed_time < MAX_WAIT_TIME:
  time.sleep(POLL_INTERVAL)
  elapsed_time += POLL_INTERVAL

  result_response = requests.get(result_url, headers=headers)
  result_data = result_response.json()
  status = result_data.get("data", {}).get("attributes", {}).get("status")

  print(f"[*] Status: {status} (Waited {elapsed_time}s)")

  if status == "completed":
    print("[+] Analysis Complete!")
    stats = result_data["data"]["attributes"]["stats"]
    print(f"""
      Detection Summary:
      Harmless   : {stats.get("harmless")}
      Malicious  : {stats.get("malicious")}
      Suspicious : {stats.get("suspicious")}
      Undetected : {stats.get("undetected")}
    """)
    break
else:
  print("[-] Analysis could not be completed within time limit")
