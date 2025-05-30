from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
import pandas as pd
import os
import tempfile
import io
import json
import re
from datetime import datetime
from typing import Dict

router = APIRouter()


# ========= FILTERING FOR EXCEL ROUTE =========

def apply_filters(df, filters):
    ops = {
        "=": lambda col, val: col == val,
        "!=": lambda col, val: col != val,
        ">": lambda col, val: col > val,
        "<": lambda col, val: col < val,
        ">=": lambda col, val: col >= val,
        "<=": lambda col, val: col <= val,
        "contains": lambda col, val: col.astype(str).str.contains(str(val), case=False, na=False),
        "not_contains": lambda col, val: ~col.astype(str).str.contains(str(val), case=False, na=False),
    }

    for rule in filters:
        col = rule.get("column")
        op = rule.get("operation")
        val = rule.get("value")

        if not all([col, op, val]):
            continue

        if op not in ops:
            raise ValueError(f"Unsupported operation: {op}")

        if col not in df.columns:
            raise ValueError(f"Column '{col}' does not exist")

        try:
            if pd.api.types.is_numeric_dtype(df[col]):
                val = float(val)
            elif pd.api.types.is_datetime64_any_dtype(df[col]):
                val = pd.to_datetime(val)
        except (ValueError, TypeError):
            pass

        df = df[ops[op](df[col], val)]

    return df


