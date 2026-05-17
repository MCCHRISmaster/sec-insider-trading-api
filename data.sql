-- Table to store the overarching filing information
CREATE TABLE sec_filings (
    filing_id SERIAL PRIMARY KEY,
    accession_number VARCHAR(50) UNIQUE NOT NULL, -- The SEC's unique ID for this specific document
    filed_at TIMESTAMP WITH TIME ZONE NOT NULL,    -- When the SEC received it
    sec_url TEXT NOT NULL                          -- Link to the original raw filing
);

-- Table to store the actual insider transactions
CREATE TABLE insider_transactions (
    transaction_id SERIAL PRIMARY KEY,
    filing_id INT REFERENCES sec_filings(filing_id) ON DELETE CASCADE,
    
    -- Company (Issuer) Info
    ticker VARCHAR(10) NOT NULL,
    company_name VARCHAR(255) NOT NULL,
    company_cik VARCHAR(10) NOT NULL,              -- SEC's Central Index Key for the company
    
    -- Insider Info
    insider_name VARCHAR(255) NOT NULL,
    insider_cik VARCHAR(10) NOT NULL,              -- SEC's Central Index Key for the person
    is_director BOOLEAN DEFAULT FALSE,
    is_officer BOOLEAN DEFAULT FALSE,
    is_ten_percent_owner BOOLEAN DEFAULT FALSE,
    officer_title VARCHAR(100),
    
    -- Transaction Info
    transaction_date DATE NOT NULL,
    transaction_code VARCHAR(2) NOT NULL,          -- 'P' for Purchase, 'S' for Sale
    is_acquisition BOOLEAN NOT NULL,               -- True if they bought/acquired, False if they sold
    shares_amount NUMERIC(15, 4) NOT NULL,
    price_per_share NUMERIC(10, 4) NOT NULL,
    total_value NUMERIC(15, 2) NOT NULL,           -- shares * price
    shares_owned_after_transaction NUMERIC(15, 4),
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes to make your API lightning fast when users search by ticker
CREATE INDEX idx_transactions_ticker ON insider_transactions(ticker);
CREATE INDEX idx_transactions_date ON insider_transactions(transaction_date DESC);