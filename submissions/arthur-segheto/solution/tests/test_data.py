def testNoDealIsLostInTheJoin(allDeals):
    assert len(allDeals) == 8800
    assert allDeals["opportunity_id"].is_unique


def testKnownTyposAreCorrected(allDeals):
    assert "GTXPro" not in set(allDeals["product"])
    assert "technolgy" not in set(allDeals["sector"].dropna())


def testEveryDealHasACatalogPrice(allDeals):
    assert allDeals["sales_price"].notna().all()


def testRevenuePercentileStaysBetweenZeroAndOne(allDeals):
    assert allDeals["revenue_percentile"].dropna().between(0, 1).all()


def testOpenAndClosedDealsAreSplitByStage(closedDeals, openDeals):
    assert set(closedDeals["deal_stage"]) == {"Won", "Lost"}
    assert set(openDeals["deal_stage"]) == {"Prospecting", "Engaging"}
    assert len(openDeals) == 2089


def testAgeExistsOnlyForEngagingDeals(closedDeals, openDeals):
    isEngaging = openDeals["deal_stage"] == "Engaging"
    assert closedDeals["age_days"].isna().all()
    assert openDeals.loc[isEngaging, "age_days"].notna().all()
    assert openDeals.loc[~isEngaging, "age_days"].isna().all()
