#!/usr/bin/env python3
import csv
import argparse
import os
from datetime import datetime
from rich.console import Console
from rich.text import Text
from rich.panel import Panel
from rich.columns import Columns

console = Console()

# Default categories
CATEGORIES = {
    '1': 'Groceries',
    '2': 'Eating & drinking out',
    '3': 'Alcohol',
    '4': 'Subscriptions & apps',
    '5': 'Transport & travel',
    '6': 'Entertainment & events',
    '7': 'Shopping & retail',
    '8': 'Health & fitness',
    '9': 'Home & garden',
    '10': 'Miscellaneous',
}


def parse_args():
    parser = argparse.ArgumentParser(description="Interactive transaction categoriser.")
    parser.add_argument('transactions_csv', help='Path to transactions CSV')
    parser.add_argument('-s', '--summary-file', default='summary.csv',
                        help='Path to summary CSV (will resume totals if exists)')
    parser.add_argument('-l', '--start-line', type=int, default=0,
                        help='Index of transaction to start from (0-based)')
    parser.add_argument('--from-date', help='Include transactions on/after this date (YYYY-MM-DD)')
    parser.add_argument('--to-date', help='Include transactions on/before this date (YYYY-MM-DD)')
    return parser.parse_args()


def extract_transactions(csv_path, from_date=None, to_date=None):
    transactions = []
    fmt = '%Y-%m-%d'
    start = datetime.strptime(from_date, fmt) if from_date else None
    end = datetime.strptime(to_date, fmt) if to_date else None
    with open(csv_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            date = datetime.strptime(row['Transaction Date'], '%d/%m/%Y')
            if (start and date < start) or (end and date > end):
                continue
            txn = {'date': row['Transaction Date'], 'merchant': row['Narration']}
            if row['Debit']:
                txn['amount'] = float(row['Debit'].replace(',', '').replace('$', '').strip())
                txn['type'] = 'debit'
            elif row['Credit']:
                txn['amount'] = float(row['Credit'].replace(',', '').replace('$', '').strip())
                txn['type'] = 'credit'
            else:
                continue
            transactions.append(txn)
    return transactions


def load_summary(path):
    totals = {}
    income = 0.0
    if os.path.exists(path):
        with open(path, newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader, None)
            for cat, val in reader:
                amt = float(val)
                if cat == 'Income':
                    income = amt
                else:
                    totals[cat] = amt
    return totals, income


def save_summary(path, totals, income):
    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Category', 'Total'])
        for cat, amt in totals.items():
            writer.writerow([cat, f"{amt:.2f}"])
        writer.writerow(['Income', f"{income:.2f}"])
    console.print(f"\n✅ [bold green]Summary saved to [underline]{path}[/underline][/bold green]")


def categorise_transactions(transactions, start_line, prev_totals, prev_income):
    totals = {**{c: 0.0 for c in CATEGORIES.values()}, **prev_totals}
    income_total = prev_income
    extra_categories = {}
    history = []  # list of (index, txn, cat_key, new_cat_flag)
    i = start_line
    while i < len(transactions):
        txn = transactions[i]
        # Choose title color based on transaction type
        title_style = 'bold red' if txn['type'] == 'debit' else 'bold green'
        title_text = f"Type: {txn['type'].capitalize()}"
        panel = Panel(
            f"[bold yellow]Date:[/bold yellow] {txn['date']}\n"
            f"[bold cyan]Merchant:[/bold cyan] {txn['merchant']}\n"
            f"[bold green]Amount:[/bold green] ${txn['amount']:.2f}",
            title=f"[{title_style}]{title_text}[/{title_style}]",
            subtitle="Assign a category"
        )
        console.print(panel)

        combined = {**CATEGORIES, **extra_categories}
        options = []
        if txn['type'] == 'credit':
            options.append(Text('[i] Income', style='bold magenta'))
            options.append(Text('[c] Categorise', style='bold magenta'))
            options.append(Text('[s] Skip', style='bold magenta'))
        else:
            for key, cat in combined.items():
                options.append(Text(f"[{key}] {cat}", style='bold'))
            options.append(Text('[n] New category', style='bold magenta'))
        options.append(Text('[b] Back', style='bold magenta'))
        options.append(Text('[q] Quit', style='bold magenta'))
        console.print(Columns(options, equal=True, expand=True))

        choice = console.input('[bold magenta]Choice:[/bold magenta] ').strip()
        # Handle quit
        if choice in ('q', 'quit'):
            break
        # Handle back
        if choice in ('b', 'back'):
            if not history:
                console.print('[bold red]No action to go back to.[/bold red]')
                continue
            idx, prev_txn, key, is_new = history.pop()
            # undo totals
            if prev_txn['category'] == 'Income':
                income_total -= prev_txn['amount']
            else:
                cat = prev_txn['category']
                totals[cat] -= prev_txn['amount'] if prev_txn['type'] == 'debit' else -prev_txn['amount']
            # remove new category if created
            if is_new:
                del extra_categories[key]
                del totals[prev_txn['category']]
            i = idx
            continue

        # Credit options
        if txn['type'] == 'credit':
            if choice == 'i':
                income_total += txn['amount']
                txn['category'] = 'Income'
                history.append((i, txn, 'i', False))
            elif choice == 'c':
                opts = [Text(f"[{k}] {v}") for k, v in combined.items()]
                console.print(Columns(opts, equal=True, expand=True))
                sub = console.input('[bold magenta]Category key:[/bold magenta] ').strip()
                if sub in combined:
                    cat = combined[sub]
                    totals[cat] -= txn['amount']
                    txn['category'] = cat
                    history.append((i, txn, sub, False))
                else:
                    txn['category'] = 'Uncategorised'
                    history.append((i, txn, None, False))
            elif choice == 's':
                txn['category'] = 'Skipped'
                history.append((i, txn, None, False))
            else:
                console.print('[bold red]Invalid choice; skipping.[/bold red]')
                txn['category'] = 'Skipped'
                history.append((i, txn, None, False))
            i += 1
            continue

        # Debit path or new category
        if choice in combined:
            cat = combined[choice]
            totals[cat] += txn['amount']
            history.append((i, txn, choice, False))
            txn['category'] = cat
            i += 1
            continue
        if choice == 'n':
            new_cat = console.input('New category name: ').strip()
            next_key = str(max(int(k) for k in combined.keys()) + 1)
            extra_categories[next_key] = new_cat
            totals[new_cat] = txn['amount']
            history.append((i, txn, next_key, True))
            txn['category'] = new_cat
            i += 1
            continue

        # Skip or invalid
        txn['category'] = 'Skipped'
        history.append((i, txn, None, False))
        i += 1

    return totals, income_total


def main():
    args = parse_args()
    prev_totals, prev_income = load_summary(args.summary_file)
    txns = extract_transactions(args.transactions_csv, args.from_date, args.to_date)
    totals, income = categorise_transactions(txns, args.start_line, prev_totals, prev_income)
    save_summary(args.summary_file, totals, income)

if __name__ == '__main__':
    main()
