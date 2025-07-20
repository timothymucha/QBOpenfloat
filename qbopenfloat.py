import streamlit as st
import pandas as pd
from io import StringIO

# Constants
OPENFLOAT_ACCOUNT = "Openfloat"
PESAPAL_ACCOUNT = "Pesapal"
BANK_FEES_ACCOUNT = "Bank Service Charges"
ACCOUNTS_PAYABLE = "Accounts Payable"
VENDOR = "Generic Vendor"

# IIF Header
IIF_HEADER = "!TRNS\tTRNSTYPE\tDATE\tACCNT\tNAME\tAMOUNT\tMEMO\n!SPL\tTRNSTYPE\tDATE\tACCNT\tNAME\tAMOUNT\tMEMO\nENDTRNS"

# Util to clean payee name (remove phone/paybill)
def clean_payee(name):
    return ' '.join([w for w in str(name).split() if not w.isdigit() and not w.startswith("07")])

# Main conversion logic
def generate_iif(df):
    output = StringIO()
    output.write(IIF_HEADER + "\n")
    
    for _, row in df.iterrows():
        if row["Transaction Status"].strip().lower() != "successful":
            continue

        txn_type = row["Transaction Type"].strip()
        date = pd.to_datetime(row["Date"]).strftime('%m/%d/%Y')
        payee = clean_payee(row.get("Payee", "Unknown"))
        memo = f"{payee} {row.get('Remark', '')}".strip()

        if txn_type == "Payment":
            amount = float(row["Amount"])
            output.write(f"TRNS\tBILLPMT\t{date}\t{OPENFLOAT_ACCOUNT}\t{payee}\t{-amount}\t{memo}\n")
            output.write(f"SPL\tBILLPMT\t{date}\t{ACCOUNTS_PAYABLE}\t{payee}\t{amount}\t{memo}\n")
            output.write("ENDTRNS\n")

        elif txn_type == "PesapalWithdrawal":
            amount = float(row["Amount"])
            output.write(f"TRNS\tTRANSFER\t{date}\t{PESAPAL_ACCOUNT}\t{payee}\t{-amount}\t{memo}\n")
            output.write(f"SPL\tTRANSFER\t{date}\t{OPENFLOAT_ACCOUNT}\t{payee}\t{amount}\t{memo}\n")
            output.write("ENDTRNS\n")

        elif txn_type in ["Charges", "Commission"]:
            charge = float(row.get("Charges", 0))
            if charge > 0:
                output.write(f"TRNS\tCHECK\t{date}\t{OPENFLOAT_ACCOUNT}\t{VENDOR}\t{-charge}\t{memo}\n")
                output.write(f"SPL\tCHECK\t{date}\t{BANK_FEES_ACCOUNT}\t{VENDOR}\t{charge}\t{memo}\n")
                output.write("ENDTRNS\n")

    return output.getvalue()

# Streamlit UI
st.title("Openfloat CSV to QuickBooks IIF Converter")
uploaded_file = st.file_uploader("Upload Openfloat CSV file", type="csv")

if uploaded_file:
    df = pd.read_csv(uploaded_file)

    # Normalize headers
    df.columns = [col.strip() for col in df.columns]

    try:
        iif_data = generate_iif(df)
        st.success("Conversion successful! Click below to download.")

        st.download_button(
            label="Download .IIF File",
            data=iif_data,
            file_name="openfloat_export.iif",
            mime="text/plain"
        )
    except Exception as e:
        st.error(f"❌ Error during conversion: {str(e)}")
