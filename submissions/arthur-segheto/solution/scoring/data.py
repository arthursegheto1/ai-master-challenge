from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
REFERENCE_DATE = pd.Timestamp("2017-12-31")
OPEN_STAGES = ("Prospecting", "Engaging")
PRODUCT_FIXES = {"GTXPro": "GTX Pro"}
SECTOR_FIXES = {"technolgy": "technology"}


def load_pipeline(data_dir=DATA_DIR):
    data_dir = Path(data_dir)
    pipeline = pd.read_csv(
        data_dir / "sales_pipeline.csv", parse_dates=["engage_date", "close_date"]
    )
    products = pd.read_csv(data_dir / "products.csv")
    teams = pd.read_csv(data_dir / "sales_teams.csv")
    accounts = pd.read_csv(data_dir / "accounts.csv")

    pipeline["product"] = pipeline["product"].replace(PRODUCT_FIXES)
    accounts["sector"] = accounts["sector"].replace(SECTOR_FIXES)

    df = (
        pipeline.merge(products, on="product", how="left")
        .merge(teams, on="sales_agent", how="left")
        .merge(accounts, on="account", how="left")
    )

    if df["sales_price"].isna().any():
        raise ValueError("Produtos do pipeline sem correspondência no catálogo")
    if df["manager"].isna().any():
        raise ValueError("Vendedores do pipeline sem correspondência em sales_teams")

    df["is_open"] = df["deal_stage"].isin(OPEN_STAGES)
    df["has_account"] = df["account"].notna()
    df["won"] = df["deal_stage"].map({"Won": 1, "Lost": 0})
    df["cycle_days"] = (df["close_date"] - df["engage_date"]).dt.days
    df["age_days"] = (REFERENCE_DATE - df["engage_date"]).dt.days.where(df["is_open"])
    return df


def split_pipeline(df):
    return df[~df["is_open"]].copy(), df[df["is_open"]].copy()