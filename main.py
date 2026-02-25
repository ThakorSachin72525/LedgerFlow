import os
from dotenv import load_dotenv
from src.models.read_pdf import extract_transactions_from_pdf

load_dotenv()

if __name__ == "__main__":
    pdf_path = os.getenv("pdf_path")
    password = os.getenv("password")

    df, opening_balance, closing_balance = extract_transactions_from_pdf(
        pdf_path, password
    )

    print("\nOpening Balance:", opening_balance)
    print("Closing Balance:", closing_balance)
    print("\nTransactions Preview:\n")
    print(df.head())
    print("\nTotal Transactions:", len(df))