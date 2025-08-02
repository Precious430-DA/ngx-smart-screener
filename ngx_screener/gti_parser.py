import os
import pandas as pd
import fitz  # PyMuPDF
from datetime import datetime
import re

PDF_FOLDER = r"C:\Users\ofoye\ngx_screener\data\daily_pdfs"
MASTER_CSV = r"C:\Users\ofoye\ngx_screener\data\ngx daily price list.csv"

def extract_text_from_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text("text")
    return text

def parse_pdf_text(text):
    lines = [line.strip() for line in text.strip().split("\n") if line.strip()]
    data = []
    
    # Find the header section
    header_keywords = ["COMPANY", "PCLOSE", "OPEN", "HIGH", "LOW", "CLOSE", "CHANGE", "%CHANGE", "TRADES", "VOLUME", "VALUE"]
    
    # Find where the data starts (after all headers are found)
    data_start_idx = 0
    headers_found = []
    
    for i, line in enumerate(lines):
        if line.upper() in header_keywords:
            headers_found.append(line.upper())
            if len(headers_found) == len(header_keywords):
                data_start_idx = i + 1
                break
    
    if data_start_idx == 0:
        print("❌ Headers not found in expected format")
        return pd.DataFrame()
    
    print(f"📊 Data starts at line {data_start_idx + 1}")
    
    # Parse data in chunks of 11 (one for each column)
    i = data_start_idx
    skipped_companies = []
    
    while i < len(lines) - 10:  # Need at least 11 lines for a complete record
        try:
            # Extract 11 consecutive values
            company = lines[i].strip()
            
            # Skip if this looks like a header, summary, footer, or document info
            skip_patterns = ["COMPANY", "ASI", "GAINERS", "LOSERS", "TOTAL", "GTI SECURITIES", 
                           "Price List", "Tinubu Street", "P.O. BOX", "Tel:", "PCLOSE", 
                           "OPEN", "HIGH", "LOW", "CLOSE", "CHANGE", "%CHANGE", "TRADES", 
                           "VOLUME", "VALUE"]
            
            if any(pattern in company.upper() for pattern in skip_patterns):
                i += 1
                continue
            
            # Check if we have enough lines left
            if i + 10 >= len(lines):
                break
            
            # Validate that next 10 lines look like numeric data
            # Skip if any of the next few lines contain obvious text patterns
            next_lines = lines[i + 1:i + 11]
            if any(any(pattern in line.upper() for pattern in skip_patterns) for line in next_lines[:3]):
                print(f"⚠️ Skipping {company} - detected non-numeric data in following lines")
                skipped_companies.append(company)
                i += 1
                continue
                
            pclose = float(lines[i + 1].replace(",", ""))
            open_price = float(lines[i + 2].replace(",", ""))
            high = float(lines[i + 3].replace(",", ""))
            low = float(lines[i + 4].replace(",", ""))
            close = float(lines[i + 5].replace(",", ""))
            change = float(lines[i + 6].replace(",", ""))
            pct_change = float(lines[i + 7].replace(",", ""))
            trades = int(lines[i + 8].replace(",", ""))
            volume = int(lines[i + 9].replace(",", ""))
            value = float(lines[i + 10].replace(",", "").replace("₦", ""))
            
            data.append({
                "COMPANY": company,
                "PCLOSE": pclose,
                "OPEN": open_price,
                "HIGH": high,
                "LOW": low,
                "CLOSE": close,
                "CHANGE": change,
                "%CHANGE": pct_change,
                "TRADES": trades,
                "VOLUME": volume,
                "VALUE": value
            })
            
            print(f"✅ Parsed: {company}")
            i += 11  # Move to next record
            
        except (ValueError, IndexError) as e:
            # Try to find next company name to resync
            company_name = lines[i] if i < len(lines) else 'EOF'
            print(f"⚠️ Skip starting at line {i + 1}: {company_name[:20]}... — {e}")
            
            # Look ahead to find next potential company (all caps, no numbers)
            found_next = False
            for j in range(i + 1, min(i + 12, len(lines))):
                potential_company = lines[j].strip()
                # Check if this looks like a company name (alphabetic, possibly with numbers at end)
                if (len(potential_company) > 2 and 
                    potential_company.replace('REIT', '').replace('ETF', '').isalpha() and
                    not any(pattern in potential_company.upper() for pattern in skip_patterns)):
                    print(f"🔄 Resyncing at line {j + 1}: {potential_company}")
                    i = j
                    found_next = True
                    break
            
            if not found_next:
                i += 1
            continue
    
    if skipped_companies:
        print(f"\n⚠️ Skipped companies due to data alignment issues: {', '.join(skipped_companies)}")
    
    return pd.DataFrame(data)

def update_master_csv():
    if os.path.exists(MASTER_CSV):
        print("📄 Master CSV found — loading existing data.")
        master_df = pd.read_csv(MASTER_CSV)
    else:
        print("📄 Creating new master CSV")
        master_df = pd.DataFrame()

    processed_dates = master_df.get("DATE", pd.Series()).dropna().unique()

    print("📂 Looking in:", PDF_FOLDER)
    for filename in os.listdir(PDF_FOLDER):
        if not filename.lower().endswith(".pdf"):
            continue

        pdf_path = os.path.join(PDF_FOLDER, filename)
        print(f"\n📦 Processing: {filename}")

        text = extract_text_from_pdf(pdf_path)
        df = parse_pdf_text(text)

        if df.empty:
            print(f"❌ No data extracted from {filename}")
            print("🔍 Showing preview of extracted text:")
            for i, line in enumerate(text.strip().splitlines()):
                print(f"{i+1:02d}: {line}")
                if i >= 29:
                    break
            continue

        # Extract date from filename
        date_str = filename.replace("GTI Daily Price List- ", "").replace(".pdf", "").strip()
        try:
            date_obj = datetime.strptime(date_str, "%A_%B %dth %Y")
        except:
            try:
                date_obj = datetime.strptime(date_str, "%A_%B %d %Y")
            except:
                print(f"❌ Skipping: {filename} — Date parse error")
                continue

        date_fmt = date_obj.strftime("%Y-%m-%d")
        if date_fmt in processed_dates:
            print(f"✅ Already added: {date_fmt}")
            continue

        df["DATE"] = date_fmt
        master_df = pd.concat([master_df, df], ignore_index=True)
        print(f"✅ Added: {filename} with {len(df)} records")

    master_df.to_csv(MASTER_CSV, index=False)
    print(f"\n✅ Master CSV updated! Total records: {len(master_df)}")

if __name__ == "__main__":
    update_master_csv()