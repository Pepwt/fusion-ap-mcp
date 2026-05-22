import os
import re
import traceback
import logging
from typing import Optional, Dict, Any, List

import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv
from fastmcp import FastMCP

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

mcp = FastMCP(name="Fusion_AP_MCP_Server")

# Environment
FUSION_BASE_URL = (os.getenv("FUSION_BASE_URL") or os.getenv("FUSION_URL") or "").rstrip("/")
FUSION_USER = os.getenv("FUSION_USER", "")
FUSION_PASSWORD = os.getenv("FUSION_PASSWORD", "")
USE_REAL_FUSION = os.getenv("USE_REAL_FUSION", "false").lower() == "true"
USE_MOCK_REFERENCE_VALIDATION = os.getenv("USE_MOCK_REFERENCE_VALIDATION", "false").lower() == "true"
DEFAULT_PAYMENT_METHOD_CODE = os.getenv("DEFAULT_PAYMENT_METHOD_CODE", "CHECK")
DEFAULT_INVOICE_SOURCE = os.getenv("DEFAULT_INVOICE_SOURCE", "External")
DEFAULT_INVOICE_TYPE = os.getenv("DEFAULT_INVOICE_TYPE", "Standard")

# Mock validations
ALLOWED_BUSINESS_UNITS = {
    "Vision Operations",
}

ALLOWED_SUPPLIERS = {
    "ABC Supplier",
    "Oracle Brasil",
}

ALLOWED_SUPPLIER_SITES = {
    "MAIN",
    "ABC_MAIN",
}


def log_request(tool_name: str, **kwargs):
    logger.info(f"[REQUEST] {tool_name} | Args: {kwargs}")


def log_response(tool_name: str, result: Any):
    logger.info(f"[RESPONSE] {tool_name} | Result: {result}")


def _clean(value: Optional[str]) -> str:
    return (value or "").strip()


def _fusion_auth():
    if not FUSION_USER or not FUSION_PASSWORD:
        raise ValueError("FUSION_USER e FUSION_PASSWORD precisam estar definidos no .env")
    return HTTPBasicAuth(FUSION_USER, FUSION_PASSWORD)


