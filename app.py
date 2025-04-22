import os
import csv
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default_secret_key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///clients.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Initialize scheduler with SQLAlchemy job store
jobstores = {
    'default': SQLAlchemyJobStore(url=app.config['SQLALCHEMY_DATABASE_URI'])
}
scheduler = BackgroundScheduler(jobstores=jobstores)
scheduler.start()

# Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    smtp_server = db.Column(db.String(120), default='smtp.gmail.com')
    smtp_port = db.Column(db.Integer, default=587)
    smtp_username = db.Column(db.String(120))
    smtp_password = db.Column(db.String(120))
    clients = db.relationship('Client', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    cc = db.Column(db.String(120))
    cost = db.Column(db.Float, nullable=False)
    message = db.Column(db.Text)
    late_fee = db.Column(db.Float, default=50.0)
    grace_period = db.Column(db.Integer, default=3)
    duration = db.Column(db.Integer, default=1)
    send_day = db.Column(db.Integer, nullable=False)
    send_hour = db.Column(db.Integer, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_paid = db.Column(db.Boolean, default=False)  # Changed from payment_status string to boolean
    payment_date = db.Column(db.DateTime)
    is_late = db.Column(db.Boolean, default=False)

class Revenue(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    payment_date = db.Column(db.DateTime, default=datetime.utcnow)
    client = db.relationship('Client', backref='revenues')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        smtp_server = request.form.get('smtp_server', 'smtp.gmail.com')
        smtp_port = int(request.form.get('smtp_port', 587))
        smtp_username = request.form.get('smtp_username')
        smtp_password = request.form.get('smtp_password')

        if User.query.filter_by(email=email).first():
            flash('Email already registered')
            return redirect(url_for('register'))

        user = User(
            email=email,
            smtp_server=smtp_server,
            smtp_port=smtp_port,
            smtp_username=smtp_username,
            smtp_password=smtp_password
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash('Registration successful')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('dashboard'))
        
        flash('Invalid email or password')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    # 🔍 DEBUG: Verify user context and client count
    print(f"[DEBUG] Logged in as: {current_user.email} (ID: {current_user.id})")

    clients = Client.query.filter_by(user_id=current_user.id).all()
    print(f"[DEBUG] Found {len(clients)} clients for this user")

    invoice_status = []
    total_revenue = 0

    for client in clients:
        # Calculate if payment is late
        days_since_creation = (datetime.utcnow() - client.created_at).days
        is_late = days_since_creation > client.grace_period and not client.is_paid

        # Calculate final cost (including late fee if applicable)
        final_cost = client.cost
        if is_late:
            final_cost *= 1.1  # 10% late fee

        # Only add to revenue if payment is marked as paid
        if client.is_paid:
            total_revenue += final_cost

        invoice_status.append({
            'id': client.id,
            'name': client.name,
            'email': client.email,
            'base_cost': client.cost,
            'final_cost': final_cost,
            'send_date': client.send_day,
            'grace_period': client.grace_period,
            'is_paid': client.is_paid,
            'is_late': is_late
        })

    return render_template('dashboard.html', 
                           invoice_status=invoice_status,
                           total_revenue=total_revenue)

import traceback

@app.route('/add_client', methods=['GET', 'POST'])
@login_required
def add_client():
    if request.method == 'POST':
        try:
            existing_client = Client.query.filter_by(email=request.form.get('email'), user_id=current_user.id).first()
            if existing_client:
                flash("A client with this email already exists.")
                return redirect(url_for('add_client'))
            # Validate required fields
            required_fields = ['email', 'name', 'cost', 'late_fee', 'grace_period', 'duration', 'send_day']
            for field in required_fields:
                value = request.form.get(field)
                if not value:
                    flash(f"{field} is required.")
                    print(f"[DEBUG] Missing field: {field}")
                    return redirect(url_for('add_client'))

            client = Client(
                email=request.form.get('email'),
                name=request.form.get('name'),
                cc=request.form.get('cc'),
                cost=float(request.form.get('cost')),
                message=request.form.get('message'),
                late_fee=float(request.form.get('late_fee')),
                grace_period=int(request.form.get('grace_period')),
                duration=int(request.form.get('duration')),
                send_day=int(request.form.get('send_day')),
                send_hour=9,
                user_id=current_user.id
            )

            db.session.add(client)
            db.session.commit()

            print(f"[DEBUG] ✅ Client '{client.name}' added with ID {client.id}")
            schedule_email_job(client)
            flash("Client added successfully")
            return redirect(url_for('dashboard'))

        except Exception as e:
            print("[ERROR] Exception occurred while adding client")
            traceback.print_exc()  
            db.session.rollback()
            flash("Something went wrong. Check server logs.")
            return redirect(url_for('add_client'))

    return render_template('add_client.html')

@app.route('/view_clients')
@login_required
def view_clients():
    # Force a fresh query from the database
    db.session.expire_all()
    clients = Client.query.filter_by(user_id=current_user.id).all()
    invoice_status = [get_invoice_status_for_client(client) for client in clients]
    print(f"View clients - Found {len(clients)} clients")
    for client in clients:
        print(f"Client: {client.name}, Status: {client.is_paid}")
    return render_template('view_clients.html', invoice_status=invoice_status)

@app.route('/edit_client/<int:client_id>', methods=['GET', 'POST'])
@login_required
def edit_client(client_id):
    client = Client.query.get_or_404(client_id)

    if client.user_id != current_user.id:
        flash('You do not have permission to edit this client')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        # Update fields safely
        client.email = request.form.get('email')
        client.name = request.form.get('name')
        client.cc = request.form.get('cc')
        client.cost = float(request.form.get('cost'))
        client.message = request.form.get('message')
        client.late_fee = float(request.form.get('late_fee'))
        client.grace_period = int(request.form.get('grace_period'))
        client.duration = int(request.form.get('duration'))

        send_day_raw = request.form.get('send_day')
        if not send_day_raw:
            flash("Send day is missing.")
            return redirect(url_for('edit_client', client_id=client.id))
        client.send_day = int(send_day_raw)

        client.send_hour = 9  # Default to 9AM PST

        db.session.commit()

        # Reschedule the job
        reschedule_email_job(client)

        flash('Client updated successfully')
        return redirect(url_for('view_clients'))

    return render_template('edit_client.html', client=client)


@app.route('/delete_client/<int:client_id>')
@login_required
def delete_client(client_id):
    client = Client.query.get_or_404(client_id)
    
    if client.user_id != current_user.id:
        flash('You do not have permission to delete this client')
        return redirect(url_for('dashboard'))
    
    # Remove the scheduled job
    job_id = f"email_job_{client.id}"
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)
    
    db.session.delete(client)
    db.session.commit()
    
    flash('Client deleted successfully')
    return redirect(url_for('view_clients'))

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
        current_user.smtp_server = request.form.get('smtp_server')
        current_user.smtp_port = int(request.form.get('smtp_port'))
        current_user.smtp_username = request.form.get('smtp_username')
        
        # Only update password if provided
        new_password = request.form.get('smtp_password')
        if new_password:
            current_user.smtp_password = new_password
        
        db.session.commit()
        flash('Settings updated successfully')
        return redirect(url_for('dashboard'))
    
    return render_template('settings.html')

@app.route('/toggle_payment_status/<int:client_id>', methods=['POST'])
@login_required
def toggle_payment_status(client_id):
    try:
        print(f"Toggle payment status called for client_id: {client_id}")
        
        # Get the client from the database
        client = Client.query.get_or_404(client_id)
        print(f"Found client: {client.name}, current is_paid: {client.is_paid}")
        
        # Check permissions
        if client.user_id != current_user.id:
            print(f"Permission denied: client.user_id={client.user_id}, current_user.id={current_user.id}")
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': 'Permission denied'})
            flash('You do not have permission to update this client')
            return redirect(url_for('dashboard'))
        
        # Toggle payment status
        client.is_paid = not client.is_paid
        client.payment_date = datetime.utcnow() if client.is_paid else None
        client.is_late = datetime.utcnow() > (client.created_at + timedelta(days=client.grace_period))
        
        print(f"Updated client: is_paid={client.is_paid}, payment_date={client.payment_date}, is_late={client.is_late}")
        
        # Create revenue entry if marked as paid
        if client.is_paid:
            revenue = Revenue(
                amount=client.cost,
                client_id=client.id,
                user_id=current_user.id
            )
            db.session.add(revenue)
            flash('Payment marked as received')
        else:
            flash('Payment marked as pending')
        
        # Save changes to database
        db.session.commit()
        print("Changes committed to database")
        
        # Return JSON response for AJAX requests
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'success': True,
                'is_paid': client.is_paid,
                'message': 'Payment marked as received' if client.is_paid else 'Payment marked as pending'
            })
        
    except Exception as e:
        print(f"Error in toggle_payment_status: {str(e)}")
        db.session.rollback()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': str(e)})
        flash('Error updating payment status')
    
    return redirect(url_for('view_clients'))

