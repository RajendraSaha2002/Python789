import pandas as pd
import sqlalchemy
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
import plotly.io as pio

# 1. DATABASE CONNECTION
# Format: postgresql+psycopg2://username:password@host:port/database_name
# REPLACE with your actual credentials
db_connection_str = 'postgresql+psycopg2://postgres:varrie75@localhost/postgres'
db_connection = sqlalchemy.create_engine(db_connection_str)

def fetch_data(query):
    """Helper to execute SQL and return a DataFrame"""
    try:
        with db_connection.connect() as conn:
            return pd.read_sql(query, conn)
    except Exception as e:
        print(f"Error executing query: {e}")
        return pd.DataFrame()

# ==========================================
# ANALYSIS 1: Revenue Growth Trends (Matplotlib)
# ==========================================
print("Generating Revenue Trend Analysis...")
sql_revenue = """
SELECT summary_date, total_revenue 
FROM daily_revenue_summary 
ORDER BY summary_date ASC;
"""
df_revenue = fetch_data(sql_revenue)

plt.figure(figsize=(12, 6))
# Moving average for smoother trend line
df_revenue['MA_7'] = df_revenue['total_revenue'].rolling(window=7).mean()

plt.plot(df_revenue['summary_date'], df_revenue['total_revenue'], alpha=0.3, color='gray', label='Daily Revenue')
plt.plot(df_revenue['summary_date'], df_revenue['MA_7'], color='blue', linewidth=2, label='7-Day Moving Avg')

plt.title('Enterprise Revenue Growth Trends (Rolling Average)', fontsize=14)
plt.xlabel('Date')
plt.ylabel('Revenue ($)')
plt.legend()
plt.grid(True, linestyle='--', alpha=0.6)
plt.tight_layout()
plt.show()

# ==========================================
# ANALYSIS 2: Product Profit Heatmap (Seaborn)
# ==========================================
print("Generating Product Profitability Heatmap...")
sql_heatmap = """
SELECT 
    p.category,
    p.name as product_name,
    SUM(oi.total_price - (p.cost_price * oi.quantity)) as total_profit
FROM order_items oi
JOIN products p ON oi.product_id = p.product_id
GROUP BY p.category, p.name;
"""
df_profit = fetch_data(sql_heatmap)

# Pivot for heatmap structure
heatmap_data = df_profit.pivot(index="product_name", columns="category", values="total_profit")

plt.figure(figsize=(10, 6))
sns.heatmap(heatmap_data, annot=True, fmt=".0f", cmap="YlGnBu", linewidths=.5)
plt.title('Profit Heatmap: Product vs Category', fontsize=14)
plt.tight_layout()
plt.show()

# ==========================================
# ANALYSIS 3: Customer Lifetime Value (CLV) - (Plotly Offline)
# ==========================================
print("Generating CLV Interactive Chart...")
sql_clv = """
SELECT 
    c.name,
    c.segment,
    SUM(oi.total_price) as lifetime_value,
    COUNT(DISTINCT o.order_id) as order_count
FROM customers c
JOIN orders o ON c.customer_id = o.customer_id
JOIN order_items oi ON o.order_id = oi.order_id
GROUP BY c.name, c.segment
HAVING SUM(oi.total_price) > 0
ORDER BY lifetime_value DESC
LIMIT 20;
"""
df_clv = fetch_data(sql_clv)

fig = px.scatter(
    df_clv,
    x="order_count",
    y="lifetime_value",
    size="lifetime_value",
    color="segment",
    hover_name="name",
    title="Top 20 Customers by CLV (Lifetime Value)",
    labels={"lifetime_value": "Total Revenue ($)", "order_count": "Number of Orders"},
    size_max=60
)

# Render inside PyCharm or Browser
fig.show()

print("Analytics Run Complete.")