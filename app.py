# Inside your app.py
import os
from fastapi import FastAPI, HTTPException
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Real-Time Insider Trading API")
DB_URI = os.getenv("DATABASE_URL")

@app.get("/api/v1/insider-trading/{ticker}")
def get_insider_trading(ticker: str):
    """Connection opens and closes dynamically per request to save memory."""
    try:
        # Open connection ONLY when a user calls the endpoint
        conn = psycopg2.connect(DB_URI)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
            SELECT ticker, insider_name, officer_title, transaction_type, shares, price_per_share, total_value, filed_at 
            FROM insider_transactions 
            WHERE ticker = %s 
            ORDER BY filed_at DESC 
            LIMIT 50;
        """, (ticker.upper(),))
        
        results = cur.fetchall()
        
        # Clean up immediately
        cur.close()
        conn.close()
        
        if not results:
            return {"ticker": ticker.upper(), "message": "No recent insider trades found."}
            
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))