# Helper functions
def init_scheduler():
    """Initialize the scheduler with all existing client jobs"""
    with app.app_context():
        clients = Client.query.all()
        for client in clients:
            schedule_email_job(client)

# Call this after creating all tables
@app.before_first_request
def setup_scheduler():
    init_scheduler()

    # monthly reset job
    scheduler.add_job(
        reset_client_payment_statuses,
        trigger='cron',
        hour=0,  # Midnight UTC
        id='monthly_payment_reset',
        replace_existing=True
    )

def schedule_email_job(client):
    """Schedule or update the email job for a client"""
    job_id = f"email_job_{client.id}"
    
    # Remove existing job if it exists
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)
    
    # Create a new job
    scheduler.add_job(
        send_invoice_email,
        # CronTrigger(minute="*"),  # every minute for testing
        CronTrigger(day=client.send_day, hour=9),
        args=[client.id],
        id=job_id,
        replace_existing=True
    )

def reschedule_email_job(client):
    schedule_email_job(client)

def send_invoice_email(client_id):
    client = Client.query.get(client_id)
    message = client.message or "No custom message provided."

    if not client:
        return
    
    user = User.query.get(client.user_id)
    if not user:
        return
    
    # Import the send_invoice function from main.py
    from main import send_invoice
    
    # Calculate the invoice date and apply late fees
    invoice_sent_date = datetime(datetime.now().year, datetime.now().month, 1)
    grace_deadline = invoice_sent_date + timedelta(days=client.grace_period, hours=23, minutes=59)
    
    # Send the invoice
    send_invoice(
        client.email, 
        client.name, 
        client.cc,
        client.cost, 
        client.message,
        user.smtp_username, 
        user.smtp_password,
        "",  # late_fee_note will be calculated in the function
        grace_deadline,
        client.late_fee,
        client.duration
    )

