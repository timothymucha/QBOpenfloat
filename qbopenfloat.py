import streamlit as st
import pandas as pd
from io import StringIO

# Chart of Accounts (adjust if needed)
openfloat_account = "Openfloat"
pesapal_bank_account = "Pesapal"
bank_fees_account = "Bank Service Charges"
accounts_payable = "Accounts Payable"

def sanitize_payee(name):
    if pd.isna(name):
        return "Unknown Payee"
    # Remove numbers (e.g., paybill)
    return ''.join([i for i in name if not i.isdigit()]).strip()

def parse_float(value):
    try:
        return float(str(value).replace(",", "").strip())
    except:
        return 0.0

def generate_iif(df):
    output = StringIO()
    
    # IIF Header
    output.write("!TRNS\tTRNSTYPE\tDATE\tACCNT\tNAME\tAMOUNT\tMEMO\tCLEAR\n")
    output.write("!SPL\tTRNSTYPE\tDATE\tACCNT\tNAME\tAMOUNT\tMEMO\tCLEAR\n")
    output.write("!ENDTRNS\n")

    for _, row in df.iterrows():
        txn_type = str(row.get("Transaction Type", "")).strip()
        status = str(row.get("Transaction Status", "")).strip()
        if status != "Successful":
            continue

        try:
            date = pd.to_datetime(row["Date"]).strftime("%m/%d/%Y")
        except:
            continue  # skip if date invalid

        payee = sanitize_payee(str(row.get("Payee", "")).strip())
        remark = str(row.get("Remark", "")).strip()
        memo = f"{payee} - {remark}" if remark else payee

        amount = parse_float(row.get("Amount", 0))
        charges = parse_float(row.get("Charges", 0))
        credit = parse_float(row.get("Credit", 0))

        if txn_type == "Payment" and amount > 0:
            # Bill Payment from Openfloat
            output.write(f"TRNS\tBILL\t{date}\t{openfloat_account}\t{payee}\t{-amount}\t{memo}\tN\n")
            output.write(f"SPL\tBILL\t{date}\t{accounts_payable}\t{payee}\t{amount}\t{memo}\tN\n")
            output.write("ENDTRNS\n")

        elif txn_type == "Charges" or txn_type == "Commission":
            # Bank Fees from Openfloat
            if charges > 0:
                output.write(f"TRNS\tCHECK\t{date}\t{openfloat_account}\t{payee}\t{-charges}\t{memo}\tN\n")
                output.write(f"SPL\tCHECK\t{date}\t{bank_fees_account}\t\t{charges}\t{memo}\tN\n")
                output.write("ENDTRNS\n")

        elif txn_type == "PesapalWithdrawal" and credit > 0:
            # Transfer from Pesapal
            output.write(f"TRNS\tTRANSFER\t{date}\t{pesapal_bank_account}\t{payee}\t{-credit}\t{memo}\tN\n")
            output.write(f"SPL\tTRANSFER\t{date}\t{{openfloat_account}\t\t{credit}\t{memo}\tN\n")
            output.write("ENDTRNS\n")

    return output.getvalue()

# Streamlit UI
st.title("🔁 Openfloat CSV to QuickBooks IIF Converter")
uploaded_file = st.file_uploader("Upload Openfloat CSV file", type=["csv"])

if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file)

        # Convert
        iif_data = generate_iif(df)

        # Download
        st.success("✅ Conversion successful!")
        st.download_button("📥 Download IIF File", iif_data, file_name="openfloat.iif", mime="text/plain")
    except Exception as e:
        st.error(f"❌ Error during conversion: {e}")
