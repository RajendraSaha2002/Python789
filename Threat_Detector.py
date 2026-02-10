import pandas as pd
import sqlalchemy
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
import plotly.graph_objects as go

# 1. DB CONFIGURATION
# REPLACE with your actual credentials
db_connection_str = 'postgresql+psycopg2://postgres:varrie75@localhost/postgres'
db_engine = sqlalchemy.create_engine(db_connection_str)

def run_query(sql):
    with db_engine.connect() as conn:
        return pd.read_sql(sql, conn)

# =========================================================
# MODULE 1: ANOMALY DETECTION (Brute Force Identification)
# =========================================================
print("Scanning logs for Brute Force patterns...")

# Rule: Find IPs with > 50 failures in a single hour
sql_brute_force = """
SELECT 
    source_ip, 
    log_hour, 
    failed_attempts,
    total_attempts,
    ROUND((failed_attempts::decimal / NULLIF(total_attempts,0)) * 100, 2) as failure_rate
FROM mv_hourly_threat_summary
WHERE failed_attempts > 50
ORDER BY failed_attempts DESC;
"""
df_threats = run_query(sql_brute_force)

if not df_threats.empty:
    print(f"CRITICAL ALERT: Detected {len(df_threats)} brute force sequences.")
    print(df_threats.head())
else:
    print("No active brute force patterns detected.")

# =========================================================
# MODULE 2: ATTACK FREQUENCY TIMELINE (Seaborn)
# =========================================================
print("Generating Attack Timeline...")

sql_timeline = """
SELECT 
    date_trunc('hour', event_timestamp) as hour_bucket,
    event_type,
    COUNT(*) as count
FROM auth_logs
WHERE event_timestamp > NOW() - INTERVAL '7 days'
GROUP BY 1, 2
ORDER BY 1;
"""
df_timeline = run_query(sql_timeline)

plt.figure(figsize=(14, 6))
sns.lineplot(data=df_timeline, x='hour_bucket', y='count', hue='event_type', linewidth=2.5)
plt.title('7-Day Login Event Volume (Anomaly Detection)', fontsize=14)
plt.axhline(y=150, color='r', linestyle='--', label='Alert Threshold') # Arbitrary threshold
plt.xlabel('Timestamp')
plt.ylabel('Event Count')
plt.legend()
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.show()

# =========================================================
# MODULE 3: SUSPICIOUS IP HEATMAP (Plotly)
# =========================================================
print("Generating IP Threat Matrix...")

# Pivot the threat data to visualize "Hot" hours for specific IPs
pivot_table = df_threats.pivot(index='source_ip', columns='log_hour', values='failed_attempts')

# We use Plotly for this as it handles timestamps in heatmaps better than Seaborn
fig = px.density_heatmap(
    df_threats,
    x="log_hour",
    y="source_ip",
    z="failed_attempts",
    title="Heatmap of Detected Attacks (IP vs Time)",
    labels={"failed_attempts": "Failed Logins"},
    color_continuous_scale="Reds"
)
fig.update_layout(xaxis_title="Time of Attack", yaxis_title="Attacker IP")
fig.show()

# =========================================================
# MODULE 4: THREAT SCORING DISTRIBUTION
# =========================================================
print("Calculating Threat Scores...")

# Advanced SQL: Calculate a dynamic 'Risk Score' based on ratio of failures vs success
sql_scoring = """
SELECT 
    source_ip::text,
    SUM(CASE WHEN event_type='LOGIN_FAILED' THEN 10 ELSE 0 END) +
    SUM(CASE WHEN event_type='LOGIN_SUCCESS' THEN -2 ELSE 0 END) as calculated_risk_score
FROM auth_logs
GROUP BY source_ip
HAVING SUM(CASE WHEN event_type='LOGIN_FAILED' THEN 10 ELSE 0 END) > 0
ORDER BY calculated_risk_score DESC
LIMIT 15;
"""
df_scores = run_query(sql_scoring)

plt.figure(figsize=(12, 6))
sns.barplot(x='calculated_risk_score', y='source_ip', data=df_scores, palette='magma')
plt.title('Top 15 High-Risk IPs (Scoring Model)', fontsize=14)
plt.xlabel('Risk Score (Higher = More Dangerous)')
plt.ylabel('IP Address')
plt.tight_layout()
plt.show()

print("Security Scan Complete.")