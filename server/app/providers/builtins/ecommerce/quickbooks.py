"""
QuickBooks Online Provider for ConnectorHub.
Loads and registers 147 actions with exact route definitions and parameters.
"""
import json
import re
import urllib.parse
from typing import Dict, Any, Optional, List
import httpx

from app.providers.base import Provider, Action
from app.providers.catalog import get_provider_actions
from app.core.ssrf import assert_public_url, execute_guarded_request

PROD_API_BASE = "https://quickbooks.api.intuit.com"
SANDBOX_API_BASE = "https://sandbox-quickbooks.api.intuit.com"

def _resolve_base_url(credential: Optional[Dict[str, Any]]) -> str:
    cred = credential or {}
    if cred.get("sandbox") or cred.get("environment") == "sandbox":
        return SANDBOX_API_BASE
    return PROD_API_BASE

def _extract_token(credential: Optional[Dict[str, Any]]) -> str:
    cred = credential or {}
    for k in ["accessToken", "token", "access_token", "apiKey"]:
        if cred.get(k):
            return str(cred[k]).strip()
    raise ValueError("QuickBooks OAuth token required. Please connect your QuickBooks account first.")

def _extract_realm_id(credential: Optional[Dict[str, Any]], input_data: Optional[Dict[str, Any]] = None) -> str:
    cred = credential or {}
    inp = input_data or {}
    for src in [inp, cred]:
        for k in ["realmId", "realm_id", "companyId", "company_id"]:
            if src.get(k):
                return str(src[k]).strip()
    return "company_realm"

def _headers(token: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "ConnectorHub/1.0"
    }

