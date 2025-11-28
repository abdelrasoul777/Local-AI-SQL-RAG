import sqlite3

class SQLiteTool:
    def __init__(self, db_path):
        self.db_path = db_path
        self._init_views()
        
    def _init_views(self):
        """Create lowercase compatibility views as required."""
        views = [
            "CREATE VIEW IF NOT EXISTS orders AS SELECT * FROM Orders;",
            "CREATE VIEW IF NOT EXISTS order_items AS SELECT * FROM \"Order Details\";",
            "CREATE VIEW IF NOT EXISTS products AS SELECT * FROM Products;",
            "CREATE VIEW IF NOT EXISTS customers AS SELECT * FROM Customers;"
        ]
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            for view in views:
                cursor.execute(view)
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Warning: Failed to initialize views: {e}")
        
    def execute(self, query):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(query)
            if query.strip().upper().startswith("SELECT") or query.strip().upper().startswith("PRAGMA"):
                result = cursor.fetchall()
                conn.close()
                return result
            else:
                conn.commit()
                conn.close()
                return "Executed successfully"
        except Exception as e:
            return f"Error: {str(e)}"
    
    def get_schema(self):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            schema = {}
            for table in tables:
                table_name = table[0]
                cursor.execute(f"PRAGMA table_info('{table_name}')")
                columns = cursor.fetchall()
                schema[table_name] = [col[1] for col in columns]
            conn.close()
            return schema
        except Exception as e:
            return f"Error: {str(e)}"
    
    def get_schema_detailed(self):
        """Get detailed schema with types for SQL generation."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Use lowercase views for simpler SQL generation
            allowed_tables = ['orders', 'order_items', 'products', 'customers', 'categories', 'suppliers']
            
            schema_text = "Database Schema (Use these lowercase views):\n\n"
            
            for table_name in allowed_tables:
                try:
                    cursor.execute(f"PRAGMA table_info('{table_name}')")
                    columns = cursor.fetchall()
                    
                    if columns:
                        schema_text += f"View: {table_name}\n"
                        schema_text += "Columns:\n"
                        for col in columns:
                            col_name = col[1]
                            col_type = col[2]
                            schema_text += f"  - {col_name} ({col_type})\n"
                        schema_text += "\n"
                except:
                    continue
            
            # Add common patterns
            schema_text += "Common Query Patterns:\n"
            schema_text += "- Revenue: SUM(oi.UnitPrice * oi.Quantity * (1 - oi.Discount))\n"
            schema_text += "- Cost of Goods Sold (COGS): 0.7 * oi.UnitPrice\n"
            schema_text += "- Join pattern: orders o JOIN order_items oi ON o.OrderID = oi.OrderID JOIN products p ON oi.ProductID = p.ProductID\n"
            schema_text += "- Date filtering: WHERE strftime('%Y-%m-%d', o.OrderDate) BETWEEN 'YYYY-MM-DD' AND 'YYYY-MM-DD'\n"
            
            conn.close()
            return schema_text
        except Exception as e:
            return f"Error: {str(e)}"

if __name__ == "__main__":
    # Simple test
    import os
    # Start from current file location, go up 3 levels (agent/tools/ -> agent/ -> root/) then to data/
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    db_path = os.path.join(base_dir, "data", "northwind.sqlite")
    
    print(f"Testing DB connection at: {db_path}")
    tool = SQLiteTool(db_path)
    
    print("\n--- Schema ---")
    schema = tool.get_schema()
    if isinstance(schema, dict):
        for table, cols in list(schema.items())[:3]: # Print first 3 tables
            print(f"{table}: {cols}")
    else:
        print(schema)
        
    print("\n--- Test Query (Products) ---")
    print(tool.execute("SELECT * FROM Products LIMIT 1"))
