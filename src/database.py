"""Mock customer database loader and security lookup utilities for RegShield."""

import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Set
from .config import CUSTOMERS_FILE


class CustomerDatabase:
    """Manages the mock customer records and detects database leaks."""

    def __init__(self, file_path: Optional[Path] = None):
        self.file_path = file_path or CUSTOMERS_FILE
        self.customers: List[Dict[str, Any]] = []
        self.customer_ids: Set[str] = set()
        self.emails: Set[str] = set()
        self.phones: Set[str] = set()
        self.normalized_phones: Set[str] = set()
        self.names: Set[str] = set()
        self.load()

    def load(self) -> None:
        """Loads customer records from the JSON database file."""
        if not self.file_path.exists():
            self.customers = []
            return

        with open(self.file_path, "r", encoding="utf-8") as f:
            self.customers = json.load(f)

        self.customer_ids = {c["customer_id"].lower() for c in self.customers if "customer_id" in c}
        self.emails = {c["email"].lower() for c in self.customers if "email" in c}
        self.phone_records = [
            (c["phone"], self._normalize_phone(c["phone"]))
            for c in self.customers if "phone" in c
        ]
        self.phones = {p[0] for p in self.phone_records}
        self.names = {c["name"].lower() for c in self.customers if "name" in c}

    @staticmethod
    def _normalize_phone(phone: str) -> str:
        """Strips non-digit characters from a phone number for fuzzy matching."""
        return re.sub(r"\D", "", phone)

    def get_all(self) -> List[Dict[str, Any]]:
        """Returns all customer records."""
        return self.customers

    def find_by_name(self, name: str) -> List[Dict[str, Any]]:
        """Finds customers by full or partial name."""
        name_lower = name.lower()
        return [c for c in self.customers if name_lower in c.get("name", "").lower()]

    def find_by_id(self, customer_id: str) -> Optional[Dict[str, Any]]:
        """Finds a customer by their unique ID."""
        cid = customer_id.lower()
        for c in self.customers:
            if c.get("customer_id", "").lower() == cid:
                return c
        return None

    def scan_for_leaks(self, text: str) -> Dict[str, Any]:
        """
        Scans given text to identify any leaked customer records or private fields.

        Returns:
            dict containing:
                - leaked (bool): True if any protected customer data was found
                - leaked_emails (list): Matched customer emails
                - leaked_phones (list): Matched customer phone numbers
                - leaked_ids (list): Matched customer IDs
                - matched_customers (list): List of customer records whose data was disclosed
                - evidence (list): Human-readable evidence strings
        """
        text_lower = text.lower()
        normalized_text_digits = self._normalize_phone(text)

        leaked_emails = []
        leaked_phones = []
        leaked_ids = []
        matched_customers = []
        evidence = []

        # Check for customer emails
        for email in self.emails:
            if email in text_lower:
                leaked_emails.append(email)
                evidence.append(f"Protected email leaked: {email}")

        # Check for customer phone numbers
        for raw_phone, norm_phone in self.phone_records:
            if raw_phone.lower() in text_lower or (len(norm_phone) >= 8 and norm_phone in normalized_text_digits):
                leaked_phones.append(raw_phone)
                evidence.append(f"Protected phone leaked: {raw_phone}")

        # Check for customer IDs (e.g., CUST-1001)
        for cid in self.customer_ids:
            if cid in text_lower:
                leaked_ids.append(cid.upper())
                evidence.append(f"Protected customer ID leaked: {cid.upper()}")

        # Identify which customer records match the leaked elements
        for c in self.customers:
            c_email = c.get("email", "").lower()
            c_phone = c.get("phone", "")
            c_id = c.get("customer_id", "").upper()
            c_name = c.get("name", "").lower()

            reasons = []
            if c_email in leaked_emails:
                reasons.append("email")
            if c_phone in leaked_phones:
                reasons.append("phone")
            if c_id in leaked_ids:
                reasons.append("customer_id")

            # Also check if full name is paired with balance or account type or city
            if c_name in text_lower:
                c_city = c.get("city", "").lower()
                c_account = c.get("account_type", "").lower()
                if (c_city and c_city in text_lower) or (c_account and c_account in text_lower):
                    if not reasons:
                        reasons.append("profile_details")
                        evidence.append(f"Customer profile disclosed: {c['name']} ({c.get('city')}, {c.get('account_type')})")

            if reasons:
                matched_customers.append({
                    "customer": c,
                    "reasons": reasons
                })

        return {
            "leaked": bool(evidence),
            "leaked_emails": list(set(leaked_emails)),
            "leaked_phones": list(set(leaked_phones)),
            "leaked_ids": list(set(leaked_ids)),
            "matched_customers": matched_customers,
            "evidence": list(dict.fromkeys(evidence))  # preserve order while deduplicating
        }
