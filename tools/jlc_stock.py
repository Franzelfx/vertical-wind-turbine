#!/usr/bin/env python3
"""Search JLCPCB's parts catalogue: stock, price and library type per keyword or LCSC number.

Uses the public search endpoint of jlcpcb.com (the KiCad MCP's offline database is optional).

    tools/jlc_stock.py STM32H743VIT6 C2836813 "470uF 16V polymer"
"""

import json
import sys
import urllib.request

URL = "https://jlcpcb.com/api/overseas-pcb-order/v1/shoppingCart/smtGood/selectSmtComponentList"


def search(keyword: str, size: int = 6) -> list[dict]:
    body = json.dumps({"keyword": keyword, "currentPage": 1, "pageSize": size}).encode()
    req = urllib.request.Request(URL, body, {"Content-Type": "application/json"})
    data = json.load(urllib.request.urlopen(req, timeout=30))
    return ((data.get("data") or {}).get("componentPageInfo") or {}).get("list") or []


def main() -> None:
    for keyword in sys.argv[1:]:
        print(f"== {keyword}")
        for c in search(keyword):
            if str(c.get("componentCode", "")).startswith("C99"):  # placeholder entries
                continue
            prices = c.get("componentPrices") or []
            price = prices[0].get("productPrice") if prices else None
            print(
                f"  {c.get('componentCode'):10s} {str(c.get('componentModelEn'))[:28]:28s} "
                f"{str(c.get('componentSpecificationEn'))[:22]:22s} stock {c.get('stockCount'):>8} "
                f"{c.get('componentLibraryType'):8s} ${price}"
            )


if __name__ == "__main__":
    main()
