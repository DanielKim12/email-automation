import csv
import os
import sys
from pathlib import Path

# UTF-safe
def clean(text):
    if not text:
        return ""
    return text.replace('\xa0', ' ').encode('utf-8', 'ignore').decode('utf-8').strip()

def collect_client_info():
    print("\n📝 Add a New Client Entry:\n")
    email = clean(input("Client email: "))
    name = clean(input("Client full name: "))
    cc = clean(input("CC email (optional): "))
    cost = clean(input("Monthly fees: ").lower())
    message = clean(input("Message to client (optional): "))
    late_fee = clean(input("Late fees for this client: ").lower())
    grace_period = clean(input("How many days for late fees to be applied?: ").lower())
    duration = clean(input("How often do you want late fees to be applied? (every day: 1, 2, 3 .. 7): ").lower())
    send_day = input("Which day of the month to send invoice? (1–28): ").strip()
    send_hour = input("What hour (0–23) should the invoice be sent? (e.g., 9 for 9AM): ").strip()

    return {
        "email": email,
        "name": name,
        "cc": cc,
        "cost": cost,
        "message": message,
        "late_fee": late_fee,
        "grace_period": grace_period,
        "duration": duration,
        "send_day": send_day,
        "send_hour": send_hour
    }

def add_client_to_database(client, filename="clients.csv"):
    file_exists = os.path.isfile(filename)
    with open(filename, mode='a', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=[
            "email", "name", "cc", "cost", "message",
            "late_fee", "grace_period", "duration",
            "send_day", "send_hour"
        ])
        if not file_exists:
            writer.writeheader()
        writer.writerow(client)
    print(f"\n✅ Client '{client['name']}' added to {filename}")

def cron_job(email, send_day, send_hour):
    # Get paths dynamically
    python_path = sys.executable  # current Python interpreter
    script_path = str(Path(__file__).resolve().parent / "main.py")  # main.py in same folder

    # Create cron line
    cron_line = f"{int(send_hour)} 9 {int(send_day)} * * {python_path} {script_path} --email {email}"

    current_cron = os.popen("crontab -l").read()
    if cron_line in current_cron:
        print("⚠️ Cron job already exists.")
        return

    updated_cron = current_cron.strip() + f"\n{cron_line}\n"

    with open("temp_cron.txt", "w") as f:
        f.write(updated_cron)

    os.system("crontab temp_cron.txt")
    os.remove("temp_cron.txt")
    print(f"✅ Cron job added for {email} on day {send_day} at {send_hour}:00.")

if __name__ == "__main__":
    client = collect_client_info()
    add_client_to_database(client)
    cron_job(client["email"], client["send_day"], client["send_hour"])