def apply_late_fees(cost, grace_period, duration, late_fee, invoice_sent_date):
    """
    Calculate the final cost and late fee note based on whether the invoice is overdue.
    """
    now = datetime.now()
    grace_deadline = invoice_sent_date + timedelta(days=grace_period)

    if now > grace_deadline:
        # Calculate how many times the late fee should be applied
        days_late = (now - grace_deadline).days
        fee_multiplier = (days_late // duration) + 1
        additional_fee = late_fee * fee_multiplier
        final_cost = cost + additional_fee
        late_fee_note = f"{fee_multiplier}x late fee applied (${additional_fee:.2f})"
    else:
        final_cost = cost
        late_fee_note = "No late fee"

    return final_cost, late_fee_note


def reset_client_payment_statuses():
    with app.app_context():
        today = datetime.utcnow()
        clients = Client.query.all()
        for client in clients:
            # Reset only if the invoice send day matches today
            if today.day == client.send_day:
                client.is_paid = False
                client.payment_date = None
                db.session.commit()



def get_invoice_status_for_client(client):
    # Calculate invoice sent date
    current_date = datetime.now()
    invoice_sent_date = datetime(current_date.year, current_date.month, min(client.send_day, 28))
    
    # If the send day has already passed this month, use next month
    if current_date.day > client.send_day:
        if current_date.month == 12:
            invoice_sent_date = datetime(current_date.year + 1, 1, min(client.send_day, 28))
        else:
            invoice_sent_date = datetime(current_date.year, current_date.month + 1, min(client.send_day, 28))
    
    # Calculate final cost and late fees
    final_cost, late_fee_note = apply_late_fees(
        client.cost, client.grace_period, client.duration, 
        client.late_fee, invoice_sent_date
    )
    
    # Calculate grace deadline and overdue status
    grace_deadline = invoice_sent_date + timedelta(days=client.grace_period, hours=23, minutes=59)
    is_overdue = datetime.now() > grace_deadline
    
    return {
        'id': client.id,
        'client_name': client.name,
        'email': client.email,
        'base_cost': client.cost,
        'final_cost': final_cost,
        'grace_period': client.grace_period,
        'grace_deadline': grace_deadline,
        'is_overdue': is_overdue,
        'late_fee_note': late_fee_note,
        'send_date': client.send_day,
        'invoice_sent_date': invoice_sent_date,
        'is_paid': client.is_paid,
        'payment_date': client.payment_date,
        'is_late': client.is_late
    }

# Create database tables
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True) 