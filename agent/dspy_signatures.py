import dspy

class Router(dspy.Signature):
    """
    Decide the best approach to answer the question.
    
    Choose 'rag' if the question asks about:
    - Product policies (return windows, warranties)
    - Marketing campaigns/calendars (event dates, focus categories)
    - KPI definitions (formulas, calculations)
    - Catalog information (category mappings)
    
    Choose 'sql' if the question asks about:
    - Actual data from the database (orders, revenue, quantities)
    - Aggregations (sum, count, average) of transactional data
    - Specific order or product details
    
    Choose 'hybrid' if the question needs BOTH:
    - Document constraints (like date ranges from marketing calendar)
    - AND database queries (like revenue during that period)
    
    Examples:
    - "What is the return window for Beverages?" -> rag
    - "What was the total revenue in June 1997?" -> sql
    - "What was revenue for Summer Beverages 1997?" -> hybrid (needs campaign dates from docs + revenue from DB)
    """
    question = dspy.InputField()
    decision = dspy.OutputField(desc="Output ONLY one word: 'rag', 'sql', or 'hybrid'")

class GenerateSQL(dspy.Signature):
    """
    Generate a VALID SQLite query. Output ONLY the SQL.
    
    Allowed Views (LOWERCASE ONLY):
    - orders (o): OrderID, OrderDate
    - order_items (oi): OrderID, ProductID, UnitPrice, Quantity, Discount
    - products (p): ProductID, ProductName, CategoryID, UnitPrice
    - categories (c): CategoryID, CategoryName
    
    Rules:
    - Revenue = SUM(oi.UnitPrice * oi.Quantity * (1 - oi.Discount))
    - Cost = 0.7 * oi.UnitPrice
    - Date format: strftime('%Y-%m-%d', o.OrderDate) BETWEEN '...' AND '...'
    - JOIN: orders o JOIN order_items oi ON o.OrderID = oi.OrderID JOIN products p ON oi.ProductID = p.ProductID JOIN categories c ON p.CategoryID = c.CategoryID
    """
    question = dspy.InputField()
    schema_info = dspy.InputField()
    constraints = dspy.InputField()
    sql_query = dspy.OutputField(desc="SQL query starting with SELECT")

class ExtractConstraints(dspy.Signature):
    """
    Extract specific constraints from documents that are needed for SQL queries.
    Look for: date ranges, product categories, KPI formulas, filters.
    """
    question = dspy.InputField()
    documents = dspy.InputField(desc="Retrieved document chunks")
    constraints = dspy.OutputField(desc="Extracted constraints in structured format (e.g., dates: 1997-06-01 to 1997-06-30, categories: Beverages, Condiments)")

class SynthesizeAnswer(dspy.Signature):
    """
    Generate a final answer matching the exact format_hint.
    For 'float', output only a number like 12345.67
    For 'int', output only an integer like 42
    For 'list', output a JSON array
    """
    question = dspy.InputField()
    context = dspy.InputField(desc="Retrieved documents or SQL results")
    format_hint = dspy.InputField(desc="Expected output format type (int, float, list, etc.)")
    
    final_answer = dspy.OutputField(desc="ONLY the answer value, matching the format_hint exactly. No text, no units.")
    explanation = dspy.OutputField(desc="Short explanation <= 2 sentences")
    confidence = dspy.OutputField(desc="Float between 0.0 and 1.0")