ROUTES: Dict[str, List[Any]] = {
    "batch": [
        "POST",
        "/v3/company/{realmId}/batch",
        [
            "realmId"
        ],
        [
            "minorversion"
        ]
    ],
    "create_account": [
        "POST",
        "/v3/company/{realmId}/account",
        [
            "realmId"
        ],
        [
            "minorversion"
        ]
    ],
    "create_bill": [
        "POST",
        "/v3/company/{realmId}/bill",
        [
            "realmId"
        ],
        [
            "minorversion"
        ]
    ],
    "create_bill_payment": [
        "POST",
        "/v3/company/{realmId}/bill_payment",
        [
            "realmId"
        ],
        [
            "minorversion"
        ]
    ],
    "create_credit_memo": [
        "POST",
        "/v3/company/{realmId}/credit_memo",
        [
            "realmId"
        ],
        [
            "minorversion"
        ]
    ],
    "create_credit_term": [
        "POST",
        "/v3/company/{realmId}/credit_term",
        [
            "realmId"
        ],
        [
            "minorversion"
        ]
    ],
    "create_customer": [
        "POST",
        "/v3/company/{realmId}/customer",
        [
            "realmId"
        ],
        [
            "minorversion"
        ]
    ],
    "create_department": [
        "POST",
        "/v3/company/{realmId}/department",
        [
            "realmId"
        ],
        [
            "minorversion"
        ]
    ],
    "create_deposit": [
        "POST",
        "/v3/company/{realmId}/deposit",
        [
            "realmId"
        ],
        [
            "minorversion"
        ]
    ],
    "create_employee": [
        "POST",
        "/v3/company/{realmId}/employee",
        [
            "realmId"
        ],
        [
            "minorversion"
        ]
    ],
    "create_estimate": [
        "POST",
        "/v3/company/{realmId}/estimate",
        [
            "realmId"
        ],
        [
            "minorversion"
        ]
    ],
    "create_invoice": [
        "POST",
        "/v3/company/{realmId}/invoice",
        [
            "realmId"
        ],
        [
            "minorversion"
        ]
    ],
    "create_journal_code": [
        "POST",
        "/v3/company/{realmId}/journal_code",
        [
            "realmId"
        ],
        [
            "minorversion"
        ]
    ],
    "create_journal_entry": [
        "POST",
        "/v3/company/{realmId}/journal_entry",
        [
            "realmId"
        ],
        [
            "minorversion"
        ]
    ],
    "create_payment": [
        "POST",
        "/v3/company/{realmId}/payment",
        [
            "realmId"
        ],
        [
            "minorversion"
        ]
    ],
    "create_payment_method": [
        "POST",
        "/v3/company/{realmId}/payment_method",
        [
            "realmId"
        ],
        [
            "minorversion"
        ]
    ],
    "create_product": [
        "POST",
        "/v3/company/{realmId}/product",
        [
            "realmId"
        ],
        [
            "minorversion"
        ]
    ],
    "create_purchase": [
        "POST",
        "/v3/company/{realmId}/purchase",
        [
            "realmId"
        ],
        [
            "minorversion"
        ]
    ],
    "create_purchase_order": [
        "POST",
        "/v3/company/{realmId}/purchase_order",
        [
            "realmId"
        ],
        [
            "minorversion"
        ]
    ],
    "create_record": [
        "POST",
        "/v3/company/{realmId}/record",
        [
            "realmId"
        ],
        [
            "minorversion"
        ]
    ],
    "create_refund_receipt": [
        "POST",
        "/v3/company/{realmId}/refund_receipt",
        [
            "realmId"
        ],
        [
            "minorversion"
        ]
    ],
    "create_sales_receipt": [
        "POST",
        "/v3/company/{realmId}/sales_receipt",
        [
            "realmId"
        ],
        [
            "minorversion"
        ]
    ],
    "create_tax_agency": [
        "POST",
        "/v3/company/{realmId}/tax_agency",
        [
            "realmId"
        ],
        [
            "minorversion"
        ]
    ],
    "create_time_activity": [
        "POST",
        "/v3/company/{realmId}/time_activity",
        [
            "realmId"
        ],
        [
            "minorversion"
        ]
    ],
    "create_transfer": [
        "POST",
        "/v3/company/{realmId}/transfer",
        [
            "realmId"
        ],
        [
            "minorversion"
        ]
    ],
    "create_vendor": [
        "POST",
        "/v3/company/{realmId}/vendor",
        [
            "realmId"
        ],
        [
            "minorversion"
        ]
    ],
    "create_vendor_credit": [
        "POST",
        "/v3/company/{realmId}/vendor_credit",
        [
            "realmId"
        ],
        [
            "minorversion"
        ]
    ],
    "delete_account": [
        "POST",
        "/v3/company/{realmId}/account?operation=delete",
        [
            "realmId"
        ],
        [
            "minorversion"
        ]
    ],
    "delete_attachment": [
        "POST",
        "/v3/company/{realmId}/attachment?operation=delete",
        [
            "realmId"
        ],
        [
            "minorversion"
        ]
    ],
    "delete_bill": [
        "POST",
        "/v3/company/{realmId}/bill?operation=delete",
        [
            "realmId"
        ],
        [
            "minorversion"
        ]
    ],
    "delete_bill_payment": [
        "POST",
        "/v3/company/{realmId}/bill_payment?operation=delete",
        [
            "realmId"
        ],
        [
            "minorversion"
        ]
    ],
    "delete_credit_memo": [
        "POST",
        "/v3/company/{realmId}/credit_memo?operation=delete",
        [
            "realmId"
        ],
        [
            "minorversion"
        ]
    ],
    "delete_credit_term": [
        "POST",
        "/v3/company/{realmId}/credit_term?operation=delete",
        [
            "realmId"
        ],
        [
            "minorversion"
        ]
    ],
    "delete_customer": [
        "POST",
        "/v3/company/{realmId}/customer?operation=delete",
        [
            "realmId"
        ],
        [
            "minorversion"
        ]
    ],
    "delete_department": [
        "POST",
        "/v3/company/{realmId}/department?operation=delete",
        [
            "realmId"
        ],
        [
            "minorversion"
        ]
    ],
    "delete_deposit": [
        "POST",
        "/v3/company/{realmId}/deposit?operation=delete",
        [
            "realmId"
        ],
        [
            "minorversion"
        ]
    ],
    "delete_employee": [
        "POST",
        "/v3/company/{realmId}/employee?operation=delete",
        [
            "realmId"
        ],
        [
            "minorversion"
        ]
    ],
    "delete_estimate": [
        "POST",
        "/v3/company/{realmId}/estimate?operation=delete",
        [
            "realmId"
        ],
        [
            "minorversion"
        ]
    ],
    "delete_invoice": [
        "POST",
        "/v3/company/{realmId}/invoice?operation=delete",
        [
            "realmId"
        ],
        [
            "minorversion"
        ]
    ],
    "delete_journal_entry": [
        "POST",
        "/v3/company/{realmId}/journal_entry?operation=delete",
        [
            "realmId"
        ],
        [
            "minorversion"
        ]
    ],
    "delete_payment": [
        "POST",
        "/v3/company/{realmId}/payment?operation=delete",
        [
            "realmId"
        ],
        [
            "minorversion"
        ]
    ],
    "delete_payment_method": [
        "POST",
        "/v3/company/{realmId}/payment_method?operation=delete",
        [
            "realmId"
        ],
        [
            "minorversion"
        ]
    ],
    "delete_product": [
        "POST",
        "/v3/company/{realmId}/product?operation=delete",
        [
            "realmId"
        ],
        [
            "minorversion"
        ]
    ],
    "delete_purchase": [
        "POST",
        "/v3/company/{realmId}/purchase?operation=delete",
        [
            "realmId"
        ],
        [
            "minorversion"
        ]
    ],
    "delete_purchase_order": [
        "POST",
        "/v3/company/{realmId}/purchase_order?operation=delete",
        [
            "realmId"
        ],
        [
            "minorversion"
        ]
    ],
    "delete_record": [
        "POST",
        "/v3/company/{realmId}/record?operation=delete",
        [
            "realmId"
        ],
        [
            "minorversion"
        ]
    ],
    "delete_refund_receipt": [
        "POST",
        "/v3/company/{realmId}/refund_receipt?operation=delete",
        [
            "realmId"
        ],
        [
            "minorversion"
        ]
    ],
    "delete_sales_receipt": [
        "POST",
        "/v3/company/{realmId}/sales_receipt?operation=delete",
        [
            "realmId"
        ],
        [
            "minorversion"
        ]
    ],
    "delete_time_activity": [
        "POST",
        "/v3/company/{realmId}/time_activity?operation=delete",
        [
            "realmId"
        ],
        [
            "minorversion"
        ]
    ],
    "delete_transfer": [
        "POST",
        "/v3/company/{realmId}/transfer?operation=delete",
        [
            "realmId"
        ],
        [
            "minorversion"
        ]
    ],
    "delete_vendor": [
        "POST",
        "/v3/company/{realmId}/vendor?operation=delete",
        [
            "realmId"
        ],
        [
            "minorversion"
        ]
    ],
    "delete_vendor_credit": [
        "POST",
        "/v3/company/{realmId}/vendor_credit?operation=delete",
        [
            "realmId"
        ],
        [
            "minorversion"
        ]
    ],
    "get_account": [
        "GET",
        "/v3/company/{realmId}/account/{id}",
        [
            "realmId",
            "id"
        ],
        [
            "minorversion"
        ]
    ],
    "get_attachment": [
        "GET",
        "/v3/company/{realmId}/attachment/{id}",
        [
            "realmId",
            "id"
        ],
        [
            "minorversion"
        ]
    ],
    "get_attachment_download_url": [
        "GET",
        "/v3/company/{realmId}/attachment_download_url/{id}",
        [
            "realmId",
            "id"
        ],
        [
            "minorversion"
        ]
    ],
    "get_bill": [
        "GET",
        "/v3/company/{realmId}/bill/{id}",
        [
            "realmId",
            "id"
        ],
        [
            "minorversion"
        ]
    ],
    "get_bill_payment": [
        "GET",
        "/v3/company/{realmId}/bill_payment/{id}",
        [
            "realmId",
            "id"
        ],
        [
            "minorversion"
        ]
    ],
    "get_changes": [
        "GET",
        "/v3/company/{realmId}/cdc",
        [
            "realmId"
        ],
        [
            "minorversion",
            "entities",
            "changedSince"
        ]
    ],
    "get_company_info": [
        "GET",
        "/v3/company/{realmId}/company_info/{id}",
        [
            "realmId",
            "id"
        ],
        [
            "minorversion"
        ]
    ],
    "get_credit_memo": [
        "GET",
        "/v3/company/{realmId}/credit_memo/{id}",
        [
            "realmId",
            "id"
        ],
        [
            "minorversion"
        ]
    ],
    "get_credit_term": [
        "GET",
        "/v3/company/{realmId}/credit_term/{id}",
        [
            "realmId",
            "id"
        ],
        [
            "minorversion"
        ]
    ],
    "get_customer": [
        "GET",
        "/v3/company/{realmId}/customer/{id}",
        [
            "realmId",
            "id"
        ],
        [
            "minorversion"
        ]
    ],
    "get_department": [
        "GET",
        "/v3/company/{realmId}/department/{id}",
        [
            "realmId",
            "id"
        ],
        [
            "minorversion"
        ]
    ],
    "get_deposit": [
        "GET",
        "/v3/company/{realmId}/deposit/{id}",
        [
            "realmId",
            "id"
        ],
        [
            "minorversion"
        ]
    ],
    "get_employee": [
        "GET",
        "/v3/company/{realmId}/employee/{id}",
        [
            "realmId",
            "id"
        ],
        [
            "minorversion"
        ]
    ],
    "get_estimate": [
        "GET",
        "/v3/company/{realmId}/estimate/{id}",
        [
            "realmId",
            "id"
        ],
        [
            "minorversion"
        ]
    ],
    "get_exchange_rate": [
        "GET",
        "/v3/company/{realmId}/exchange_rate/{id}",
        [
            "realmId",
            "id"
        ],
        [
            "minorversion"
        ]
    ],
    "get_invoice": [
        "GET",
        "/v3/company/{realmId}/invoice/{id}",
        [
            "realmId",
            "id"
        ],
        [
            "minorversion"
        ]
    ],
    "get_journal_code": [
        "GET",
        "/v3/company/{realmId}/journal_code/{id}",
        [
            "realmId",
            "id"
        ],
        [
            "minorversion"
        ]
    ],
    "get_journal_entry": [
        "GET",
        "/v3/company/{realmId}/journal_entry/{id}",
        [
            "realmId",
            "id"
        ],
        [
            "minorversion"
        ]
    ],
    "get_payment": [
        "GET",
        "/v3/company/{realmId}/payment/{id}",
        [
            "realmId",
            "id"
        ],
        [
            "minorversion"
        ]
    ],
    "get_payment_method": [
        "GET",
        "/v3/company/{realmId}/payment_method/{id}",
        [
            "realmId",
            "id"
        ],
        [
            "minorversion"
        ]
    ],
    "get_preferences": [
        "GET",
        "/v3/company/{realmId}/preferences/{id}",
        [
            "realmId",
            "id"
        ],
        [
            "minorversion"
        ]
    ],
    "get_product": [
        "GET",
        "/v3/company/{realmId}/product/{id}",
        [
            "realmId",
            "id"
        ],
        [
            "minorversion"
        ]
    ],
    "get_purchase": [
        "GET",
        "/v3/company/{realmId}/purchase/{id}",
        [
            "realmId",
            "id"
        ],
        [
            "minorversion"
        ]
    ],
    "get_purchase_order": [
        "GET",
        "/v3/company/{realmId}/purchase_order/{id}",
        [
            "realmId",
            "id"
        ],
        [
            "minorversion"
        ]
    ],
    "get_record": [
        "GET",
        "/v3/company/{realmId}/record/{id}",
        [
            "realmId",
            "id"
        ],
        [
            "minorversion"
        ]
    ],
    "get_refund_receipt": [
        "GET",
        "/v3/company/{realmId}/refund_receipt/{id}",
        [
            "realmId",
            "id"
        ],
        [
            "minorversion"
        ]
    ],
    "get_report": [
        "GET",
        "/v3/company/{realmId}/reports/Report",
        [
            "realmId"
        ],
        [
            "minorversion",
            "date_macro",
            "start_date",
            "end_date",
            "accounting_method",
            "columns"
        ]
    ],
    "get_sales_receipt": [
        "GET",
        "/v3/company/{realmId}/sales_receipt/{id}",
        [
            "realmId",
            "id"
        ],
        [
            "minorversion"
        ]
    ],
    "get_tax_agency": [
        "GET",
        "/v3/company/{realmId}/tax_agency/{id}",
        [
            "realmId",
            "id"
        ],
        [
            "minorversion"
        ]
    ],
    "get_tax_code": [
        "GET",
        "/v3/company/{realmId}/tax_code/{id}",
        [
            "realmId",
            "id"
        ],
        [
            "minorversion"
        ]
    ],
    "get_tax_rate": [
        "GET",
        "/v3/company/{realmId}/tax_rate/{id}",
        [
            "realmId",
            "id"
        ],
        [
            "minorversion"
        ]
    ],
    "get_time_activity": [
        "GET",
        "/v3/company/{realmId}/time_activity/{id}",
        [
            "realmId",
            "id"
        ],
        [
            "minorversion"
        ]
    ],
    "get_transfer": [
        "GET",
        "/v3/company/{realmId}/transfer/{id}",
        [
            "realmId",
            "id"
        ],
        [
            "minorversion"
        ]
    ],
    "get_vendor": [
        "GET",
        "/v3/company/{realmId}/vendor/{id}",
        [
            "realmId",
            "id"
        ],
        [
            "minorversion"
        ]
    ],
    "get_vendor_credit": [
        "GET",
        "/v3/company/{realmId}/vendor_credit/{id}",
        [
            "realmId",
            "id"
        ],
        [
            "minorversion"
        ]
    ],
    "list_accounts": [
        "GET",
        "/v3/company/{realmId}/query",
        [
            "realmId"
        ],
        [
            "minorversion",
            "query",
            "max_results",
            "start_position"
        ]
    ],
    "list_attachments": [
        "GET",
        "/v3/company/{realmId}/query",
        [
            "realmId"
        ],
        [
            "minorversion",
            "query",
            "max_results",
            "start_position"
        ]
    ],
    "list_bill_payments": [
        "GET",
        "/v3/company/{realmId}/query",
        [
            "realmId"
        ],
        [
            "minorversion",
            "query",
            "max_results",
            "start_position"
        ]
    ],
    "list_bills": [
        "GET",
        "/v3/company/{realmId}/query",
        [
            "realmId"
        ],
        [
            "minorversion",
            "query",
            "max_results",
            "start_position"
        ]
    ],
    "list_budgets": [
        "GET",
        "/v3/company/{realmId}/query",
        [
            "realmId"
        ],
        [
            "minorversion",
            "query",
            "max_results",
            "start_position"
        ]
    ],
    "list_classes": [
        "GET",
        "/v3/company/{realmId}/query",
        [
            "realmId"
        ],
        [
            "minorversion",
            "query",
            "max_results",
            "start_position"
        ]
    ],
    "list_credit_memos": [
        "GET",
        "/v3/company/{realmId}/query",
        [
            "realmId"
        ],
        [
            "minorversion",
            "query",
            "max_results",
            "start_position"
        ]
    ],
    "list_credit_terms": [
        "GET",
        "/v3/company/{realmId}/query",
        [
            "realmId"
        ],
        [
            "minorversion",
            "query",
            "max_results",
            "start_position"
        ]
    ],
    "list_currencies": [
        "GET",
        "/v3/company/{realmId}/query",
        [
            "realmId"
        ],
        [
            "minorversion",
            "query",
            "max_results",
            "start_position"
        ]
    ],
    "list_customers": [
        "GET",
        "/v3/company/{realmId}/query",
        [
            "realmId"
        ],
        [
            "minorversion",
            "query",
            "max_results",
            "start_position"
        ]
    ],
    "list_departments": [
        "GET",
        "/v3/company/{realmId}/query",
        [
            "realmId"
        ],
        [
            "minorversion",
            "query",
            "max_results",
            "start_position"
        ]
    ],
    "list_deposits": [
        "GET",
        "/v3/company/{realmId}/query",
        [
            "realmId"
        ],
        [
            "minorversion",
            "query",
            "max_results",
            "start_position"
        ]
    ],
    "list_employees": [
        "GET",
        "/v3/company/{realmId}/query",
        [
            "realmId"
        ],
        [
            "minorversion",
            "query",
            "max_results",
            "start_position"
        ]
    ],
    "list_estimates": [
        "GET",
        "/v3/company/{realmId}/query",
        [
            "realmId"
        ],
        [
            "minorversion",
            "query",
            "max_results",
            "start_position"
        ]
    ],
    "list_invoices": [
        "GET",
        "/v3/company/{realmId}/query",
        [
            "realmId"
        ],
        [
            "minorversion",
            "query",
            "max_results",
            "start_position"
        ]
    ],
    "list_journal_codes": [
        "GET",
        "/v3/company/{realmId}/query",
        [
            "realmId"
        ],
        [
            "minorversion",
            "query",
            "max_results",
            "start_position"
        ]
    ],
    "list_journal_entries": [
        "GET",
        "/v3/company/{realmId}/query",
        [
            "realmId"
        ],
        [
            "minorversion",
            "query",
            "max_results",
            "start_position"
        ]
    ],
    "list_payment_methods": [
        "GET",
        "/v3/company/{realmId}/query",
        [
            "realmId"
        ],
        [
            "minorversion",
            "query",
            "max_results",
            "start_position"
        ]
    ],
    "list_payments": [
        "GET",
        "/v3/company/{realmId}/query",
        [
            "realmId"
        ],
        [
            "minorversion",
            "query",
            "max_results",
            "start_position"
        ]
    ],
    "list_products": [
        "GET",
        "/v3/company/{realmId}/query",
        [
            "realmId"
        ],
        [
            "minorversion",
            "query",
            "max_results",
            "start_position"
        ]
    ],
    "list_purchase_orders": [
        "GET",
        "/v3/company/{realmId}/query",
        [
            "realmId"
        ],
        [
            "minorversion",
            "query",
            "max_results",
            "start_position"
        ]
    ],
    "list_purchases": [
        "GET",
        "/v3/company/{realmId}/query",
        [
            "realmId"
        ],
        [
            "minorversion",
            "query",
            "max_results",
            "start_position"
        ]
    ],
    "list_records": [
        "GET",
        "/v3/company/{realmId}/query",
        [
            "realmId"
        ],
        [
            "minorversion",
            "query",
            "max_results",
            "start_position"
        ]
    ],
    "list_refund_receipts": [
        "GET",
        "/v3/company/{realmId}/query",
        [
            "realmId"
        ],
        [
            "minorversion",
            "query",
            "max_results",
            "start_position"
        ]
    ],
    "list_sales_receipts": [
        "GET",
        "/v3/company/{realmId}/query",
        [
            "realmId"
        ],
        [
            "minorversion",
            "query",
            "max_results",
            "start_position"
        ]
    ],
    "list_tax_agencies": [
        "GET",
        "/v3/company/{realmId}/query",
        [
            "realmId"
        ],
        [
            "minorversion",
            "query",
            "max_results",
            "start_position"
        ]
    ],
    "list_tax_codes": [
        "GET",
        "/v3/company/{realmId}/query",
        [
            "realmId"
        ],
        [
            "minorversion",
            "query",
            "max_results",
            "start_position"
        ]
    ],
    "list_tax_rates": [
        "GET",
        "/v3/company/{realmId}/query",
        [
            "realmId"
        ],
        [
            "minorversion",
            "query",
            "max_results",
            "start_position"
        ]
    ],
    "list_time_activities": [
        "GET",
        "/v3/company/{realmId}/query",
        [
            "realmId"
        ],
        [
            "minorversion",
            "query",
            "max_results",
            "start_position"
        ]
    ],
    "list_transfers": [
        "GET",
        "/v3/company/{realmId}/query",
        [
            "realmId"
        ],
        [
            "minorversion",
            "query",
            "max_results",
            "start_position"
        ]
    ],
    "list_vendor_credits": [
        "GET",
        "/v3/company/{realmId}/query",
        [
            "realmId"
        ],
        [
            "minorversion",
            "query",
            "max_results",
            "start_position"
        ]
    ],
    "list_vendors": [
        "GET",
        "/v3/company/{realmId}/query",
        [
            "realmId"
        ],
        [
            "minorversion",
            "query",
            "max_results",
            "start_position"
        ]
    ],
    "ping": [
        "GET",
        "/v3/company/{realmId}/companyinfo/{realmId}",
        [
            "realmId"
        ],
        [
            "minorversion"
        ]
    ],
    "update_attachment": [
        "POST",
        "/v3/company/{realmId}/attachment?operation=update",
        [
            "realmId"
        ],
        [
            "minorversion"
        ]
    ],
    "update_bill": [
        "POST",
        "/v3/company/{realmId}/bill?operation=update",
        [
            "realmId"
        ],
        [
            "minorversion"
        ]
    ],
    "update_bill_payment": [
        "POST",
        "/v3/company/{realmId}/bill_payment?operation=update",
        [
            "realmId"
        ],
        [
            "minorversion"
        ]
    ],
    "update_credit_memo": [
        "POST",
        "/v3/company/{realmId}/credit_memo?operation=update",
        [
            "realmId"
        ],
        [
            "minorversion"
        ]
    ],
    "update_credit_term": [
        "POST",
        "/v3/company/{realmId}/credit_term?operation=update",
        [
            "realmId"
        ],
        [
            "minorversion"
        ]
    ],
    "update_customer": [
        "POST",
        "/v3/company/{realmId}/customer?operation=update",
        [
            "realmId"
        ],
        [
            "minorversion"
        ]
    ],
    "update_department": [
        "POST",
        "/v3/company/{realmId}/department?operation=update",
        [
            "realmId"
        ],
        [
            "minorversion"
        ]
    ],
    "update_deposit": [
        "POST",
        "/v3/company/{realmId}/deposit?operation=update",
        [
            "realmId"
        ],
        [
            "minorversion"
        ]
    ],
    "update_employee": [
        "POST",
        "/v3/company/{realmId}/employee?operation=update",
        [
            "realmId"
        ],
        [
            "minorversion"
        ]
    ],
    "update_estimate": [
        "POST",
        "/v3/company/{realmId}/estimate?operation=update",
        [
            "realmId"
        ],
        [
            "minorversion"
        ]
    ],
    "update_invoice": [
        "POST",
        "/v3/company/{realmId}/invoice?operation=update",
        [
            "realmId"
        ],
        [
            "minorversion"
        ]
    ],
    "update_journal_code": [
        "POST",
        "/v3/company/{realmId}/journal_code?operation=update",
        [
            "realmId"
        ],
        [
            "minorversion"
        ]
    ],
    "update_journal_entry": [
        "POST",
        "/v3/company/{realmId}/journal_entry?operation=update",
        [
            "realmId"
        ],
        [
            "minorversion"
        ]
    ],
    "update_payment": [
        "POST",
        "/v3/company/{realmId}/payment?operation=update",
        [
            "realmId"
        ],
        [
            "minorversion"
        ]
    ],
    "update_product": [
        "POST",
        "/v3/company/{realmId}/product?operation=update",
        [
            "realmId"
        ],
        [
            "minorversion"
        ]
    ],
    "update_purchase": [
        "POST",
        "/v3/company/{realmId}/purchase?operation=update",
        [
            "realmId"
        ],
        [
            "minorversion"
        ]
    ],
    "update_purchase_order": [
        "POST",
        "/v3/company/{realmId}/purchase_order?operation=update",
        [
            "realmId"
        ],
        [
            "minorversion"
        ]
    ],
    "update_record": [
        "POST",
        "/v3/company/{realmId}/record?operation=update",
        [
            "realmId"
        ],
        [
            "minorversion"
        ]
    ],
    "update_refund_receipt": [
        "POST",
        "/v3/company/{realmId}/refund_receipt?operation=update",
        [
            "realmId"
        ],
        [
            "minorversion"
        ]
    ],
    "update_sales_receipt": [
        "POST",
        "/v3/company/{realmId}/sales_receipt?operation=update",
        [
            "realmId"
        ],
        [
            "minorversion"
        ]
    ],
    "update_time_activity": [
        "POST",
        "/v3/company/{realmId}/time_activity?operation=update",
        [
            "realmId"
        ],
        [
            "minorversion"
        ]
    ],
    "update_transfer": [
        "POST",
        "/v3/company/{realmId}/transfer?operation=update",
        [
            "realmId"
        ],
        [
            "minorversion"
        ]
    ],
    "update_vendor": [
        "POST",
        "/v3/company/{realmId}/vendor?operation=update",
        [
            "realmId"
        ],
        [
            "minorversion"
        ]
    ],
    "update_vendor_credit": [
        "POST",
        "/v3/company/{realmId}/vendor_credit?operation=update",
        [
            "realmId"
        ],
        [
            "minorversion"
        ]
    ],
    "upload_attachment": [
        "POST",
        "/v3/company/{realmId}/upload",
        [
            "realmId"
        ],
        [
            "minorversion"
        ]
    ],
    "void_invoice": [
        "POST",
        "/v3/company/{realmId}/invoice?operation=void",
        [
            "realmId"
        ],
        [
            "minorversion"
        ]
    ],
    "void_payment": [
        "POST",
        "/v3/company/{realmId}/payment?operation=void",
        [
            "realmId"
        ],
        [
            "minorversion"
        ]
    ]
}

