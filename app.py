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

# Env
FUSION_BASE_URL = os.getenv("FUSION_BASE_URL", "").rstrip("/")
FUSION_USER = os.getenv("FUSION_USER", "")
FUSION_PASSWORD = os.getenv("FUSION_PASSWORD", "")
USE_REAL_FUSION = os.getenv("USE_REAL_FUSION", "false").lower() == "true"

# Validação local simples
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


def _fusion_auth():
    if not FUSION_USER or not FUSION_PASSWORD:
        raise ValueError("FUSION_USER e FUSION_PASSWORD precisam estar definidos no .env")
    return HTTPBasicAuth(FUSION_USER, FUSION_PASSWORD)


def _fusion_headers():
    return {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def validate_invoice_payload(
    business_unit: str,
    supplier: str,
    supplier_site: str,
    invoice_number: str,
    invoice_date: str,
    amount: float,
    currency: str,
    description: Optional[str] = None
) -> Dict[str, Any]:
    errors: List[str] = []

    if not business_unit or not business_unit.strip():
        errors.append("business_unit is required")

    if not supplier or not supplier.strip():
        errors.append("supplier is required")

    if not supplier_site or not supplier_site.strip():
        errors.append("supplier_site is required")

    if not invoice_number or not invoice_number.strip():
        errors.append("invoice_number is required")

    if not invoice_date or not invoice_date.strip():
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

    if not currency or not currency.strip():
        errors.append("currency is required")

    # description virou opcional
    return {
        "valid": len(errors) == 0,
        "errors": errors
    }


def validate_supplier_context(
    business_unit: str,
    supplier: str,
    supplier_site: str
) -> Dict[str, Any]:
    errors: List[str] = []

    if business_unit and business_unit not in ALLOWED_BUSINESS_UNITS:
        errors.append(f"business_unit '{business_unit}' not recognized")

    if supplier and supplier not in ALLOWED_SUPPLIERS:
        errors.append(f"supplier '{supplier}' not recognized")

    if supplier_site and supplier_site not in ALLOWED_SUPPLIER_SITES:
        errors.append(f"supplier_site '{supplier_site}' not recognized")

    return {
        "valid": len(errors) == 0,
        "errors": errors
    }


def normalize_description(description: Optional[str]) -> str:
    if description and description.strip():
        return description.strip()
    return "Invoice criada via Agent"


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
def resolve_supplier(
    supplier_name: str,
    supplier_site: Optional[str] = None
) -> Dict[str, Any]:
    log_request(
        "resolve_supplier",
        supplier_name=supplier_name,
        supplier_site=supplier_site
    )

    result = {
        "supplier_name": supplier_name,
        "supplier_site": supplier_site,
        "status": "FOUND" if supplier_name in ALLOWED_SUPPLIERS else "NOT_FOUND"
    }

    log_response("resolve_supplier", result)
    return result


@mcp.tool
def validate_supplier_context_tool(
    business_unit: str,
    supplier: str,
    supplier_site: str
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
    business_unit: str,
    supplier: str,
    supplier_site: str,
    invoice_number: str,
    invoice_date: str,
    amount: float,
    currency: str,
    description: Optional[str] = None
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
        description=description
    )

    result = validate_invoice_payload(
        business_unit=business_unit,
        supplier=supplier,
        supplier_site=supplier_site,
        invoice_number=invoice_number,
        invoice_date=invoice_date,
        amount=amount,
        currency=currency,
        description=description
    )

    log_response("validate_invoice_payload_tool", result)
    return result


@mcp.tool
def create_ap_invoice(
    business_unit: str,
    supplier: str,
    supplier_site: str,
    invoice_number: str,
    invoice_date: str,
    amount: float,
    currency: str,
    description: Optional[str] = None
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
        description=description
    )

    final_description = normalize_description(description)

    payload_validation = validate_invoice_payload(
        business_unit=business_unit,
        supplier=supplier,
        supplier_site=supplier_site,
        invoice_number=invoice_number,
        invoice_date=invoice_date,
        amount=amount,
        currency=currency,
        description=final_description
    )

    if not payload_validation["valid"]:
        result = {
            "status": "ERROR",
            "message": "Invoice payload inválido",
            "validation_errors": payload_validation["errors"]
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
            "status": "ERROR",
            "message": "Contexto de fornecedor inválido",
            "validation_errors": context_validation["errors"]
        }
        log_response("create_ap_invoice", result)
        return result

    # Modo mock para testar o fluxo Oracle -> MCP sem depender do Fusion
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
                "amount": amount,
                "currency": currency,
                "description": final_description
            }
        }
        log_response("create_ap_invoice", result)
        return result

    if not FUSION_BASE_URL:
        result = {
            "status": "ERROR",
            "message": "FUSION_BASE_URL não está definido no .env"
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
        "InvoiceAmount": amount,
        "Currency": currency,
        "Description": final_description,
        "InvoiceLines": [
            {
                "LineNumber": 1,
                "LineType": "Item",
                "LineAmount": amount,
                "Description": final_description
            }
        ]
    }

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

    logger.info( "Starting Fusion AP MCP Server...")
    port = int(os.getenv("PORT", "10000"))
    mcp.run(
        transport="http",
        host="0.0.0.0",
        port=port
    )