def _fusion_headers():
    return {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def normalize_description(description: Optional[str]) -> str:
    if description and description.strip():
        return description.strip()
    return "Invoice criada via Agent"


def _error_to_label(error: str) -> str:
    return error.split(" is required", 1)[0] if error.endswith(" is required") else error


def _extract_self_link(response_data: Dict[str, Any]) -> Optional[str]:
    links = response_data.get("links")
    if not isinstance(links, list):
        return None

    for link in links:
        if isinstance(link, dict) and link.get("rel") == "self" and link.get("href"):
            return link["href"]

    return None


def validate_invoice_payload(
    business_unit: Optional[str],
    supplier: Optional[str],
    supplier_site: Optional[str],
    invoice_number: Optional[str],
    invoice_date: Optional[str],
    amount: Optional[float],
    currency: Optional[str],
    description: Optional[str] = None,
    accounting_date: Optional[str] = None,
    terms_date: Optional[str] = None,
    payment_method_code: Optional[str] = None
) -> Dict[str, Any]:
    errors: List[str] = []

    if not _clean(business_unit):
        errors.append("business_unit is required")

    if not _clean(supplier):
        errors.append("supplier is required")

    if not _clean(supplier_site):
        errors.append("supplier_site is required")

    if not _clean(invoice_number):
        errors.append("invoice_number is required")

    if not _clean(invoice_date):
        errors.append("invoice_date is required")
    else:
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", invoice_date.strip()):
            errors.append("invoice_date must be in YYYY-MM-DD format")

    if amount is None:
        errors.append("amount is required")
    else:
        try:
            amount_value = float(amount)
            if amount_value <= 0:
                errors.append("amount must be greater than 0")
        except (TypeError, ValueError):
            errors.append("amount must be numeric")

    if not _clean(currency):
        errors.append("currency is required")

    if USE_REAL_FUSION:
        for field_name, field_value in {
            "accounting_date": accounting_date or invoice_date,
            "terms_date": terms_date or invoice_date,
            "payment_method_code": payment_method_code or DEFAULT_PAYMENT_METHOD_CODE,
        }.items():
            if not _clean(field_value):
                errors.append(f"{field_name} is required")

    return {
        "valid": len(errors) == 0,
        "errors": errors
    }


def validate_supplier_context(
    business_unit: Optional[str],
    supplier: Optional[str],
    supplier_site: Optional[str]
) -> Dict[str, Any]:
    errors: List[str] = []

    if not USE_MOCK_REFERENCE_VALIDATION:
        return {
            "valid": True,
            "errors": errors
        }

    if _clean(business_unit) and business_unit not in ALLOWED_BUSINESS_UNITS:
        errors.append(f"business_unit '{business_unit}' not recognized")

    if _clean(supplier) and supplier not in ALLOWED_SUPPLIERS:
        errors.append(f"supplier '{supplier}' not recognized")

    if _clean(supplier_site) and supplier_site not in ALLOWED_SUPPLIER_SITES:
        errors.append(f"supplier_site '{supplier_site}' not recognized")

    return {
        "valid": len(errors) == 0,
        "errors": errors
    }


@mcp.tool
def get_business_unit() -> Dict[str, Any]:
    log_request("get_business_unit")

    result = {
        "business_units": [
            {
                "name": "Vision Operations",
                "code": "Vision Operations"
            }
        ]
    }

    log_response("get_business_unit", result)
    return result


@mcp.tool
def validate_supplier_context_tool(
    business_unit: Optional[str] = None,
    supplier: Optional[str] = None,
    supplier_site: Optional[str] = None
) -> Dict[str, Any]:
    log_request(
        "validate_supplier_context_tool",
        business_unit=business_unit,
        supplier=supplier,
        supplier_site=supplier_site
    )

    result = validate_supplier_context(
        business_unit=business_unit,
        supplier=supplier,
        supplier_site=supplier_site
    )

    log_response("validate_supplier_context_tool", result)
    return result


@mcp.tool
def validate_invoice_payload_tool(
    business_unit: Optional[str] = None,
    supplier: Optional[str] = None,
    supplier_site: Optional[str] = None,
    invoice_number: Optional[str] = None,
    invoice_date: Optional[str] = None,
    amount: Optional[float] = None,
    currency: Optional[str] = None,
    description: Optional[str] = None,
    accounting_date: Optional[str] = None,
    terms_date: Optional[str] = None,
    payment_method_code: Optional[str] = None
) -> Dict[str, Any]:
    log_request(
        "validate_invoice_payload_tool",
        business_unit=business_unit,
        supplier=supplier,
        supplier_site=supplier_site,
        invoice_number=invoice_number,
        invoice_date=invoice_date,
        amount=amount,
        currency=currency,
        description=description,
        accounting_date=accounting_date,
        terms_date=terms_date,
        payment_method_code=payment_method_code
    )

    result = validate_invoice_payload(
        business_unit=business_unit,
        supplier=supplier,
        supplier_site=supplier_site,
        invoice_number=invoice_number,
        invoice_date=invoice_date,
        amount=amount,
        currency=currency,
        description=description,
        accounting_date=accounting_date,
        terms_date=terms_date,
        payment_method_code=payment_method_code
    )

    log_response("validate_invoice_payload_tool", result)
    return result


@mcp.tool
def create_ap_invoice(
    business_unit: Optional[str] = None,
    supplier: Optional[str] = None,
    supplier_site: Optional[str] = None,
    invoice_number: Optional[str] = None,
    invoice_date: Optional[str] = None,
    amount: Optional[float] = None,
    currency: Optional[str] = None,
    description: Optional[str] = None,
    accounting_date: Optional[str] = None,
    terms_date: Optional[str] = None,
    payment_method_code: Optional[str] = None,
    invoice_source: Optional[str] = None,
    invoice_type: Optional[str] = None,
    distribution_combination: Optional[str] = None
) -> Dict[str, Any]:
    log_request(
        "create_ap_invoice",
        business_unit=business_unit,
        supplier=supplier,
        supplier_site=supplier_site,
        invoice_number=invoice_number,
        invoice_date=invoice_date,
        amount=amount,
        currency=currency,
        description=description,
        accounting_date=accounting_date,
        terms_date=terms_date,
        payment_method_code=payment_method_code,
        invoice_source=invoice_source,
        invoice_type=invoice_type,
        distribution_combination=distribution_combination
    )

    final_description = normalize_description(description)
    final_accounting_date = _clean(accounting_date) or _clean(invoice_date)
    final_terms_date = _clean(terms_date) or _clean(invoice_date)
    final_payment_method_code = _clean(payment_method_code) or DEFAULT_PAYMENT_METHOD_CODE
    final_invoice_source = _clean(invoice_source) or DEFAULT_INVOICE_SOURCE
    final_invoice_type = _clean(invoice_type) or DEFAULT_INVOICE_TYPE

    payload_validation = validate_invoice_payload(
        business_unit=business_unit,
        supplier=supplier,
        supplier_site=supplier_site,
        invoice_number=invoice_number,
        invoice_date=invoice_date,
        amount=amount,
        currency=currency,
        description=final_description,
        accounting_date=final_accounting_date,
        terms_date=final_terms_date,
        payment_method_code=final_payment_method_code
    )

    if not payload_validation["valid"]:
        result = {
            "status": "NEEDS_INFO",
            "message": "Campos obrigatórios faltantes",
            "missing_fields": [_error_to_label(error) for error in payload_validation["errors"]],
            "details": payload_validation["errors"]
        }
        log_response("create_ap_invoice", result)
        return result

    context_validation = validate_supplier_context(
        business_unit=business_unit,
        supplier=supplier,
        supplier_site=supplier_site
    )

    if not context_validation["valid"]:
        result = {
            "status": "NEEDS_INFO",
            "message": "Contexto de fornecedor inválido",
            "missing_or_invalid_fields": context_validation["errors"]
        }
        log_response("create_ap_invoice", result)
        return result

    if not USE_REAL_FUSION:
        result = {
            "status": "SUCCESS",
            "message": "AP Invoice preparada com sucesso (modo mock)",
            "invoice_data": {
                "business_unit": business_unit,
                "supplier": supplier,
                "supplier_site": supplier_site,
                "invoice_number": invoice_number,
                "invoice_date": invoice_date,
                "accounting_date": final_accounting_date,
                "terms_date": final_terms_date,
                "amount": amount,
                "currency": currency,
                "payment_method_code": final_payment_method_code,
                "invoice_source": final_invoice_source,
                "invoice_type": final_invoice_type,
                "distribution_combination": distribution_combination,
                "description": final_description
            }
        }
        log_response("create_ap_invoice", result)
        return result

    if not FUSION_BASE_URL:
        result = {
            "status": "ERROR",
            "message": "FUSION_BASE_URL ou FUSION_URL não está definido no ambiente"
        }
        log_response("create_ap_invoice", result)
        return result

    url = f"{FUSION_BASE_URL}/fscmRestApi/resources/11.13.18.05/invoices"

    payload = {
        "BusinessUnit": business_unit,
        "Supplier": supplier,
        "SupplierSite": supplier_site,
        "InvoiceNumber": invoice_number,
        "InvoiceDate": invoice_date,
        "AccountingDate": final_accounting_date,
        "TermsDate": final_terms_date,
        "InvoiceAmount": amount,
        "InvoiceCurrency": currency,
        "PaymentCurrency": currency,
        "PaymentMethodCode": final_payment_method_code,
        "InvoiceSource": final_invoice_source,
        "InvoiceType": final_invoice_type,
        "Description": final_description,
        "invoiceLines": [
            {
                "LineNumber": 1,
                "LineType": "Item",
                "LineAmount": amount,
                "Description": final_description
            }
        ]
    }

    if _clean(distribution_combination):
        payload["invoiceLines"][0]["DistributionCombination"] = distribution_combination

    try:
        response = requests.post(
            url,
            json=payload,
            headers=_fusion_headers(),
            auth=_fusion_auth(),
            timeout=60
        )

        response.raise_for_status()

        try:
            response_data = response.json()
        except ValueError:
            response_data = {"raw_response": response.text}

        result = {
            "status": "SUCCESS",
            "message": "Invoice criada no Fusion com sucesso",
            "invoice_id": response_data.get("InvoiceId"),
            "invoice_number": response_data.get("InvoiceNumber", invoice_number),
            "business_unit": response_data.get("BusinessUnit", business_unit),
            "supplier": response_data.get("Supplier", supplier),
            "supplier_site": response_data.get("SupplierSite", supplier_site),
            "invoice_amount": response_data.get("InvoiceAmount", amount),
            "invoice_currency": response_data.get("InvoiceCurrency", currency),
            "validation_status": response_data.get("ValidationStatus"),
            "fusion_url": _extract_self_link(response_data),
            "fusion_response": response_data
        }

        log_response("create_ap_invoice", result)
        return result

    except requests.HTTPError as exc:
        error_text = exc.response.text if exc.response is not None else str(exc)
        result = {
            "status": "ERROR",
            "message": "Falha ao criar invoice no Fusion",
            "details": error_text
        }
        log_response("create_ap_invoice", result)
        return result

    except Exception:
        logger.error(traceback.format_exc())
        result = {
            "status": "ERROR",
            "message": "Erro inesperado ao criar invoice"
        }
        log_response("create_ap_invoice", result)
        return result


if __name__ == "__main__":
    logger.info("Starting Fusion AP MCP Server...")
    port = int(os.getenv("PORT", "10000"))
    mcp.run(
        transport="http",
        host="0.0.0.0",
        port=port
    )
