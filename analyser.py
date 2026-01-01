#!/usr/bin/env python3
import csv
import argparse
import os
from datetime import datetime
from decimal import Decimal, InvalidOperation
from collections import defaultdict

from rich.console import Console
from rich.text import Text
from rich.panel import Panel
from rich.columns import Columns

import matplotlib.pyplot as plt

console = Console()

CATEGORIES = {
    '1': 'Groceries',
    '2': 'Eating out',
    '3': 'Guinness',
    '4': 'Homewares',
    '5': 'Transport',
    '6': 'Entertainment',
    '7': 'Shopping',
    '8': 'Fitness',
    '9': 'Subscriptions',
    '10': 'Rent',
    '11': 'Miscellaneous',
}

def parse_args():
    p = argparse.ArgumentParser(description="Manual transaction categoriser.")
    p.add_argument('transactions_csv', nargs='?', default=None, help='Path to transactions CSV')
    p.add_argument('-s', '--summary-file', default='summary.csv',
                   help='Path to summary CSV (balances will resume if exists)')
    p.add_argument('-l', '--start-line', type=int, default=0,
                   help='Index of transaction to start from (0-based)')
    p.add_argument('--from-date', help='Include transactions on/after this date (YYYY-MM-DD)')
    p.add_argument('--to-date', help='Include transactions on/before this date (YYYY-MM-DD)')
    p.add_argument('--pie-chart', default='summary.png', help='Output path for pie chart')
    p.add_argument('--chart-only', action='store_true',
               help='Only regenerate the pie chart from the summary file and exit')
    return p.parse_args()

def to_decimal(s: str) -> Decimal:
    s = (s or "").strip()
    if not s:
        return Decimal("0")
    # remove commas and currency symbols if any sneak in
    s = s.replace(",", "").replace("$", "").replace("£", "")
    try:
        return Decimal(s)
    except InvalidOperation:
        return Decimal("0")

def extract_transactions(csv_path, from_date=None, to_date=None):
    txns = []
    fmt = '%Y-%m-%d'
    start = datetime.strptime(from_date, fmt).date() if from_date else None
    end = datetime.strptime(to_date, fmt).date() if to_date else None

    with open(csv_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            date_str = (row.get('Transaction Date') or '').strip()
            if not date_str or date_str.lower() == 'transaction date':
                # skip blank rows or repeated headers
                continue

            try:
                d = datetime.strptime(date_str, '%d/%m/%Y').date()
            except ValueError:
                # skip rows with unexpected date formats
                continue

            if (start and d < start) or (end and d > end):
                continue

            debit = to_decimal(row.get('Debit', ''))
            credit = to_decimal(row.get('Credit', ''))

            # Your CSV uses negative numbers in Debit for spending.
            # We'll build a single signed amount:
            amount = Decimal("0")
            if debit != 0:
                amount = debit            # already negative for spending
            elif credit != 0:
                amount = credit           # positive
            else:
                continue

            txns.append({
                'date': row['Transaction Date'],
                'merchant': row.get('Narration', ''),
                'amount': amount,         # signed
                'raw_debit': debit,
                'raw_credit': credit,
            })

    return txns

def load_summary(path):
    """
    Summary is stored as:
    Category, Balance
    Groceries, -123.45
    ...
    (no special Income row; income is just positive amounts in categories or kept as 'Income' category)
    """
    balances = defaultdict(Decimal)
    if os.path.exists(path):
        with open(path, newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader, None)
            for cat, val in reader:
                balances[cat] = to_decimal(val)
    return balances

def save_summary(path, balances):
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['Category', 'Balance'])
        for cat, bal in sorted(balances.items(), key=lambda x: x[0].lower()):
            w.writerow([cat, f"{bal:.2f}"])

    console.print(f"\n✅ [bold green]Summary saved to [underline]{path}[/underline][/bold green]")

def generate_pie_chart(balances, output_path='summary.png'):
    # Spending only (negative balances)
    items = [(cat, bal) for cat, bal in balances.items() if bal < 0]

    if not items:
        console.print("[bold red]No spending (negative balances) to chart.[/bold red]")
        return

    # Sort largest spend first
    items.sort(key=lambda x: x[1])  # most negative first

    labels = [cat for cat, _ in items]
    values = [float(-bal) for _, bal in items]  # positive magnitudes

    total_spend = sum(values)

    fig, ax = plt.subplots()

    wedges, _, _ = ax.pie(
        values,
        autopct='%1.1f%%',
        startangle=90,
        pctdistance=0.75
    )
    ax.axis('equal')

    # Legend shows category + $ amount
    legend_labels = [f"{cat} — {val:.2f}" for cat, val in zip(labels, values)]
    ax.legend(
        wedges,
        legend_labels,
        title=f"Total spend: {total_spend:.2f}",
        loc="center left",
        bbox_to_anchor=(1.02, 0.5),
        borderaxespad=0.0
    )

    plt.title('Spending by Category (net)')
    plt.tight_layout()
    plt.savefig(output_path, bbox_inches="tight")
    console.print(f"✅ [bold green]Pie chart saved to [underline]{output_path}[/underline][/bold green]")
    console.print(f"[bold]Total spend (from negative balances):[/bold] {total_spend:.2f}")

