import pandas as pd
import sqlite3
from pathlib import Path

class DatabaseManager:
    def __init__(self, db_path: str = "manufacturing_data.db"):
        self.db_path = Path(db_path)
        self.init_database()
    
    def init_database(self):
        """Initialize the database with required tables."""
        with sqlite3.connect(self.db_path) as conn:
            # Products table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY,
                    product_name TEXT UNIQUE NOT NULL,
                    partner TEXT NOT NULL,
                    shipment_units INTEGER NOT NULL
                )
            """)
            
            # Packing data table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS packing_data (
                    id INTEGER PRIMARY KEY,
                    product_name TEXT NOT NULL,
                    om_number TEXT NOT NULL,
                    file_name TEXT NOT NULL,
                    part_number TEXT NOT NULL,
                    alternative_part TEXT,
                    quantity REAL NOT NULL,
                    description TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (product_name) REFERENCES products (product_name)
                )
            """)
    
    def get_all_products(self) -> pd.DataFrame:
        """Get all products from the database."""
        with sqlite3.connect(self.db_path) as conn:
            try:
                df = pd.read_sql_query("SELECT * FROM products", conn)
                return df
            except Exception:
                return pd.DataFrame()
    
    def add_product(self, product_name: str, partner: str, shipment_units: int):
        """Add a new product to the database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO products (product_name, partner, shipment_units) VALUES (?, ?, ?)",
                (product_name, partner, shipment_units)
            )
    
    def save_packing_data(self, df: pd.DataFrame, product_name: str, om_number: str, file_name: str):
        """Save packing data to the database."""
        with sqlite3.connect(self.db_path) as conn:
            for _, row in df.iterrows():
                conn.execute(
                    """INSERT INTO packing_data 
                       (product_name, om_number, file_name, part_number, alternative_part, quantity, description)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (product_name, om_number, file_name, row['part_number'], 
                     row.get('alternative_part', ''), row['quantity'], row.get('description', ''))
                )