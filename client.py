import csv
import os

# utf-safe
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

    return {
        "email": email,
        "name": name,
        "cc": cc,
        "cost": cost,
        "message": message,
        "late_fee": late_fee,
        "grace_period": grace_period,
        "duration": duration
    }

def add_client_to_database(filename="clients.csv"):
    client = collect_client_info()

    file_exists = os.path.isfile(filename)
    with open(filename, mode='a', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=[
            "email", "name", "cc", "cost", "message", "late_fee", "grace_period", "duration"
        ])
        if not file_exists:
            writer.writeheader()
        writer.writerow(client)

    print(f"\n✅ Client '{client['name']}' added to {filename}")

if __name__ == "__main__":
    add_client_to_database()