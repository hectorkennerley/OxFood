"""Order → CSV for Foodbuy. Column layout is our proposal; confirm the exact format with Foodbuy."""
import csv
import io

COLUMNS = ["OrderRef", "College", "CostCentre", "DeliveryDate", "SupplierCode", "SupplierName", "ProductCode",
           "Description", "PackSize", "Unit", "Qty", "UnitPrice", "LineTotal"]


def order_to_csv(order_ref: str, college_name: str, cost_centre: str, delivery_date: str, lines: list[dict]) -> str:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(COLUMNS)
    for l in lines:
        w.writerow([order_ref, college_name, cost_centre, delivery_date, l["supplier_code"], l["supplier_name"],
                    l["sku"], l["name"], l["pack_size"], l["unit"], l["qty"], f"{l['unit_price']:.2f}",
                    f"{l['qty'] * l['unit_price']:.2f}"])
    return buf.getvalue()
