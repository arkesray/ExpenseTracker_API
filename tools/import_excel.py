"""Import historical trips and transactions from an Excel workbook.

Sheets and columns:
  Trips: trip_name, description, members
  Transactions: trip_name, amount, description, paid_by, shared_by, shares, is_expense

Use shared_by as ``alice,bob`` for an equal split, or shares as
``alice:12.50,bob:7.50`` for explicit shares. Users must already exist.
"""

from __future__ import annotations

import argparse
import math
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any
from urllib.parse import quote

import pandas as pd
import requests


MICRO_UNIT = Decimal("0.000001")
REQUIRED_TRIP_COLUMNS = {"trip_name", "description", "members"}
REQUIRED_TRANSACTION_COLUMNS = {"trip_name", "amount", "description", "paid_by", "shared_by"}


def text(value: Any) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def decimal(value: Any, label: str) -> Decimal:
    try:
        result = Decimal(text(value))
    except (InvalidOperation, ValueError):
        raise ValueError(f"{label} must be a number, got {value!r}") from None
    if not result.is_finite() or result <= 0:
        raise ValueError(f"{label} must be greater than zero")
    return result


def parse_names(value: Any, label: str) -> list[str]:
    names = [part.strip() for part in text(value).split(",") if part.strip()]
    if not names:
        raise ValueError(f"{label} must contain at least one username")
    if len(names) != len(set(names)):
        raise ValueError(f"{label} contains duplicate usernames")
    return names


def parse_shares(value: Any, label: str) -> list[dict[str, Any]]:
    result = []
    for item in parse_names(value, label):
        if ":" not in item:
            raise ValueError(f"{label} entries must look like username:amount")
        username, amount = item.split(":", 1)
        result.append({"username": username.strip(), "share": float(decimal(amount, label))})
    return result


def equal_shares(usernames: list[str], amount: Decimal) -> list[dict[str, Any]]:
    share = (amount / len(usernames)).quantize(MICRO_UNIT, rounding=ROUND_HALF_UP)
    shares = [share] * len(usernames)
    shares[-1] += amount - sum(shares)
    return [{"username": user, "share": float(value)} for user, value in zip(usernames, shares)]


