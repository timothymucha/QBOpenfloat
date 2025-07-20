import streamlit as st
import pandas as pd
from io import StringIO

st.title("🔁 Openfloat CSV to QuickBooks IIF Converter")

uploaded_file = st.file_uploader("Upload Openfloat CSV file", type="csv")

def clean_amount(val):
    if pd.isna(val):
        return 0.0
    return float(str(val).replace(",", "").strip())

def extract_name(name):
    if pd.isna(name):
        return ""
    return str(name).split()[0]  # Remove paybill or code

def generate_iif(df):
    output = StringIO()
    output.write("!TRNS\tTRNSTYPE\tDATE\tACCNT\tNAME\tAMOUNT\tMEMO\n")
    output.write("!SPL\tTRNSTYPE\tDATE\tACCNT\tNAME\tAMOUNT\tMEMO\n")
    output.write("ENDTRNS\n")

    for _, row in df.iterrows():
        status = str(row.get("Transaction Status", "")).strip()
        if status != "Successful":
            continue

        txn_type = str(row.get("Transaction Type", "")).strip()
        date = pd.to_datetime(row["Date"]).strftime("%m/%d/%Y")
        payee = extract_name(row.get("Payee", ""))
        remark = str(row.get("Remark", "")).strip()
        memo = f"{payee} - {remark}"

        if txn_type == "Payment":
            amount = clean_amount(row.get("Amount"))
            if amount > 0:
                output.write(f"TRNS\tBILLPMT\t{date}\tOpenfloat\t{payee}\t{-amount:.2f}\t{memo}\n")
                output.write(f"SPL\tBILLPMT\t{date}\tAccounts Payable\t{payee}\t{amount:.2f}\t{memo}\n")
                output.write("ENDTRNS\n")

        elif txn_type == "PesapalWithdrawal":
            credit = clean_amount(row.get("Credit"))
            if credit > 0:
                output.write(f"TRNS\tTRANSFER\t{date}\tPesapal\tDTB\t{-credit:.2f}\t{memo}\n")
                output.write(f"SPL\tTRANSFER\t{date}\tOpenfloat\tDTB\t{credit:.2f}\t{memo}\n")
                output.write("ENDTRNS\n")

        elif txn_type in ["Charge", "Commission"]:
            charge = clean_amount(row.get("Charges"))
            if charge > 0:
                output.write(f"TRNS\tCHECK\t{date}\tOpenfloat\tBank Fees\t{-charge:.2f}\t{memo}\n")
                output.write(f"SPL\tCHECK\t{date}\tBank Service Charges\tBank Fees\t{charge:.2f}\t{memo}\n")
                output.write("ENDTRNS\n")

    return output.getvalue()

if uploaded_file:
    try:
        df = pd.read_csv(uploaded_file)
        if "Date" not in df.columns:
            st.error("CSV must contain a 'Date' column.")
        else:
            iif_data = generate_iif(df)
            st.download_button(
                label="📥 Download IIF File",
                data=iif_data,
                file_name="openfloat_export.iif",
                mime="text/plain"
            )
    except Exception as e:
        st.error(f"❌ Error during conversion: {e}")
