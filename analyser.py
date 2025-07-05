import pdfplumber
import re
import csv

CATEGORIES = {
    '1': 'Groceries',
    '2': 'Beer',
    '3': 'Subscriptions',
}

def extract_transactions(pdf_path):
    transactions = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                lines = text.split('\n')
                for line in lines:
                    match = re.match(r"(\d{2} \w{3} \d{2}) (.*?) \$([\d,]+\.\d\d)", line)
                    if match:
                        date, merchant, amount = match.groups()
                        transactions.append({
                            'date': date,
                            'merchant': merchant.strip(),
                            'amount': amount.replace(",", ""),
                        })
    return transactions

def categorise_transactions(transactions):
    results = []
    extra_categories = {}
    for txn in transactions:
        print(f"\nDate: {txn['date']}, Merchant: {txn['merchant']}, Amount: ${txn['amount']}")
        print("Categories:")
        for key, cat in CATEGORIES.items():
            print(f"{key}: {cat}")
        print("n: New category")
        print("s: Skip")

        choice = input("Choose category: ").strip()
        if choice in CATEGORIES:
            category = CATEGORIES[choice]
        elif choice == 'n':
            new_cat = input("Enter new category name: ").strip()
            key = str(len(CATEGORIES) + len(extra_categories) + 1)
            extra_categories[key] = new_cat
            category = new_cat
        elif choice == 's':
            category = 'Uncategorised'
        else:
            category = 'Uncategorised'

        txn['category'] = category
        results.append(txn)
    return results

def save_summary(transactions, output_file='summary.csv'):
    keys = ['date', 'merchant', 'amount', 'category']
    with open(output_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(transactions)

    print(f"\nSummary saved to {output_file}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python analyser.py /path/to/statements/")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    txns = extract_transactions(pdf_path)
    categorised = categorise_transactions(txns)
    save_summary(categorised)