def render_balances(balances):
    lines = []
    for cat, bal in sorted(balances.items(), key=lambda x: x[0].lower()):
        style = "green" if bal > 0 else "red" if bal < 0 else "white"
        lines.append(f"[bold]{cat}[/bold]: [{style}]{bal:.2f}[/{style}]")
    return "\n".join(lines) if lines else "(no balances yet)"

def categorise_transactions(transactions, start_line, balances):
    # ensure all default categories exist
    for c in CATEGORIES.values():
        balances.setdefault(c, Decimal("0"))
    balances.setdefault("Income", Decimal("0"))  # optional bucket if you want it

    history = []
    i = start_line
    quit_early = False

    while i < len(transactions):
        txn = transactions[i]
        amt = txn['amount']
        kind = "CREDIT" if amt > 0 else "DEBIT" if amt < 0 else "ZERO"

        title_style = 'bold green' if amt > 0 else 'bold red' if amt < 0 else 'bold yellow'
        panel = Panel(
            f"[bold yellow]Date:[/bold yellow] {txn['date']}\n"
            f"[bold cyan]Merchant:[/bold cyan] {txn['merchant']}\n"
            f"[bold]Amount:[/bold] {amt:.2f}\n\n"
            f"[dim]Current balances:[/dim]\n{render_balances(balances)}",
            title=f"[{title_style}]{kind}[/{title_style}]"
        )
        console.print(panel)

        combined = dict(CATEGORIES)  # only your numbered categories
        options = [Text(f"[{k}] {v}", style='bold') for k, v in combined.items()]
        options.append(Text("[i] Income (only for credits)", style="bold magenta"))
        options.append(Text("[n] New category", style="bold magenta"))
        options.append(Text("[b] Back", style="bold magenta"))
        options.append(Text("[q] Quit", style="bold magenta"))
        console.print(Columns(options, equal=True, expand=True))

        raw_choice = console.input('[bold magenta]Choice (Enter = skip):[/bold magenta] ')
        choice = raw_choice.strip().lower()

        if choice == '':
            history.append((i, None, Decimal("0")))
            i += 1
            continue

        if choice in ('q', 'quit'):
            quit_early = True
            break

        if choice in ('b', 'back'):
            if not history:
                console.print('[bold red]No action to go back to.[/bold red]')
                continue
            idx, prev_category, prev_amount = history.pop()
            if prev_category is not None:
                balances[prev_category] -= prev_amount
            i = idx
            continue

        if choice == 'i':
            if amt <= 0:
                console.print("[bold red]Income only makes sense for positive amounts.[/bold red]")
                continue
            balances["Income"] += amt
            history.append((i, "Income", amt))
            i += 1
            continue

        if choice == 'n':
            new_cat = console.input('New category name: ').strip()
            if not new_cat:
                console.print("[bold red]Category name cannot be empty.[/bold red]")
                continue
            balances.setdefault(new_cat, Decimal("0"))
            balances[new_cat] += amt
            history.append((i, new_cat, amt))
            i += 1
            continue

        if choice in combined:
            cat = combined[choice]
            balances[cat] += amt
            history.append((i, cat, amt))
            i += 1
            continue

        console.print("[bold red]Invalid choice.[/bold red]")

    return balances, quit_early

def main():
    args = parse_args()
    balances = load_summary(args.summary_file)

    if args.chart_only:
        generate_pie_chart(balances, args.pie_chart)
        return

    if not args.transactions_csv:
        console.print("[bold red]transactions_csv is required unless --chart-only is used.[/bold red]")
        return

    txns = extract_transactions(args.transactions_csv, args.from_date, args.to_date)

    if not txns:
        console.print("[bold red]No transactions found in the specified date range.[/bold red]")
        return

    balances, quit_early = categorise_transactions(txns, args.start_line, balances)
    save_summary(args.summary_file, balances)
    generate_pie_chart(balances, args.pie_chart)

    if quit_early:
        console.print("[bold yellow]Session ended early. Summary and pie chart generated for transactions processed so far.[/bold yellow]")

if __name__ == '__main__':
    main()
