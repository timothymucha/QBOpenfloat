import streamlit as st
import pandas as pd
from io import StringIO

# Set account names (update as needed)
OPENFLOAT_ACCOUNT = "Openfloat"
PESAPAL_ACCOUNT = "Pesapal"
BANK_FEES_ACCOUNT = "Bank Service Charges"
ACCOUNTS_PAYABLE = "Accounts Payable"

# IIF headers
IIF_HEADER = "!TRNS\tTRNSTYPE\tDATE\tACCNT\tNAME\tMEMO\tAMOUNT\tDOCNUM\n!SPL\tTRNSTYPE\tDATE\tACCNT\tNAME\tMEMO\tAMOUNT\nENDTRNS"

def clean_amount(value):
    try:
        return float(str(value).replace(",", "").strip())
    except:
        return 0.0

def clean_payee(name):
    # Remove paybill number if in format "123456 - XYZ Supplier"
    if "-" in name:
        parts = name.split("-")
        if len(parts) > 1:
            return parts[1].strip()
    return name.strip()

def generate_iif(df):
    output = StringIO()
    output.write(IIF_HEADER + "\n")

    for _, row in df.iterrows():
        tx_type = row["Transaction Type"]
        date = pd.to_datetime(row["Date"]).strftime("%m/%d/%Y")
        payee = clean_payee(row["Account Name"])
        memo = f"{payee} - {row['Remark']}".strip()

        if tx_type == "Payment":
            amount = clean_amount(row["Amount"])
            output.write(f"TRNS\tBILL\t{date}\t{ACCOUNTS_PAYABLE}\t{payee}\t{memo}\t{-amount}\t\n")
            output.write(f"SPL\tBILL\t{date}\t{OPENFLOAT_ACCOUNT}\t{payee}\t{memo}\t{amount}\nENDTRNS\n")

        elif tx_type == "PesapalWithdrawal":
            amount = clean_amount(row["Credit"])
            output.write(f"TRNS\tTRANSFER\t{date}\t{PESAPAL_ACCOUNT}\t{payee}\t{memo}\t{-amount}\t\n")
            output.write(f"SPL\tTRANSFER\t{date}\t{OPENFLOAT_ACCOUNT}\t{payee}\t{memo}\t{amount}\nENDTRNS\n")

        elif tx_type in ["Charges", "Commission"]:
            amount = clean_amount(row["Charges"])
            output.write(f"TRNS\tCHECK\t{date}\t{OPENFLOAT_ACCOUNT}\t{BANK_FEES_ACCOUNT}\t{memo}\t{-amount}\t\n")
            output.write(f"SPL\tCHECK\t{date}\t{BANK_FEES_ACCOUNT}\t{BANK_FEES_ACCOUNT}\t{memo}\t{amount}\nENDTRNS\n")

    return output.getvalue()

# Streamlit UI
st.title("🔁 Openfloat CSV to QuickBooks IIF Converter")

uploaded_file = st.file_uploader("Upload Openfloat CSV file", type=["csv"])

if uploaded_file:
    try:
        df = pd.read_csv(uploaded_file)

        # Standardize column names
        df.columns = df.columns.str.strip()

        # Filter successful transactions only
        df = df[df["Transaction Status"].str.strip().str.lower() == "successful"]

        iif_data = generate_iif(df)

        st.success("✅ Conversion complete! Download your IIF file below.")
        st.download_button("📥 Download .IIF file", iif_data, file_name="openfloat_converted.iif")

    except Exception as e:
        st.error(f"❌ Error during conversion: {e}")
