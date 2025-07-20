import streamlit as st
import pandas as pd
from io import StringIO

st.title("Openfloat CSV to QuickBooks IIF Converter")
uploaded_file = st.file_uploader("Upload Openfloat CSV file", type="csv")

def clean_amount(val):
    try:
        return float(str(val).replace(',', '').strip())
    except:
        return 0.0

def clean_payee(name):
    if isinstance(name, str):
        return ' '.join(word for word in name.split() if not word.isdigit())
    return name

def generate_iif(df):
    output = StringIO()
    output.write("!TRNS\tTRNSTYPE\tDATE\tACCNT\tNAME\tMEMO\tAMOUNT\n")
    output.write("!SPL\tTRNSTYPE\tDATE\tACCNT\tNAME\tMEMO\tAMOUNT\n")
    output.write("!ENDTRNS\n")

    for _, row in df.iterrows():
        date = pd.to_datetime(row['Date']).strftime('%m/%d/%Y')
        status = row['Transaction Status']
        if status != "Successful":
            continue

        tx_type = row['Transaction Type']
        raw_payee = str(row.get("Account Name", "Unknown"))
        payee = clean_payee(raw_payee)
        remark = str(row.get("Remark", "")).strip()
        memo = f"{payee} - {remark}"

        amount = clean_amount(row.get("Amount", 0))
        charges = clean_amount(row.get("Charges", 0))
        credit = clean_amount(row.get("Credit", 0))
        debit = clean_amount(row.get("Debit", 0))

        if tx_type == "PesapalWithdrawal":
            # Transfer from Pesapal to Openfloat
            output.write(f"TRNS\tTRANSFER\t{date}\tPesapal\t\t{memo}\t{-debit}\n")
            output.write(f"SPL\tTRANSFER\t{date}\tOpenfloat\t\t{memo}\t{debit}\n")
            output.write("ENDTRNS\n")
        elif tx_type in ["Charges", "Commission"]:
            # Expense: Bank Charges
            output.write(f"TRNS\tCHECK\t{date}\tOpenfloat\t{payee}\t{memo}\t{-charges}\n")
            output.write(f"SPL\tCHECK\t{date}\tBank Service Charges\t\t{memo}\t{charges}\n")
            output.write("ENDTRNS\n")
        elif tx_type == "Payment":
            # Bill Payment
            output.write(f"TRNS\tBILLPMT\t{date}\tOpenfloat\t{payee}\t{memo}\t{-debit}\n")
            output.write(f"SPL\tBILLPMT\t{date}\tAccounts Payable\t\t{memo}\t{debit}\n")
            output.write("ENDTRNS\n")

    return output.getvalue()

if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file)
        st.dataframe(df.head())

        iif_data = generate_iif(df)
        st.download_button("Download IIF File", iif_data, file_name="openfloat.iif", mime="text/plain")
    except Exception as e:
        st.error(f"❌ Error during conversion: {e}")
