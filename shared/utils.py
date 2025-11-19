# Shared utilities for Quantora

def format_currency(amount: float, currency: str = "USD") -> str:
    return f"{amount:.2f} {currency}"
