import streamlit as st
import pandas as pd
import io
import re

st.title("Openfloat to QuickBooks IIF Converter")

uploaded_file = st.file_uploader("Upload Openfloat CSV", type="csv")

def clean_name(name):
    # Remove paybill numbers or trailing digits
    if pd.isna(name):
        return ""
    return re.sub(r'\s*\d+\s*$', '', str(name)).strip()

def format_date(date_str):
    try:
        return pd.to_datetime(date_str).strftime('%m/%d/%Y')
    except:
        return ""

def generate_iif(df):
    output = io.StringIO()
    output.write("!TRNS\tTRNSTYPE\tDATE\tACCNT\tNAME\tAMOUNT\tMEMO\tCLASS\n")
    output.write("!SPL\tTRNSTYPE\tDATE\tACCNT\tNAME\tAMOUNT\tMEMO\tCLASS\n")
    
    for _, row in df.iterrows():
        txn_type = row["Transaction Type"]
        status = row["Transaction Status"]
        if status != "Successful":
            continue

        memo = f"{clean_name(row['Account Name'])} - {row['Remark']}".strip(" -")
        date = format_date(row["Date"])
        name = clean_name(row["Account Name"])

        # Pesapal withdrawal – Transfer from Pesapal to Openfloat
        if txn_type == "PesapalWithdrawal":
            amount = float(row["Credit"])
            output.write(f"TRNS\tTRANSFER\t{date}\tOpenfloat\tPesapal\t{amount:.2f}\t{memo}\t\n")
            output.write(f"SPL\tTRANSFER\t{date}\tPesapal\tPesapal\t{-amount:.2f}\t{memo}\t\n")
            output.write("ENDTRNS\n")

        # Payment – Treat as Bill Payment
        elif txn_type == "Payment":
            bill_amount = float(row["Amount"])
            charges = float(row.get("Charges", 0) or 0)
            commission = float(row.get("Commission Amount", 0) or 0)
            total = float(row["Debit"])

            output.write(f"TRNS\tBILLPMT\t{date}\tOpenfloat\t{name}\t{-total:.2f}\t{memo}\t\n")
            output.write(f"SPL\tBILLPMT\t{date}\tAccounts Payable\t{name}\t{bill_amount:.2f}\t{memo}\t\n")

            if charges > 0:
                output.write(f"SPL\tBILLPMT\t{date}\tExpenses:BankFees\tBank Fee\t{charges:.2f}\tCharges\t\n")

            if commission > 0:
                output.write(f"SPL\tBILLPMT\t{date}\tExpenses:BankFees\tBank Fee\t{commission:.2f}\tCommission\t\n")

            output.write("ENDTRNS\n")

    return output.getvalue()

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    iif_data = generate_iif(df)

    st.download_button("Download .IIF File", iif_data, file_name="openfloat_export.iif", mime="text/plain")
    st.subheader("Data Preview")
    st.dataframe(df.head())
