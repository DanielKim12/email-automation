from flask import Flask, render_template, jsonify, request, redirect, url_for, flash
import pandas as pd
from datetime import datetime, timedelta
from main import apply_late_fees, load_credentials

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Required for flash messages

def load_clients():
    try:
        df = pd.read_csv('data/clients.csv')
        
        # Add new columns if they don't exist
        if 'payment_status' not in df.columns:
            df['payment_status'] = 'Pending'
        if 'payment_date' not in df.columns:
            df['payment_date'] = None
        if 'is_late' not in df.columns:
            df['is_late'] = False
        if 'created_at' not in df.columns:
            df['created_at'] = datetime.now()
        
        return df
    except FileNotFoundError:
        # Create an empty dataframe with all required columns
        return pd.DataFrame(columns=[
            'email', 'name', 'cc', 'cost', 'message', 'late_fee', 
            'grace_period', 'duration', 'send_date', 'payment_status', 
            'payment_date', 'is_late', 'created_at'
        ])

def save_clients(df):
    # Ensure all required columns exist
    required_columns = [
        'email', 'name', 'cc', 'cost', 'message', 'late_fee', 
        'grace_period', 'duration', 'send_date', 'payment_status', 
        'payment_date', 'is_late', 'created_at'
    ]
    
    for col in required_columns:
        if col not in df.columns:
            if col == 'payment_status':
                df[col] = 'Pending'
            elif col == 'payment_date':
                df[col] = None
            elif col == 'is_late':
                df[col] = False
            elif col == 'created_at':
                df[col] = datetime.now()
    
    df.to_csv('data/clients.csv', index=False)

def get_invoice_status():
    clients = load_clients()
    if clients.empty:
        return []
    
    status_list = []
    
    for _, client in clients.iterrows():
        base_cost = float(client['cost'])
        grace_period = int(client.get('grace_period', 3))
        occupancy = int(client.get('duration', 1))
        late_fee_amount = float(client.get('late_fee', 50))
        
        # Get the send date from the client data or use the first day of the current month
        send_date_str = client.get('send_date', '1')
        try:
            send_day = int(send_date_str)
            # Create a date for the current month with the specified day
            current_date = datetime.now()
            invoice_sent_date = datetime(current_date.year, current_date.month, min(send_day, 28))
            
            # If the send day has already passed this month, use next month
            if current_date.day > send_day:
                if current_date.month == 12:
                    invoice_sent_date = datetime(current_date.year + 1, 1, min(send_day, 28))
                else:
                    invoice_sent_date = datetime(current_date.year, current_date.month + 1, min(send_day, 28))
        except (ValueError, TypeError):
            # Default to the first day of the current month if there's an error
            invoice_sent_date = datetime(datetime.now().year, datetime.now().month, 1)
        
        final_cost, late_fee_note = apply_late_fees(
            base_cost, grace_period, occupancy, 
            late_fee_amount, invoice_sent_date
        )
        
        grace_deadline = invoice_sent_date + timedelta(days=grace_period, hours=23, minutes=59)
        is_overdue = datetime.now() > grace_deadline
        
        status_list.append({
            'id': client.name,  # Using index as ID
            'client_name': client['name'],
            'email': client['email'],
            'base_cost': base_cost,
            'final_cost': final_cost,
            'grace_period': grace_period,
            'grace_deadline': grace_deadline,
            'is_overdue': is_overdue,
            'late_fee_note': late_fee_note,
            'send_date': send_day,
            'invoice_sent_date': invoice_sent_date,
            'payment_status': client.get('payment_status', 'Pending'),
            'payment_date': client.get('payment_date'),
            'is_late': client.get('is_late', False)
        })
    
    return status_list

@app.route('/')
def dashboard():
    status_list = get_invoice_status()
    return render_template('dashboard.html', invoice_status=status_list)

