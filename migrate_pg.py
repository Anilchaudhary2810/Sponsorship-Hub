import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def migrate():
    db_url = os.getenv("DATABASE_URL")
    if not db_url or not db_url.startswith("postgresql"):
        print("Not a postgres connection or no DATABASE_URL found.")
        return

    try:
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()
        
        # Check if old column exists
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='deals' AND column_name='stripe_payment_intent_id';
        """)
        
        if cur.fetchone():
            print("Found 'stripe_payment_intent_id'. Renaming to 'razorpay_payment_id'...")
            cur.execute("ALTER TABLE deals RENAME COLUMN stripe_payment_intent_id TO razorpay_payment_id;")
            conn.commit()
            print("Successfully renamed column.")
        else:
            print("'stripe_payment_intent_id' not found or already renamed.")
            
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error during migration: {e}")

if __name__ == "__main__":
    migrate()
