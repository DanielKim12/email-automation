import csv
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email import policy
import smtplib
from datetime import datetime

# Config (move to global or keep local)
SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 587

def load_credentials(filename="data/user.csv"):
    with open(filename, newline='') as file:
        reader = csv.DictReader(file)
        credentials = next(reader)
        return credentials["email"], credentials["password"]

def apply_late_fees(original_cost, grace_days, occupancy_days, late_fee_amount, invoice_sent_date):
    now = datetime.now()
    grace_deadline = invoice_sent_date + timedelta(days=grace_days, hours=23, minutes=59)
    resend = False
    late_fee_info = ""

    if now > grace_deadline:
        overdue_days = (now - grace_deadline).days
        periods_overdue = overdue_days // occupancy_days
        additional_fees = periods_overdue * late_fee_amount
        resend = overdue_days % occupancy_days == 0

        if periods_overdue > 0:
            late_fee_info = (
                f"\n⚠️ Late fees applied:\n"
                f"- Grace period was {grace_days} days (until {grace_deadline.strftime('%Y-%m-%d %H:%M:%S')})\n"
                f"- Late fees started on {grace_deadline.strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"- Applied every {occupancy_days} day(s)\n"
                f"- Total late fees: ${additional_fees:.2f}\n"
            )
        return float(original_cost), late_fee_info, resend, grace_deadline

    return float(original_cost), "", False, grace_deadline



def clean_hard(text):
    if not text:
        return ""
    return text.replace('\xa0', ' ').encode("utf-8", "ignore").decode("utf-8").strip()


def send_invoice(email, name, cc, cost, message, sender_email, sender_password, late_fee_note, grace_deadline, late_fee_amount, occupancy_days):
    print("=== Starting email construction ===")

    print(">> name:", repr(name))
    print(">> email:", repr(email))
    print(">> cc:", repr(cc))
    print(">> message:", repr(message))
    print(">> late_fee_note:", repr(late_fee_note))

    name = clean_hard(name)
    message = clean_hard(message)
    late_fee_note = clean_hard(late_fee_note)
    body_message = f"Hello {name},\n\n"

    if message:
        body_message += f"{message}\n\n"
        
    full_message = body_message + f"""\
Total due: ${cost:.2f}
Last day before Late fees: {grace_deadline.strftime('%Y-%m-%d %H:%M:%S')}
Late Fee of ${late_fee_amount:.2f} will be applied every {occupancy_days} day(s) from that date.
{late_fee_note}

Thank you,
GUK IL KIM
"""

    print("📩 Email body preview:\n", full_message[:300])

    try:
        # Use policy.SMTPUTF8 to enforce UTF-8 support in headers/body
        msg = MIMEMultipart(policy=policy.SMTPUTF8)
        msg['From'] = sender_email
        msg['To'] = email
        msg['Subject'] = f"Monthly Invoice - {datetime.now().strftime('%B %Y')}"
        if cc:
            msg['Cc'] = cc

        msg.attach(MIMEText(full_message, 'plain', 'utf-8'))

        recipients = [email] + ([cc] if cc else [])

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            print("🔗 Connecting to SMTP...")
            server.starttls()
            print("🔐 TLS started.")
            server.login(sender_email, sender_password)
            print("✅ Logged in.")
            # Send as string, with UTF-8 policy enforced
            server.sendmail(sender_email, recipients, msg.as_string(policy=policy.SMTPUTF8))
            print(f"✅ Invoice sent to {name} at {email}")

    except Exception as e:
        print(f"❌ Failed to send invoice to {email}: {e}")

def clean(text):
    if not text:
        return ""
    return text.replace('\xa0', ' ').encode('utf-8', 'ignore').decode('utf-8').strip()

def process_clients(filename="data/clients.csv"):
    invoice_sent_date = datetime(datetime.now().year, datetime.now().month, 1)
    sender_email, sender_password = load_credentials("data/user.csv")

    with open(filename, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            name = clean(row["name"])
            email = clean(row["email"])
            cc = clean(row["cc"])
            message = clean(row["message"])
            base_cost = float(clean(row["cost"]))
            grace_period = int(clean(row.get("grace_period", 3)))
            occupancy = int(clean(row.get("duration", 1)))
            late_fee_amount = float(clean(row.get("late_fee", 50))) # if late fees not set then $50 default
            final_cost, late_fee_note, resend, grace_deadline = apply_late_fees(
            base_cost, grace_period, occupancy, late_fee_amount, invoice_sent_date
        )

        is_initial_day = datetime.now().day == invoice_sent_date.day
        if is_initial_day or resend:
            send_invoice(
                email, name, cc,
                final_cost, message,
                sender_email, sender_password,
                late_fee_note,
                grace_deadline,
                late_fee_amount,
                occupancy
            )

if __name__ == "__main__":
    process_clients()