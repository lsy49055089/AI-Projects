"""시뮬레이션 동작 점검에 사용할 주문 예제 데이터를 생성한다."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


def generate_sample_csv(path: str | Path, seed: int = 42) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)
    rows = []
    for i in range(160):
        sku_id = i % 40
        is_return = i % 4 == 0
        price = [1.25, 2.75, 4.5, 7.0][sku_id % 4]
        # 주문 ID의 C 접두어와 음수 수량 모두 반품 구분에 사용한다.
        rows.append(
            {
                "InvoiceNo": f"{'C' if is_return else ''}{500000+i}",
                "StockCode": f"SKU{sku_id:03d}",
                "Description": f"Item {sku_id:03d}",
                "Quantity": -int(rng.integers(1, 51)) if is_return else int(rng.integers(1, 51)),
                "UnitPrice": price,
                "InvoiceDate": "2024-01-01 12:00:00",
                "CustomerID": 10000 + sku_id,
                "Country": "Sample",
            }
        )
    # 같은 SKU에 일반 주문과 반품 주문이 포함되도록 구성한다.
    for sku_id in range(40):
        rows.append(
            {
                "InvoiceNo": f"C{600000+sku_id}",
                "StockCode": f"SKU{sku_id:03d}",
                "Description": f"Item {sku_id:03d}",
                "Quantity": -int(rng.integers(1, 41)),
                "UnitPrice": [1.25, 2.75, 4.5, 7.0][sku_id % 4],
                "InvoiceDate": "2024-01-02 12:00:00",
                "CustomerID": 11000 + sku_id,
                "Country": "Sample",
            }
        )
    pd.DataFrame(rows).to_csv(path, index=False, encoding="utf-8-sig")
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description="학습 점검용 예제 주문 데이터")
    parser.add_argument("--output", default="data/sample_online_retail.csv")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    result = generate_sample_csv(args.output, args.seed)
    print(f"예제 데이터 저장: {result}")


if __name__ == "__main__":
    main()
