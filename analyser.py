import csv
from rich.console import Console
from rich.table import Table
from rich.text import Text
from rich.panel import Panel
from rich.columns import Columns

console = Console()

CATEGORIES = {
    '1': 'Groceries',
    '2': 'Eating & drinking out',
    '3': 'Alcohol',
    '4': 'Subscriptions & apps',
    '5': 'Transport & travel',
    '6': 'Public transport (Smartrider)',
    '7': 'Entertainment & events',
    '8': 'Gifts & donations',
    '9': 'Shopping & retail',
    '10': 'Health & fitness',
    '11': 'Home & garden',
    '13': 'Miscellaneous',
}

def extract_costs(csv_path):
    transactions = []
    with open(csv_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            debit = row['Debit']
            if debit:
                amount = float(debit.replace(',', '').replace('$', '').strip())
                txn = {
                    'date': row['Transaction Date'],
                    'merchant': row['Narration'],
                    'amount': amount
                }
                transactions.append(txn)
    return transactions

def categorise_transactions(transactions):
    results = []
    extra_categories = {}

    for txn in transactions:
        panel_text = f"[bold yellow]Date:[/bold yellow] {txn['date']}\n" \
                     f"[bold cyan]Merchant:[/bold cyan] {txn['merchant']}\n" \
                     f"[bold green]Amount:[/bold green] ${txn['amount']:.2f}"
        console.print(Panel(panel_text, title="Transaction", subtitle="Assign a category"))

        # Combine default and extra categories
        combined_categories = {**CATEGORIES, **extra_categories}
        # Prepare list of Text objects for columns
        category_blocks = []

        for key, cat in combined_categories.items():
            block = Text(f"[{key}] {cat}", style="bold")
            category_blocks.append(block)

        # Add options for new/skip
        category_blocks.append(Text("[n] New category", style="bold magenta"))
        category_blocks.append(Text("[s] Skip", style="bold magenta"))

        console.print(Columns(category_blocks, equal=True, expand=True))

        choice = console.input("[bold magenta]Choose category:[/bold magenta] ").strip()

        if choice in CATEGORIES:
            category = CATEGORIES[choice]
        elif choice in extra_categories:
            category = extra_categories[choice]
        elif choice == 'n':
            new_cat = console.input("Enter new category name: ").strip()
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
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(transactions)

    console.print(f"\n✅ [bold green]Summary saved to [underline]{output_file}[/underline][/bold green]")

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        console.print("[bold red]Usage: python analyser.py /path/to/statements.csv[/bold red]")
        sys.exit(1)

    csv_path = sys.argv[1]
    txns = extract_costs(csv_path)
    categorised = categorise_transactions(txns)
    save_summary(categorised)