class QuickBooksDynamicAction(Action):
    def __init__(self, action_meta: Dict[str, Any]):
        super().__init__(
            id=action_meta["id"],
            name=action_meta["name"],
            description=action_meta["description"],
            category=action_meta.get("category", "Accounting & Finance"),
            required_scopes=action_meta.get("required_scopes", []),
            input_schema=action_meta.get("input_schema", {"type": "object", "properties": {}})
        )
        self.action_name = action_meta["name"]
        self.route_info = ROUTES.get(self.action_name, [action_meta.get("method", "GET"), action_meta.get("endpoint", f"/{self.action_name}"), [], []])

    async def execute(self, input_data: Dict[str, Any], credential: Optional[Dict[str, Any]], client: httpx.AsyncClient) -> Dict[str, Any]:
        token = _extract_token(credential)
        base_url = _resolve_base_url(credential)
        realm_id = _extract_realm_id(credential, input_data)
        headers = _headers(token)

        req_method, path_template, path_vars, query_keys = self.route_info
        path = path_template

        # Substitute realmId
        path = path.replace("{realmId}", urllib.parse.quote(realm_id, safe=""))
        path = path.replace("{realm_id}", urllib.parse.quote(realm_id, safe=""))

        # Substitute any other path variables
        for var in path_vars:
            if var in ["realmId", "realm_id"]:
                continue
            val = input_data.get(var)
            if val is None:
                # check snake_case or camelCase
                alt = "".join(["_" + c.lower() if c.isupper() else c for c in var]).lstrip("_")
                val = input_data.get(alt)
            if val is not None:
                path = path.replace("{" + var + "}", urllib.parse.quote(str(val), safe=""))

        # Strip unreplaced optional path placeholders
        path = re.sub(r"/\{[^}]+\}", "", path)

        target_url = f"{base_url}{path}"
        assert_public_url(target_url)

        params: Dict[str, Any] = {"minorversion": "75"}
        body: Dict[str, Any] = {}

        for k, v in input_data.items():
            if k in ["realmId", "realm_id"] or k in path_vars:
                continue
            if k in query_keys or (req_method == "GET"):
                params[k] = v
            else:
                body[k] = v

        resp = await execute_guarded_request(
            client=client,
            method=req_method,
            url=target_url,
            headers=headers,
            params=params if params else None,
            json_body=body if (req_method in ["POST", "PUT", "PATCH"] and body) else None
        )

        try:
            data = resp.json()
        except Exception:
            data = {"raw_response": resp.text}

        if resp.status_code >= 400:
            err_msg = data.get("Fault", {}).get("Error", [{}])[0].get("Message") or data.get("message") or resp.text
            raise ValueError(f"QuickBooks API error ({resp.status_code}): {err_msg}")

        return {"status": resp.status_code, "data": data}