@router.post("/convert-txt")
async def convert_txt_to_excel(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        decoded = contents.decode("utf-8")
        df = pd.read_csv(io.StringIO(decoded), sep=r'\s{2,}', engine='python')

        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
            output_path = tmp.name
            df.to_excel(output_path, index=False)

        return FileResponse(output_path, filename="converted_file.xlsx")

    except Exception as e:
        print(f"❌ Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to convert TXT to Excel.")


@router.post("/process-excel")
async def process_excel_file(file: UploadFile = File(...), filters: str = Form("[]")):
    try:
        contents = await file.read()
        df = pd.read_excel(io.BytesIO(contents))

        filter_rules = json.loads(filters)
        if filter_rules:
            df = apply_filters(df, filter_rules)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
            output_path = tmp.name
            df.to_excel(output_path, index=False)

        return FileResponse(output_path, filename=f"processed_{file.filename}")

    except Exception as e:
        raise HTTPException(500, f"Failed to process Excel file: {str(e)}")


# ========= VISA REPORT PARSING ROUTE =========
def parse_visa_report(content: str) -> Dict:
    data = {
        'ReportID': '',
        'ReportingFor': '',
        'RollupTo': '',
        'FundsXferEntity': '',
        'ProcDate': '',
        'ReportDate': '',
        'SettlementCurrency': '',
    }

    def parse_amount(amount_str):
        if not amount_str or str(amount_str).strip() in ('', '0.00'):
            return 0.0
        amount_str = str(amount_str).replace(',', '').strip()
        if 'CR' in amount_str:
            return float(amount_str.replace('CR', ''))
        elif 'DB' in amount_str:
            return -float(amount_str.replace('DB', ''))
        try:
            return float(amount_str)
        except ValueError:
            return 0.0 # Return 0.0 if parsing fails


    # Parse headers (unchanged)
    headers = {
        'ReportID': r'REPORT ID:\s+(VSS-\d+)',
        'ReportingFor': r'REPORTING FOR:\s+(.+?)\s+BIN',
        'RollupTo': r'ROLLUP TO:\s+(.+?)\s+BA',
        'FundsXferEntity': r'FUNDS XFER ENTITY:\s+(.+?)\n',
        'ProcDate': r'PROC DATE:\s+(\d{2}[A-Za-z]{3}\d{2})',
        'ReportDate': r'REPORT DATE:\s+(\d{2}[A-Za-z]{3}\d{2})',
        'SettlementCurrency': r'SETTLEMENT CURRENCY:\s+([A-Z]{3})'
    }
    for field, pattern in headers.items():
        if match := re.search(pattern, content):
            data[field] = match.group(1).strip()

    # Define section-specific column parsing logic
    sections = [
        {
            'name': 'Interchange',
            'pattern': r'INTERCHANGE VALUE(.*?)REIMBURSEMENT FEES',
            'line_types': ['ACQUIRER', 'ISSUER', 'OTHER'],
            'columns': ['Count', 'CreditAmount', 'DebitAmount', 'TotalAmount'],
            'total_pattern': r'TOTAL INTERCHANGE VALUE\s+([\d,]+)\s+([\d,]+\.\d{2}[A-Z]{0,2})?\s+([\d,]+\.\d{2}[A-Z]{0,2})?\s+([\d,]+\.\d{2}[A-Z]{0,2})?'
        },
        {
            'name': 'Reimbursement',
            'pattern': r'REIMBURSEMENT FEES(.*?)VISA CHARGES',
            'line_types': ['ACQUIRER', 'ISSUER', 'OTHER'],
            'columns': ['CreditAmount', 'DebitAmount', 'TotalAmount'],
            'total_pattern': r'TOTAL REIMBURSEMENT FEES\s+([\d,]+\.\d{2}[A-Z]{0,2})?\s+([\d,]+\.\d{2}[A-Z]{0,2})?\s+([\d,]+\.\d{2}[A-Z]{0,2})?'
        },
        {
            'name': 'VisaCharges',
            'pattern': r'VISA CHARGES(.*?)TOTAL VISA CHARGES',
            'line_types': ['ACQUIRER', 'ISSUER', 'OTHER'],
            'columns': ['CreditAmount', 'DebitAmount', 'TotalAmount'],
            'total_pattern': r'TOTAL VISA CHARGES\s+([\d,]+\.\d{2}[A-Z]{0,2})?\s+([\d,]+\.\d{2}[A-Z]{0,2})?\s+([\d,]+\.\d{2}[A-Z]{0,2})?'
        }
    ]

    for section in sections:
        if section_match := re.search(section['pattern'], content, re.DOTALL):
            section_content = section_match.group(1)
            # print(f"\n--- {section['name']} Section Content ---\n{section_content}\n--------------------------") # Debugging line
            
            for line_type in section['line_types']:
                # The key is to match the exact spacing and potential optionality of fields
                if section['name'] == 'Interchange':
                    # Pattern for Interchange which includes Count (always present) and then 3 amounts (optional)
                    # Using non-greedy matches for amounts to prevent issues if there's text after
                    pattern = rf'TOTAL {line_type}\s+([\d,]+)\s+([\d,]+\.\d{{2}}[A-Z]{{0,2}})?\s+([\d,]+\.\d{{2}}[A-Z]{{0,2}})?\s+([\d,]+\.\d{{2}}[A-Z]{{0,2}})?'
                else:
                    # Pattern for Reimbursement and VisaCharges without Count, just 3 amounts (optional)
                    pattern = rf'TOTAL {line_type}\s+([\d,]+\.\d{{2}}[A-Z]{{0-2}})?\s+([\d,]+\.\d{{2}}[A-Z]{{0-2}})?\s+([\d,]+\.\d{{2}}[A-Z]{{0-2}})?'
                
                if match := re.search(pattern, section_content):
                    # print(f"  Matched {line_type} in {section['name']}: {match.groups()}") # Debugging line
                    start_idx = 1 
                    if section['name'] == 'Interchange':
                        data[f"{section['name']}_{line_type}_Count"] = int(match.group(start_idx)) if match.group(start_idx) else 0
                        start_idx += 1
                    
                    data[f"{section['name']}_{line_type}_CreditAmount"] = parse_amount(match.group(start_idx))
                    data[f"{section['name']}_{line_type}_DebitAmount"] = parse_amount(match.group(start_idx + 1))
                    data[f"{section['name']}_{line_type}_TotalAmount"] = parse_amount(match.group(start_idx + 2))
                # else:
                    # print(f"  No match for {line_type} in {section['name']}") # Debugging line

            # Parse section total
            if total_match := re.search(section['total_pattern'], content):
                # print(f"  Matched Total for {section['name']}: {total_match.groups()}") # Debugging line
                start_idx = 1
                if section['name'] == 'Interchange':
                    data[f"{section['name']}_Total_Count"] = int(total_match.group(start_idx)) if total_match.group(start_idx) else 0
                    start_idx += 1
                
                data[f"{section['name']}_Total_CreditAmount"] = parse_amount(total_match.group(start_idx))
                data[f"{section['name']}_Total_DebitAmount"] = parse_amount(total_match.group(start_idx + 1))
                data[f"{section['name']}_Total_TotalAmount"] = parse_amount(total_match.group(start_idx + 2))
            # else:
                # print(f"  No Total match for {section['name']}") # Debugging line


    # Parse Settlement (special case)
    # The pattern for extracting settlement content needs to be precise.
    # It should capture all lines between 'TOTAL' and 'NET SETTLEMENT AMOUNT' that represent ACQUIRER, ISSUER, OTHER totals.
    # Re-evaluating the settlement block extraction for robustness
    if settlement_block_match := re.search(r'(TOTAL\s+(?:ACQUIRER|ISSUER|OTHER).*?)(NET SETTLEMENT AMOUNT)', content, re.DOTALL):
        settlement_block_content = settlement_block_match.group(1) # This should contain the ACQUIRER, ISSUER, OTHER lines
        # print(f"\n--- Settlement Block Content ---\n{settlement_block_content}\n--------------------------") # Debugging line

        for line_type in ['ACQUIRER', 'ISSUER', 'OTHER']:
            # This regex is specifically looking for "TOTAL ACQUIRER", "TOTAL ISSUER", "TOTAL OTHER" lines
            # within the settlement block and capturing the three amount columns.
            pattern = rf'TOTAL {line_type}\s+([\d,]+\.\d{{2}}[A-Z]{{0,2}})?\s+([\d,]+\.\d{{2}}[A-Z]{{0,2}})?\s+([\d,]+\.\d{{2}}[A-Z]{{0,2}})?'
            if match := re.search(pattern, settlement_block_content):
                # print(f"  Matched {line_type} in Settlement: {match.groups()}") # Debugging line
                data[f'Settlement_Total{line_type}_CreditAmount'] = parse_amount(match.group(1))
                data[f'Settlement_Total{line_type}_DebitAmount'] = parse_amount(match.group(2))
                data[f'Settlement_Total{line_type}_TotalAmount'] = parse_amount(match.group(3))
            # else:
                # print(f"  No match for {line_type} in Settlement block") # Debugging line


    if net_match := re.search(r'NET SETTLEMENT AMOUNT\s+([\d,]+\.\d{2}[A-Z]{0,2})?\s+([\d,]+\.\d{2}[A-Z]{0,2})?\s+([\d,]+\.\d{2}[A-Z]{0-2})?', content):
        # print(f"  Matched Net Settlement: {net_match.groups()}") # Debugging line
        data['Settlement_Net_CreditAmount'] = parse_amount(net_match.group(1))
        data['Settlement_Net_DebitAmount'] = parse_amount(net_match.group(2))
        data['Settlement_Net_TotalAmount'] = parse_amount(net_match.group(3))
    # else:
        # print("  No match for Net Settlement Amount") # Debugging line

    return data


def transform_report_data_to_rows(data: dict) -> pd.DataFrame:
    metadata_cols = ['ReportID', 'ReportingFor', 'RollupTo', 'FundsXferEntity', 
                    'ProcDate', 'ReportDate', 'SettlementCurrency']
    
    sections = [
        {
            'MajorType': 'Interchange',
            'MinorTypes': ['Acquirer', 'Issuer', 'Other', 'Total'], # Changed MinorTypes to match parsed data keys more directly
            'Fields': ['Count', 'CreditAmount', 'DebitAmount', 'TotalAmount']
        },
        {
            'MajorType': 'Reimbursement',
            'MinorTypes': ['Acquirer', 'Issuer', 'Other', 'Total'],
            'Fields': ['CreditAmount', 'DebitAmount', 'TotalAmount']
        },
        {
            'MajorType': 'VisaCharges',
            'MinorTypes': ['Acquirer', 'Issuer', 'Other', 'Total'],
            'Fields': ['CreditAmount', 'DebitAmount', 'TotalAmount']
        },
        {
            'MajorType': 'Settlement',
            'MinorTypes': ['Acquirer', 'Issuer', 'Other', 'Net'],
            'Fields': ['CreditAmount', 'DebitAmount', 'TotalAmount']
        }
    ]
    
    rows = []
    
    for section in sections:
        for minor_type in section['MinorTypes']:
            row = {col: data.get(col, '') for col in metadata_cols}
            row['MajorType'] = section['MajorType']
            row['MinorType'] = minor_type
            
            for field in section['Fields']:
                # Construct the key based on how it's stored in parse_visa_report
                # For line types like 'ACQUIRER', 'ISSUER', 'OTHER', the key will be 'MajorType_MinorType_Field'
                # For 'Total' and 'Net', it will be 'MajorType_Total_Field' or 'Settlement_Net_Field'
                
                if minor_type in ['Acquirer', 'Issuer', 'Other']:
                    key = f"{section['MajorType']}_{minor_type}_{field}"
                elif minor_type == 'Total': # for section totals
                    key = f"{section['MajorType']}_Total_{field}"
                elif minor_type == 'Net' and section['MajorType'] == 'Settlement':
                    key = f"Settlement_Net_{field}"
                else:
                    # Fallback or error if a minor_type doesn't fit
                    key = f"{section['MajorType']}_{minor_type}_{field}"


                value = data.get(key, 0.0 if 'Amount' in field else 0)  # Default to 0.0 for amounts, 0 for count
                
                # Ensure values are correctly typed for DataFrame
                if isinstance(value, (int, float)):
                    pass 
                elif isinstance(value, str) and value.replace('.', '', 1).isdigit():
                    value = float(value) if 'Amount' in field else int(value)
                else: # Handle cases where value might be an empty string or other non-numeric
                    value = 0.0 if 'Amount' in field else 0

                row[field] = value
            
            rows.append(row)
    
    df = pd.DataFrame(rows)
    column_order = metadata_cols + ['MajorType', 'MinorType', 'Count', 
                                  'CreditAmount', 'DebitAmount', 'TotalAmount']
    
    # print("Parsed Data Keys:")
    # print(sorted(data.keys()))
    # print("\nSample Values (from parsed_data dict):")
    # print("Interchange_Acquirer_Count:", data.get('Interchange_Acquirer_Count')) 
    # print("Reimbursement_Acquirer_DebitAmount:", data.get('Reimbursement_Acquirer_DebitAmount'))
    # print("VisaCharges_Issuer_DebitAmount:", data.get('VisaCharges_Issuer_DebitAmount'))
    # print("Settlement_Net_TotalAmount:", data.get('Settlement_Net_TotalAmount'))
    
    return df[column_order]

@router.post("/process-visa-report")
async def process_visa_report(file: UploadFile = File(...), background_tasks: BackgroundTasks = BackgroundTasks()):
    try:
        contents = await file.read()
        parsed_data = parse_visa_report(contents.decode("utf-8"))
        df = transform_report_data_to_rows(parsed_data)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
            output_path = tmp.name
            df.to_excel(output_path, index=False)

        background_tasks.add_task(os.unlink, output_path)

        return FileResponse(
            output_path,
            filename="visa_report.xlsx",
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            background=background_tasks
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process Visa report: {str(e)}")