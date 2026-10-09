"""Online Retail 주문 데이터에서 학습용 상품 목록을 생성한다."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


REQUIRED_COLUMNS = ("InvoiceNo", "StockCode", "Description", "Quantity", "UnitPrice")


def read_retail_data(input_path: str | Path) -> pd.DataFrame:
    path = Path(input_path)
    if not path.is_file():
        raise FileNotFoundError(f"입력 파일이 없습니다: {path}")
    suffix = path.suffix.lower()
    if suffix == ".csv":
        data = pd.read_csv(path, encoding="utf-8-sig", dtype={"InvoiceNo": str, "StockCode": str})
    elif suffix in (".xlsx", ".xls"):
        data = pd.read_excel(path, dtype={"InvoiceNo": str, "StockCode": str})
    else:
        raise ValueError("입력 형식은 CSV 또는 Excel(.xlsx/.xls)입니다.")
    missing = set(REQUIRED_COLUMNS) - set(data.columns)
    if missing:
        raise ValueError(f"필수 컬럼이 없습니다: {sorted(missing)}")
    return data


def preprocess(data: pd.DataFrame, seed: int = 42) -> list[dict]:
    df = data[list(REQUIRED_COLUMNS)].copy()
    df["Quantity"] = pd.to_numeric(df["Quantity"], errors="coerce")
    df["UnitPrice"] = pd.to_numeric(df["UnitPrice"], errors="coerce")
    df = df.dropna(subset=["StockCode", "Quantity", "UnitPrice"])
    df = df[(df["Quantity"] != 0) & (df["UnitPrice"] > 0)].copy()
    df["StockCode"] = df["StockCode"].astype(str).str.strip()
    df = df[df["StockCode"] != ""]
    df["Description"] = df["Description"].fillna("").astype(str).str.strip()
    df["InvoiceNo"] = df["InvoiceNo"].fillna("").astype(str)

    df["Type"] = np.where(
        (df["Quantity"] < 0) | df["InvoiceNo"].str.upper().str.startswith("C"),
        "Return Zone",
        "Product",
    )
    df["Quantity"] = df["Quantity"].abs()
    grouped = (
        df.groupby(["StockCode", "Type"], as_index=False, sort=True)
        .agg(Name=("Description", "first"), Quantity=("Quantity", "sum"), UnitPrice=("UnitPrice", "median"))
    )
    if grouped.empty:
        raise ValueError("유효한 주문 데이터가 없습니다.")

    rng = np.random.default_rng(seed)
    distinct_codes = sorted(grouped["StockCode"].unique())
    # 원본 주문 데이터에 없는 무게·높이·너비는 재현 가능한 난수로 정의한다.
    sku_features = {
        code: (
            int(rng.integers(1, 101)),
            int(rng.integers(5, 101)),
            int(rng.integers(5, 101)),
        )
        for code in distinct_codes
    }
    records = []
    for row in grouped.itertuples(index=False):
        weight, height, width = sku_features[row.StockCode]
        records.append(
            {
                "StockCode": str(row.StockCode),
                "Name": row.Name or str(row.StockCode),
                "Type": str(row.Type),
                "Quantity": int(round(row.Quantity)),
                "UnitPrice": round(float(row.UnitPrice), 2),
                "Weight": weight,
                "Height": height,
                "Width": width,
            }
        )
    return records


def export_json(records: list[dict], output_path: str | Path) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(records, handle, ensure_ascii=False, indent=2)


def main() -> None:
    parser = argparse.ArgumentParser(description="Online Retail 데이터 전처리")
    parser.add_argument("--input", required=True, help="Online Retail CSV/Excel 파일")
    parser.add_argument("--output", default="data/Combined_States.json")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    records = preprocess(read_retail_data(args.input), seed=args.seed)
    export_json(records, args.output)
    count_product = sum(x["Type"] == "Product" for x in records)
    count_return = sum(x["Type"] == "Return Zone" for x in records)
    print(f"저장 완료: {args.output} (Product {count_product}, Return Zone {count_return})")
    if not count_product or not count_return:
        print("주의: DQN을 실행하려면 Product와 Return Zone이 각각 필요합니다.")


if __name__ == "__main__":
    main()