@app.route('/add_client', methods=['GET', 'POST'])
def add_client():
    if request.method == 'POST':
        clients_df = load_clients()
        new_client = {
            'name': request.form['name'],
            'email': request.form['email'],
            'cost': float(request.form['cost']),
            'grace_period': int(request.form.get('grace_period', 3)),
            'duration': int(request.form.get('duration', 1)),
            'late_fee': float(request.form.get('late_fee', 50)),
            'send_date': int(request.form.get('send_date', 1)),
            'payment_status': 'Pending',
            'payment_date': None,
            'is_late': False,
            'created_at': datetime.now()
        }
        clients_df = pd.concat([clients_df, pd.DataFrame([new_client])], ignore_index=True)
        save_clients(clients_df)
        flash('Client added successfully!', 'success')
        return redirect(url_for('dashboard'))
    return render_template('add_client.html')

@app.route('/edit_client/<client_id>', methods=['GET', 'POST'])
def edit_client(client_id):
    clients_df = load_clients()
    client = clients_df.iloc[int(client_id)]
    
    if request.method == 'POST':
        clients_df.at[int(client_id), 'name'] = request.form['name']
        clients_df.at[int(client_id), 'email'] = request.form['email']
        clients_df.at[int(client_id), 'cost'] = float(request.form['cost'])
        clients_df.at[int(client_id), 'grace_period'] = int(request.form.get('grace_period', 3))
        clients_df.at[int(client_id), 'duration'] = int(request.form.get('duration', 1))
        clients_df.at[int(client_id), 'late_fee'] = float(request.form.get('late_fee', 50))
        clients_df.at[int(client_id), 'send_date'] = int(request.form.get('send_date', 1))
        save_clients(clients_df)
        flash('Client updated successfully!', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('edit_client.html', client=client)

@app.route('/delete_client/<client_id>')
def delete_client(client_id):
    clients_df = load_clients()
    clients_df = clients_df.drop(int(client_id))
    save_clients(clients_df)
    flash('Client deleted successfully!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/view_clients')
def view_clients():
    status_list = get_invoice_status()
    return render_template('view_clients.html', invoice_status=status_list)

@app.route('/toggle_payment_status/<client_id>', methods=['POST'])
def toggle_payment_status(client_id):
    clients_df = load_clients()
    
    # Check if client exists
    if clients_df.empty:
        flash('No clients found in the database')
        return redirect(url_for('view_clients'))
    
    # Find the client by name
    client_matches = clients_df[clients_df['name'] == client_id]
    if client_matches.empty:
        flash(f'Client with ID {client_id} not found')
        return redirect(url_for('view_clients'))
    
    client_index = client_matches.index[0]
    
    # Ensure all required columns exist
    if 'payment_status' not in clients_df.columns:
        clients_df['payment_status'] = 'Pending'
    if 'payment_date' not in clients_df.columns:
        clients_df['payment_date'] = None
    if 'is_late' not in clients_df.columns:
        clients_df['is_late'] = False
    if 'created_at' not in clients_df.columns:
        clients_df['created_at'] = datetime.now()
    
    # Toggle payment status
    current_status = clients_df.at[client_index, 'payment_status']
    if current_status == 'Pending':
        clients_df.at[client_index, 'payment_status'] = 'Paid'
        clients_df.at[client_index, 'payment_date'] = datetime.now()
        
        # Convert grace_period to regular int
        grace_period = int(clients_df.at[client_index, 'grace_period'])
        
        # Convert created_at to datetime if it's a string
        created_at_str = clients_df.at[client_index, 'created_at']
        if isinstance(created_at_str, str):
            try:
                created_at = datetime.strptime(created_at_str, '%Y-%m-%d %H:%M:%S.%f')
            except ValueError:
                try:
                    created_at = datetime.strptime(created_at_str, '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    created_at = datetime.now()
        else:
            created_at = created_at_str
        
        # Check if payment is late
        clients_df.at[client_index, 'is_late'] = datetime.now() > (created_at + timedelta(days=grace_period))
        
        flash('Payment marked as received')
    else:
        clients_df.at[client_index, 'payment_status'] = 'Pending'
        clients_df.at[client_index, 'payment_date'] = None
        clients_df.at[client_index, 'is_late'] = False
        flash('Payment marked as pending')
    
    save_clients(clients_df)
    return redirect(url_for('view_clients'))

@app.route('/api/invoices')
def get_invoices():
    return jsonify(get_invoice_status())

if __name__ == '__main__':
    app.run(debug=True) 