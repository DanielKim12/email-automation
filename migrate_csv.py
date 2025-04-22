import pandas as pd
from datetime import datetime
from app import app, db, User, Client
from werkzeug.security import generate_password_hash

def migrate_data():
    with app.app_context():
        # Create tables if they don't exist
        db.create_all()
        
        try:
            # Read CSV files
            clients_df = pd.read_csv('data/clients.csv')
            user_df = pd.read_csv('data/user.csv')
            
            # Create default user if not exists
            user_email = user_df['email'].iloc[0]
            user = User.query.filter_by(email=user_email).first()
            if not user:
                user = User(
                    email=user_email,
                    smtp_username=user_df['email'].iloc[0],
                    smtp_password=user_df['password'].iloc[0]
                )
                user.set_password('default_password')  # Set a default password
                db.session.add(user)
                db.session.commit()
            
            # Migrate each client
            for _, row in clients_df.iterrows():
                # Check if client already exists
                existing_client = Client.query.filter_by(
                    email=row['email'],
                    name=row['name'],
                    user_id=user.id
                ).first()
                
                if not existing_client:
                    # Convert date strings to datetime objects
                    created_at = datetime.strptime(row['created_at'], '%Y-%m-%d %H:%M:%S.%f') if pd.notna(row['created_at']) else datetime.utcnow()
                    payment_date = datetime.strptime(row['payment_date'], '%Y-%m-%d %H:%M:%S.%f') if pd.notna(row['payment_date']) else None
                    
                    client = Client(
                        email=row['email'],
                        name=row['name'],
                        cc=row['cc'] if pd.notna(row['cc']) else None,
                        cost=float(row['cost']),
                        message=row['message'] if pd.notna(row['message']) else None,
                        late_fee=float(row['late_fee']) if pd.notna(row['late_fee']) else 50.0,
                        grace_period=int(row['grace_period']) if pd.notna(row['grace_period']) else 3,
                        duration=int(row['duration']) if pd.notna(row['duration']) else 1,
                        send_day=int(row['send_date']) if pd.notna(row['send_date']) else 1,
                        send_hour=9,  # Default to 9 AM
                        user_id=user.id,
                        created_at=created_at,
                        payment_status=row['payment_status'] if pd.notna(row['payment_status']) else 'Pending',
                        payment_date=payment_date,
                        is_late=bool(row['is_late']) if pd.notna(row['is_late']) else False
                    )
                    db.session.add(client)
            
            db.session.commit()
            print("Migration completed successfully!")
            
        except Exception as e:
            print(f"Error during migration: {str(e)}")
            db.session.rollback()

if __name__ == '__main__':
    migrate_data() 