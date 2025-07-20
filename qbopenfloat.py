import streamlit as st
import pandas as pd
from io import StringIO

# Chart of Accounts
openfloat_account = "Openfloat"
pesapal_bank_account = "Pesapal"
bank_fees_account = "Bank Service Charges"
accounts_payable = "Accounts Payable"

def sanitize_payee(name):
    if pd.isna(name):
        return "Pesapal"
    return str(name).strip()

def parse_float(value):
    try:
        return float(str(value).replace(",", "").strip())
    except:
        return 0.0

def generate_iif(df):
    output = StringIO()

    # IIF Headers (added DOCNUM for BILLPMT)
    output.write("!TRNS\tTRNSTYPE\tDATE\tACCNT\tNAME\tAMOUNT\tDOCNUM\tMEMO\tCLEAR\n")
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
            continue  # skip bad dates

        payee = sanitize_payee(row.get("Account Name", ""))
        remark = str(row.get("Remark", "")).strip()
        memo = f"{payee} - {remark}".strip(" -")
        reference = str(row.get("Reference Id", "")).strip() or "N/A"

        amount = parse_float(row.get("Amount", 0))
        charges = parse_float(row.get("Charges", 0))
        commission = parse_float(row.get("Commission Amount", 0))
        credit = parse_float(row.get("Credit", 0))

        if txn_type == "Payment" and amount > 0:
            output.write(f"TRNS\tBILLPMT\t{date}\t{openfloat_account}\t{payee}\t{-amount:.2f}\t{reference}\t{memo}\tN\n")
            output.write(f"SPL\tBILLPMT\t{date}\t{accounts_payable}\t{payee}\t{amount:.2f}\t{memo}\tN\n")
            output.write("ENDTRNS\n")

        elif txn_type == "PesapalWithdrawal" and credit > 0:
            output.write(f"TRNS\tTRANSFER\t{date}\t{pesapal_bank_account}\t{payee}\t{-credit:.2f}\t{reference}\t{memo}\tN\n")
            output.write(f"SPL\tTRANSFER\t{date}\t{openfloat_account}\t\t{credit:.2f}\t{memo}\tN\n")
            output.write("ENDTRNS\n")

        elif txn_type in ["Charges", "Commission"] or (charges > 0 or commission > 0):
            total_fees = charges + commission
            if total_fees > 0:
                fee_memo = f"Bank Fees - {remark}" if remark else "Bank Fees"
                output.write(f"TRNS\tCHECK\t{date}\t{openfloat_account}\t{payee}\t{-total_fees:.2f}\t{reference}\t{fee_memo}\tN\n")
                output.write(f"SPL\tCHECK\t{date}\t{bank_fees_account}\t{payee}\t{total_fees:.2f}\t{fee_memo}\tN\n")
                output.write("ENDTRNS\n")

    return output.getvalue()

# Streamlit UI
st.title("🔁 Openfloat CSV to QuickBooks IIF Converter")
uploaded_file = st.file_uploader("Upload Openfloat CSV file", type=["csv"])

if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file)
        iif_data = generate_iif(df)

        st.success("✅ Conversion successful!")
        st.download_button("📥 Download IIF File", iif_data, file_name="openfloat.iif", mime="text/plain")
    except Exception as e:
        st.error(f"❌ Error during conversion: {e}")