class QuickBooksProvider(Provider):
    def __init__(self):
        super().__init__(
            service="quickbooks",
            display_name="QuickBooks Online",
            category="Accounting & Finance",
            auth_types=["oauth2"],
            description="Intuit QuickBooks Online Accounting integration suite with 147 actions.",
            auth_configs=[
                {
                    "type": "oauth2",
                    "fields": [
                        {
                            "key": "realmId",
                            "label": "Company ID (Realm ID)",
                            "type": "text",
                            "required": False,
                            "placeholder": "1234567890",
                            "description": "QuickBooks Company ID (Realm ID). Automatically filled during OAuth if available."
                        }
                    ]
                }
            ]
        )
        for act in get_provider_actions("quickbooks"):
            self.register_action(QuickBooksDynamicAction(act))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        token = _extract_token(credential)
        base_url = _resolve_base_url(credential)
        realm_id = _extract_realm_id(credential)
        headers = _headers(token)

        val_url = f"{base_url}/v3/company/{realm_id}/companyinfo/{realm_id}"
        assert_public_url(val_url)

        resp = await execute_guarded_request(
            client=client,
            method="GET",
            url=val_url,
            headers=headers,
            params={"minorversion": "75"}
        )

        if resp.status_code in [401, 403]:
            raise ValueError(f"Invalid QuickBooks credentials: {resp.status_code} {resp.text}")
        elif resp.status_code >= 400:
            raise ValueError(f"QuickBooks validation failed: {resp.status_code} {resp.text}")

        try:
            res_data = resp.json()
            comp_info = res_data.get("CompanyInfo", {})
            comp_name = comp_info.get("CompanyName") or realm_id
        except Exception:
            comp_name = realm_id

        return {
            "account_id": realm_id,
            "display_name": f"QuickBooks ({comp_name})"
        }
