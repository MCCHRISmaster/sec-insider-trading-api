import os
import requests
import xml.etree.ElementTree as ET
import time
import re
import psycopg2
from dotenv import load_dotenv

# Load the keys from the hidden .env file into your system's memory
load_dotenv()

HEADERS = {"User-Agent": "YourCompanyName contact@yourdomain.com"}
SEC_RSS_URL = "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=4&count=100&output=atom"
# Inside tracker.py
DB_URI = os.getenv("DATABASE_URL")
# If using Neon, swap it out: DB_URI = "your_neon_connection_string_here"

def init_db():
    """Creates the tables if they don't exist yet."""
    conn = psycopg2.connect(DB_URI)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS insider_transactions (
            transaction_id SERIAL PRIMARY KEY,
            accession_number VARCHAR(50) UNIQUE NOT NULL,
            ticker VARCHAR(10) NOT NULL,
            insider_name VARCHAR(255) NOT NULL,
            officer_title VARCHAR(100),
            transaction_type VARCHAR(10) NOT NULL,
            shares NUMERIC NOT NULL,
            price_per_share NUMERIC NOT NULL,
            total_value NUMERIC NOT NULL,
            filed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_ticker ON insider_transactions(ticker);
    """)
    conn.commit()
    cur.close()
    conn.close()

def fetch_latest_filings():
    response = requests.get(SEC_RSS_URL, headers=HEADERS)
    if response.status_code != 200: return []
    root = ET.fromstring(response.content)
    namespaces = {'atom': 'http://www.w3.org/2005/Atom'}
    
    filings = []
    for entry in root.findall('atom:entry', namespaces):
        title = entry.find('atom:title', namespaces).text
        html_url = entry.find('atom:link', namespaces).attrib['href']
        if "Form 4 " in title:
            xml_url = html_url.replace(".txt", "/form4.xml").replace("-index.html", "/form4.xml")
            accession_match = re.search(r'data/\d+/(.+?)/', xml_url)
            accession_number = accession_match.group(1) if accession_match else html_url
            filings.append({"accession_number": accession_number, "url": xml_url})
    return filings

def parse_form_4_xml(xml_url):
    time.sleep(0.15) # Stay SEC compliant
    response = requests.get(xml_url, headers=HEADERS)
    if response.status_code != 200: return None
    try:
        root = ET.fromstring(response.content)
        ticker = root.find('.//issuerTradingSymbol').text
        insider_name = root.find('.//rptOwnerName').text
        officer_title_node = root.find('.//officerTitle')
        officer_title = officer_title_node.text if officer_title_node is not None else "Insider"
        
        transaction = root.find('.//nonDerivativeTransaction')
        if transaction is None: return None
            
        t_code = transaction.find('.//transactionCoding/transactionCode').text
        if t_code not in ['P', 'S']: return None # Only market buys and sells
        
        acquire_dispose = transaction.find('.//transactionAmounts/transactionAcquiredDisposedCode/value').text
        shares = float(transaction.find('.//transactionAmounts/transactionShares/value').text)
        price_node = transaction.find('.//transactionAmounts/transactionPricePerShare/value')
        price = float(price_node.text) if price_node is not None else 0.0
        
        return {
            "ticker": ticker,
            "insider_name": insider_name,
            "officer_title": officer_title,
            "transaction_type": "BUY" if acquire_dispose == 'A' else "SELL",
            "shares": shares,
            "price_per_share": price,
            "total_value": shares * price
        }
    except Exception:
        return None

def save_to_db(accession_number, data):
    try:
        conn = psycopg2.connect(DB_URI)
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO insider_transactions 
            (accession_number, ticker, insider_name, officer_title, transaction_type, shares, price_per_share, total_value)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (accession_number) DO NOTHING;
        """, (accession_number, data['ticker'], data['insider_name'], data['officer_title'], data['transaction_type'], data['shares'], data['price_per_share'], data['total_value']))
        conn.commit()
        cur.close()
        conn.close()
        print(f" Saved {data['ticker']} trade to Database!")
    except Exception as e:
        print(f"Database error: {e}")

if __name__ == "__main__":
    init_db()
    print("SEC Tracker engine running...")
    processed_filings = set()
    
    while True:
        filings = fetch_latest_filings()
        for filing in filings:
            if filing["accession_number"] in processed_filings: continue
            
            data = parse_form_4_xml(filing["url"])
            if data:
                print(f" Found: {data['insider_name']} traded {data['ticker']}")
                save_to_db(filing["accession_number"], data)
                
            processed_filings.add(filing["accession_number"])
        time.sleep(30)