def load_workbook(path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    try:
        trips = pd.read_excel(path, sheet_name="Trips").fillna("")
        transactions = pd.read_excel(path, sheet_name="Transactions").fillna("")
    except ValueError as exc:
        raise ValueError("Workbook must contain sheets named Trips and Transactions") from exc

    missing_trips = REQUIRED_TRIP_COLUMNS - set(trips.columns)
    missing_transactions = REQUIRED_TRANSACTION_COLUMNS - set(transactions.columns)
    if missing_trips:
        raise ValueError(f"Trips sheet is missing columns: {', '.join(sorted(missing_trips))}")
    if missing_transactions:
        raise ValueError(f"Transactions sheet is missing columns: {', '.join(sorted(missing_transactions))}")
    return trips, transactions


def validate(trips: pd.DataFrame, transactions: pd.DataFrame) -> list[dict[str, Any]]:
    trip_data = []
    trip_names = set()
    for row_number, row in trips.iterrows():
        name = text(row["trip_name"])
        if not name or name in trip_names:
            raise ValueError(f"Trips row {row_number + 2}: trip_name is missing or duplicated")
        trip_names.add(name)
        trip_data.append({
            "name": name,
            "description": text(row["description"]),
            "members": parse_names(row["members"], f"Trips row {row_number + 2} members"),
        })

    transaction_data = []
    for row_number, row in transactions.iterrows():
        label = f"Transactions row {row_number + 2}"
        trip_name = text(row["trip_name"])
        if trip_name not in trip_names:
            raise ValueError(f"{label}: unknown trip_name {trip_name!r}")
        amount = decimal(row["amount"], f"{label} amount")
        shared_by = parse_names(row["shared_by"], f"{label} shared_by")
        shares = parse_shares(row["shares"], f"{label} shares") if text(row.get("shares", "")) else equal_shares(shared_by, amount)
        if {item["username"] for item in shares} != set(shared_by):
            raise ValueError(f"{label}: shares usernames must match shared_by")
        if not math.isclose(sum(item["share"] for item in shares), float(amount), abs_tol=0.000001):
            raise ValueError(f"{label}: shares must add up to amount")
        transaction_data.append({
            "trip_name": trip_name,
            "amount": float(amount),
            "description": text(row["description"]),
            "paid_by": text(row["paid_by"]),
            "shared_by": shared_by,
            "shares": shares,
            "is_expense": text(row.get("is_expense", "true")).lower() not in {"false", "0", "no"},
        })

    members_by_trip = {trip["name"]: set(trip["members"]) for trip in trip_data}
    for transaction in transaction_data:
        members = members_by_trip[transaction["trip_name"]]
        referenced = {transaction["paid_by"], *transaction["shared_by"]}
        unknown = referenced - members
        if unknown:
            raise ValueError(f"Transaction for {transaction['trip_name']!r} references non-member(s): {', '.join(sorted(unknown))}")
    return [{"trip": trip, "transactions": [t for t in transaction_data if t["trip_name"] == trip["name"]]} for trip in trip_data]


class ApiClient:
    def __init__(self, base_url: str, username: str, password: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.username = username
        response = requests.post(
            f"{self.base_url}/login",
            json={"Username": username, "Password": password},
            timeout=30,
        )
        response.raise_for_status()
        self.session = requests.Session()
        self.session.headers.update({"x-access-token": response.json()["token"]})

    def post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        response = self.session.post(f"{self.base_url}{path}", json=payload, timeout=30)
        response.raise_for_status()
        return response.json()


def import_data(groups: list[dict[str, Any]], client: ApiClient | None, dry_run: bool) -> None:
    for group in groups:
        trip = group["trip"]
        print(f"{('[dry-run] ' if dry_run else '')}Trip: {trip['name']} ({len(group['transactions'])} transactions)")
        if dry_run:
            continue
        assert client is not None
        event = client.post("/events", {"eventName": trip["name"], "eventDescription": trip["description"]})
        event_name = quote(trip["name"], safe="")
        members_to_add = [member for member in trip["members"] if member != client.username]
        if members_to_add:
            client.post(f"/events/{event_name}/members", {"memberList": members_to_add})
        for transaction in group["transactions"]:
            client.post(f"/events/{event_name}/transactions", {
                "Amount": transaction["amount"],
                "description": transaction["description"],
                "paidByUserName": transaction["paid_by"],
                "sharedByUserNames": transaction["shares"],
                "isExpense": transaction["is_expense"],
            })
        print(f"  created event {event.get('eventID', '?')}")


def create_template(path: Path) -> None:
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        pd.DataFrame([{"trip_name": "Japan 2023", "description": "Historical trip", "members": "alice,bob"}]).to_excel(writer, sheet_name="Trips", index=False)
        pd.DataFrame([
            {"trip_name": "Japan 2023", "amount": 120.50, "description": "Hotel", "paid_by": "alice", "shared_by": "alice,bob", "shares": "", "is_expense": True},
            {"trip_name": "Japan 2023", "amount": 30, "description": "Train", "paid_by": "bob", "shared_by": "alice,bob", "shares": "alice:10,bob:20", "is_expense": True},
        ]).to_excel(writer, sheet_name="Transactions", index=False)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workbook", type=Path, help="Excel workbook containing Trips and Transactions sheets")
    parser.add_argument("--base-url", default="http://localhost:5000", help="API base URL")
    parser.add_argument("--username", help="API login username")
    parser.add_argument("--password", help="API login password")
    parser.add_argument("--dry-run", action="store_true", help="Validate and print trips without calling the API")
    parser.add_argument("--create-template", action="store_true", help="Create a sample workbook at the workbook path")
    args = parser.parse_args()

    if args.create_template:
        create_template(args.workbook)
        print(f"Created {args.workbook}")
        return
    trips, transactions = load_workbook(args.workbook)
    groups = validate(trips, transactions)
    if args.dry_run:
        import_data(groups, None, dry_run=True)
        return
    if not args.username or not args.password:
        parser.error("--username and --password are required unless --dry-run or --create-template is used")
    import_data(groups, ApiClient(args.base_url, args.username, args.password), dry_run=False)


if __name__ == "__main__":
    main()