# 📧 Email Invoice Automation with Late Fee Handling

This is a Python-based email automation system that sends monthly invoices to clients and automatically applies late fees based on configurable grace periods and penalty frequencies.

> Designed for freelancers, consultants, and small teams to automate recurring client billing and improve payment tracking.

---

## ⚙️ Features

- Auto-sends invoices on the **1st of each month**
- Late fees applied after configurable grace period
- Penalty amount and frequency customizable per client
- Sends emails via **Gmail SMTP** with app password
- UTF-8 safe (handles special characters and encoding issues)
- Clean CSV-based client + credential storage

---

## 🧩 Project Structure
```
email-automation/
├── main.py           # Core logic: reads client list, applies late fees, sends emails
├── client.py         # Interactive script to add new clients into clients.csv
├── clients.csv       # Stores client info (email, name, fees, message, etc.)
├── user.csv          # Stores your own email + Gmail app password
└── README.md         # You're reading it!
```

---

## 🔁 Flow

1. You add a client using:
   ```bash
   python3 client.py
   ```

2. `clients.csv` is updated with:
   - Email, name, message, monthly fee
   - Grace period, late fee amount, and recurrence

3. On the 1st of every month (via cron or manual run), this command is triggered:
   ```bash
   python3 main.py
   ```

4. It sends a personalized invoice and applies late fees if payment is overdue.

---

## 🛠️ Setup Instructions

1. **Install dependencies (Python 3 required)**:  
   No external libraries needed — all standard libraries.

2. **Set up Gmail App Password**:
   - Visit https://myaccount.google.com/apppasswords
   - Generate a 16-char password for "Mail"
   - Save it in `user.csv` like so:

     ```
     email,password
     your_email@gmail.com,app_password_here
     ```

3. **Add a client**:
   ```bash
   python3 client.py
   ```

4. **Run the invoice job manually (or via cron)**:
   ```bash
   python3 main.py
   ```

---

## 🧪 Testing

To test sending now via cron, add this to `crontab -e`:
```bash
* * * * * /usr/bin/python3 /full/path/to/main.py

# 0 minutes, 9 am, 1st day of the month, every month, day of the week (5 stars)
0 9 1 * * /usr/bin/python3 /full/path/to/main.py
```

To send manually:
```bash
python3 main.py
```

---

## 🧭 To Do (Planned Features)

- ✅ Attach PDF invoice
- ✅ Dashboard to track payments
- ✅ Stripe or PayPal integration
- ✅ Client payment status
- ✅ Auto-reminder before due date

---

## 🧑‍💻 Author

**Guk Il Kim**  
[Email me](mailto:kimgukil2@gmail.com)
