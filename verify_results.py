import json
import os
import sqlite3

db_path = os.path.join("data", "northwind.sqlite")

def load_jsonl(filepath):
    data = {}
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    item = json.loads(line)
                    data[item['id']] = item
    return data

def run_ground_truth_sql(q_id):
    """Returns the ground truth result for a given question ID by running manual SQL."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        sql = None
        result = "N/A (Not SQL)"
        
        if q_id == "hybrid_top_category_qty_summer_1997":
            # Summer 1997 (June) Top Category by Qty
            sql = """
                SELECT c.CategoryName, SUM(oi.Quantity) as TotalQty
                FROM Orders o
                JOIN "Order Details" oi ON o.OrderID = oi.OrderID
                JOIN Products p ON oi.ProductID = p.ProductID
                JOIN Categories c ON p.CategoryID = c.CategoryID
                WHERE strftime('%Y-%m-%d', o.OrderDate) BETWEEN '1997-06-01' AND '1997-06-30'
                GROUP BY c.CategoryName
                ORDER BY TotalQty DESC
                LIMIT 1;
            """
        elif q_id == "hybrid_aov_winter_1997":
            # Winter 1997 (Dec) AOV for Dairy/Confections
            sql = """
                SELECT (SUM(oi.UnitPrice * oi.Quantity * (1 - oi.Discount)) / COUNT(DISTINCT o.OrderID)) as AOV
                FROM Orders o
                JOIN "Order Details" oi ON o.OrderID = oi.OrderID
                JOIN Products p ON oi.ProductID = p.ProductID
                JOIN Categories c ON p.CategoryID = c.CategoryID
                WHERE strftime('%Y-%m-%d', o.OrderDate) BETWEEN '1997-12-01' AND '1997-12-31'
                AND c.CategoryName IN ('Dairy', 'Confections');
            """
        elif q_id == "sql_top3_products_by_revenue_alltime":
            # Top 3 Products Revenue All-Time
            sql = """
                SELECT p.ProductName, SUM(oi.UnitPrice * oi.Quantity * (1 - oi.Discount)) as Revenue
                FROM "Order Details" oi
                JOIN Products p ON oi.ProductID = p.ProductID
                GROUP BY p.ProductName
                ORDER BY Revenue DESC
                LIMIT 3;
            """
        elif q_id == "hybrid_revenue_beverages_summer_1997":
            # Summer 1997 (June) Beverages Revenue
            sql = """
                SELECT SUM(oi.UnitPrice * oi.Quantity * (1 - oi.Discount)) as Revenue
                FROM Orders o
                JOIN "Order Details" oi ON o.OrderID = oi.OrderID
                JOIN Products p ON oi.ProductID = p.ProductID
                JOIN Categories c ON p.CategoryID = c.CategoryID
                WHERE strftime('%Y-%m-%d', o.OrderDate) BETWEEN '1997-06-01' AND '1997-06-30'
                AND c.CategoryName = 'Beverages';
            """
        elif q_id == "rag_policy_beverages_return_days":
            return "14 (From Docs)"

        if sql:
            cursor.execute(sql)
            rows = cursor.fetchall()
            if not rows:
                result = "No Data Found"
            elif rows[0][0] is None:
                result = "None/Zero"
            else:
                # Format complex results
                if len(rows) > 1:
                    result = str(rows) # Multiple rows
                elif len(rows[0]) > 1:
                    result = str(rows[0]) # Multiple cols
                else:
                    result = str(rows[0][0]) # Single value
                    
        conn.close()
        return result
    except Exception as e:
        return f"Error: {str(e)}"

def verify_results():
    questions_path = "sample_questions_hybrid_eval.jsonl"
    outputs_path = "outputs_hybrid.jsonl"

    questions = load_jsonl(questions_path)
    outputs = load_jsonl(outputs_path)

    print(f"{'ID':<40} | {'Ground Truth (Manual SQL)':<30} | {'Agent Answer'}")
    print("-" * 100)

    for q_id, q_data in questions.items():
        ground_truth = str(run_ground_truth_sql(q_id))
        
        if q_id in outputs:
            agent_ans = str(outputs[q_id].get('final_answer', 'N/A'))
            if len(agent_ans) > 40:
                agent_ans = agent_ans[:37] + "..."
        else:
            agent_ans = "[NO OUTPUT]"
            
        # Truncate GT for display
        if len(ground_truth) > 30:
            ground_truth = ground_truth[:27] + "..."
            
        print(f"{q_id:<40} | {ground_truth:<30} | {agent_ans}")

if __name__ == "__main__":
    verify_results()
