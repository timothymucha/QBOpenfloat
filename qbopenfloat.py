import streamlit as st
import pandas as pd
from io import StringIO
from datetime import datetime

def convert_pesapal_to_iif(file):
    df = pd.read_csv(file, skiprows=6)

    # Normalize and clean up column names
    df.columns = df.columns.str.strip()
    
    iif_output = StringIO()
    iif_output.write("!TRNS\tTRNSTYPE\tDATE\tACCNT\tNAME\tAMOUNT\tMEMO\tCLEAR\n")
    iif_output.write("!SPL\tTRNSTYPE\tDATE\tACCNT\tNAME\tAMOUNT\tMEMO\tCLEAR\n")
    iif_output.write("!ENDTRNS\n")

    for _, row in df.iterrows():
        txn_type = row.get("Transaction Type", "").strip()
        date_str = row.get("Date", "").strip()
        try:
            txn_date = datetime.strptime(date_str, "%d/%m/%Y %I:%M:%S %p").strftime("%m/%d/%Y")
        except:
            continue  # Skip malformed date

        account_name = str(row.get("Account Name", "")).strip()
        remark = str(row.get("Remark", "")).strip()
        memo = f"{account_name} - {remark}" if remark else account_name

        if txn_type == "Payment":
            amount = float(str(row.get("Amount", "0")).replace(",", "").strip())
            if amount <= 0:
                continue  # skip invalid payments

            iif_output.write(f"TRNS\tBILL\t{txn_date}\tOpenfloat\t{account_name}\t{-amount:.2f}\t{memo}\tN\n")
            iif_output.write(f"SPL\tBILL\t{txn_date}\tAccounts Payable\t{account_name}\t{amount:.2f}\t{memo}\tN\n")
            iif_output.write("ENDTRNS\n")

        elif txn_type == "PesapalWithdrawal":
            credit = float(str(row.get("Credit", "0")).replace(",", "").strip())
            if credit <= 0:
                continue  # skip invalid transfers

            iif_output.write(f"TRNS\tTRANSFER\t{txn_date}\tPesapal\t\t{-credit:.2f}\tPesapal to DTB\tN\n")
            iif_output.write(f"SPL\tTRANSFER\t{txn_date}\tDTB\t\t{credit:.2f}\tPesapal to DTB\tN\n")
            iif_output.write("ENDTRNS\n")

        elif txn_type in ["Charges", "Commission"]:
            charges = float(str(row.get("Charges", "0")).replace(",", "").strip() or 0)
            commission = float(str(row.get("Commission Amount", "0")).replace(",", "").strip() or 0)
            total_fee = charges + commission
            if total_fee <= 0:
                continue  # no fees to record

            fee_memo = f"Bank Fees - {remark}" if remark else "Bank Fees"

            iif_output.write(f"TRNS\tBILL\t{txn_date}\tOpenfloat\t{account_name}\t{-total_fee:.2f}\t{fee_memo}\tN\n")
            iif_output.write(f"SPL\tBILL\t{txn_date}\tBank Service Charges\t{account_name}\t{total_fee:.2f}\t{fee_memo}\tN\n")
            iif_output.write("ENDTRNS\n")

    return iif_output.getvalue()
# Streamlit UI
st.title("🔁 Openfloat CSV to QuickBooks IIF Converter")
uploaded_file = st.file_uploader("Upload Openfloat CSV file", type=["csv"])

if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file)

        # Convert
        iif_data = convert_pesapal_to_iif(df)

        # Download
        st.success("✅ Conversion successful!")
        st.download_button("📥 Download IIF File", iif_data, file_name="openfloat.iif", mime="text/plain")
    except Exception as e:
        st.error(f"❌ Error during conversion: {e}")
