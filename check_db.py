from backend.database import engine
from sqlalchemy import inspect

def check_schema():
    inspector = inspect(engine)
    columns = inspector.get_columns('deals')
    print("Columns in 'deals' table:")
    for column in columns:
        print(f"- {column['name']}")

if __name__ == "__main__":
    try:
        check_schema()
    except Exception as e:
        print(f"Error checking schema: {e}")
