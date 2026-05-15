import sqlite3
import pandas as pd
from pathlib import Path

class DatabaseManager:
    def __init__(self, db_path: str = "database/manufacturing.db"):
        self.db_path = db_path
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        """ساخت جداول با اضافه شدن فیلد om_number"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS products (
                    product_name TEXT PRIMARY KEY,
                    partner TEXT,
                    shipment_units INTEGER
                )
            """)
            # اضافه شدن om_number به اینجا
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS packing_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_name TEXT,
                    om_number TEXT,
                    part_number TEXT,
                    alternative_part TEXT,
                    qty_raw REAL,
                    file_name TEXT,
                    FOREIGN KEY (product_name) REFERENCES products (product_name)
                )
            """)
            conn.commit()

    def add_product(self, name, partner, units):
        with self._get_connection() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO products (product_name, partner, shipment_units) VALUES (?, ?, ?)",
                (name, partner, units)
            )

    def get_all_products(self):
        with self._get_connection() as conn:
            return pd.read_sql("SELECT * FROM products", conn)

    def save_packing_data(self, df: pd.DataFrame, product_name: str, om_number: str, file_name: str):
        """ذخیره داده‌های پکینگ همراه با شماره OM"""
        with self._get_connection() as conn:
            for _, row in df.iterrows():
                conn.execute("""
                    INSERT INTO packing_history 
                    (product_name, om_number, part_number, alternative_part, qty_raw, file_name)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (product_name, om_number, row['part_number'], row['alternative_part'], row['quantity'], file_name))

    def get_aggregated_packing(self, product_name: str):
        """تجمیع کل سوابق برای یک محصول"""
        query = """
            SELECT part_number, alternative_part, SUM(qty_raw) as total_qty
            FROM packing_history
            WHERE product_name = ?
            GROUP BY part_number, alternative_part
        """
        with self._get_connection() as conn:
            return pd.read_sql(query, conn, params=(product_name,))

    def get_history_by_om(self, om_number: str):
        """فقط اطلاعات مربوط به یک محموله خاص"""
        query = "SELECT * FROM packing_history WHERE om_number = ?"
        with self._get_connection() as conn:
            return pd.read_sql(query, conn, params=(om_number,))