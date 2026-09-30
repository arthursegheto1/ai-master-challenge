from pathlib import Path

import pandas as pd

DATA_DIRECTORY = Path(__file__).resolve().parent.parent / "data"
REFERENCE_DATE = pd.Timestamp("2017-12-31")
OPEN_STAGES = ("Prospecting", "Engaging")
OUTCOME_BY_CLOSED_STAGE = {"Won": 1, "Lost": 0}
PRODUCT_NAME_FIXES = {"GTXPro": "GTX Pro"}
SECTOR_NAME_FIXES = {"technolgy": "technology"}


def loadPipeline(dataDirectory=DATA_DIRECTORY):
    directory = Path(dataDirectory)
    pipeline = readCsv(directory, "sales_pipeline.csv", parseDates=["engage_date", "close_date"])
    products = readCsv(directory, "products.csv")
    salesTeams = readCsv(directory, "sales_teams.csv")
    accounts = readCsv(directory, "accounts.csv")

    pipeline = replaceValues(pipeline, "product", PRODUCT_NAME_FIXES)
    accounts = replaceValues(accounts, "sector", SECTOR_NAME_FIXES)
    accounts = addRevenuePercentile(accounts)

    deals = joinDealDetails(pipeline, products, salesTeams, accounts)
    ensureNoDealLostItsDetails(deals)
    return addDerivedColumns(deals)


def readCsv(directory, fileName, parseDates=False):
    return pd.read_csv(directory / fileName, parse_dates=parseDates)


def replaceValues(table, column, replacements):
    return table.assign(**{column: table[column].replace(replacements)})


def addRevenuePercentile(accounts):
    return accounts.assign(revenue_percentile=accounts["revenue"].rank(pct=True))


def joinDealDetails(pipeline, products, salesTeams, accounts):
    return (
        pipeline.merge(products, on="product", how="left")
        .merge(salesTeams, on="sales_agent", how="left")
        .merge(accounts, on="account", how="left")
    )


def ensureNoDealLostItsDetails(deals):
    if deals["sales_price"].isna().any():
        raise ValueError("Há deals com produto ausente do catálogo")
    if deals["manager"].isna().any():
        raise ValueError("Há deals com vendedor ausente da tabela de times")


def addDerivedColumns(deals):
    isOpen = deals["deal_stage"].isin(OPEN_STAGES)
    daysSinceEngagement = (REFERENCE_DATE - deals["engage_date"]).dt.days
    return deals.assign(
        is_open=isOpen,
        has_account=deals["account"].notna(),
        won=deals["deal_stage"].map(OUTCOME_BY_CLOSED_STAGE),
        cycle_days=(deals["close_date"] - deals["engage_date"]).dt.days,
        age_days=daysSinceEngagement.where(isOpen),
    )


def splitClosedAndOpenDeals(deals):
    closedDeals = deals[~deals["is_open"]].copy()
    openDeals = deals[deals["is_open"]].copy()
    return closedDeals, openDeals
