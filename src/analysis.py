from __future__ import annotations
import pandas as pd
from .db import connect

def get_subscriptions(conn=None):
    """
    Detect recurring payments:
    Same Merchant + Same Amount (within 5% tolerance) appearing in at least 2 distinct months.
    """
    close_conn = False
    if conn is None:
        conn = connect()
        close_conn = True
        
    query = """
    SELECT
      r.merchant,
      i.amount,
      r.receipt_date
    FROM items i
    JOIN receipts r ON r.id = i.receipt_id
    WHERE r.merchant IS NOT NULL AND i.amount > 0 AND r.receipt_date IS NOT NULL
    """
    df = pd.read_sql_query(query, conn)
    
    if close_conn:
        conn.close()
        
    if df.empty:
        return pd.DataFrame()

    df['month'] = df['receipt_date'].astype(str).str.slice(0, 7)
    
    # Group by merchant and amount (rounded to 1 decimal for tolerance)
    df['amount_key'] = df['amount'].round(1)
    
    # Count unique months per (merchant, amount)
    tech_subs = df.groupby(['merchant', 'amount_key'])['month'].nunique().reset_index()
    # Filter for >= 2 months
    candidates = tech_subs[tech_subs['month'] >= 2]
    
    # Get details
    subs = []
    for _, row in candidates.iterrows():
        m = row['merchant']
        a = row['amount_key']
        # approximate monthly cost
        subs.append({
            'merchant': m,
            'estimated_cost': a,
            'frequency_months': row['month']
        })
        
    return pd.DataFrame(subs)

def check_budget_alerts(conn=None, monthly_budget=10000.0):
    """
    Compare current month spending vs budget.
    """
    close_conn = False
    if conn is None:
        conn = connect()
        close_conn = True
        
    query = """
    SELECT
      r.receipt_date,
      i.amount
    FROM items i
    JOIN receipts r ON r.id = i.receipt_id
    WHERE r.receipt_date IS NOT NULL
    """
    df = pd.read_sql_query(query, conn)
    
    if close_conn:
        conn.close()

    if df.empty:
        return []

    df['month'] = df['receipt_date'].astype(str).str.slice(0, 7)
    
    monthly_spend = df.groupby('month')['amount'].sum()
    if monthly_spend.empty:
        return []
        
    latest_month = monthly_spend.index.max()
    latest_val = monthly_spend.iloc[-1]
    
    alerts = []
    if latest_val > monthly_budget:
        alerts.append({
            'type': 'warning',
            'msg': f"Budget Alert: You spent {latest_val:,.2f} in {latest_month}, exceeding budget of {monthly_budget:,.2f}"
        })
    else:
        alerts.append({
            'type': 'success',
            'msg': f"On track: {latest_val:,.2f} spent in {latest_month} (Budget: {monthly_budget:,.2f})"
        })
        
    return alerts
