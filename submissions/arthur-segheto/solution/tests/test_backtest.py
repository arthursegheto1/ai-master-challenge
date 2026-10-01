import pandas as pd
import pytest

from validation.backtest import (
    TOP_SHARE,
    bootstrapWinRateDifference,
    capturedRevenue,
    evaluateAtCutoff,
    presentAsOpen,
    selectCutoffDate,
    selectDealsOpenAtCutoff,
    selectHistory,
    topDeals,
)

FEW_BOOTSTRAP_ROUNDS = 50


def buildDeals():
    return pd.DataFrame(
        {
            "opportunity_id": ["a", "b", "c", "d"],
            "engage_date": pd.to_datetime(["2017-01-01", "2017-01-01", "2017-03-01", "2017-06-01"]),
            "close_date": pd.to_datetime(["2017-02-01", "2017-05-01", "2017-04-01", "2017-07-01"]),
        }
    )


CUTOFF = pd.Timestamp("2017-03-15")


def testHistoryNeverContainsDealsClosedAfterTheCutoff():
    history = selectHistory(buildDeals(), CUTOFF)
    assert (history["close_date"] <= CUTOFF).all()


def testDealsOpenAtCutoffWereEngagedBeforeAndClosedAfter():
    openDeals = selectDealsOpenAtCutoff(buildDeals(), CUTOFF)
    assert list(openDeals["opportunity_id"]) == ["b", "c"]


def testNoDealIsBothHistoryAndEvaluated():
    deals = buildDeals()
    historyIds = set(selectHistory(deals, CUTOFF)["opportunity_id"])
    openIds = set(selectDealsOpenAtCutoff(deals, CUTOFF)["opportunity_id"])
    assert historyIds.isdisjoint(openIds)


def testAgeIsMeasuredFromTheCutoffAndNotFromTheOutcome():
    deals = buildDeals().iloc[[0, 1]].assign(engage_date=pd.Timestamp("2017-01-01"))
    ages = presentAsOpen(deals, CUTOFF)["age_days"]
    assert ages.nunique() == 1
    assert ages.iloc[0] == (CUTOFF - pd.Timestamp("2017-01-01")).days


def testTopDealsKeepsTheRequestedShareOfTheBestOrdered():
    deals = pd.DataFrame({"score": range(100)})
    top = topDeals(deals, "score")
    assert len(top) == int(100 * TOP_SHARE)
    assert top["score"].min() == 100 - len(top)


def testCapturedRevenueCountsOnlyWonDeals():
    deals = pd.DataFrame({"won": [1, 0, 1], "sales_price": [100, 500, 50]})
    assert capturedRevenue(deals) == 150


def testBootstrapIntervalIsOrderedAndReproducible():
    deals = pd.DataFrame(
        {"won": [1, 0] * 50, "score": range(100), "sales_price": list(range(100))[::-1]}
    )
    first = bootstrapWinRateDifference(deals, FEW_BOOTSTRAP_ROUNDS)
    second = bootstrapWinRateDifference(deals, FEW_BOOTSTRAP_ROUNDS)
    assert first == second
    assert first[0] <= first[1]


def testEvaluationOnRealDataTrainsOnlyOnThePastAndReturnsValidRates(closedDeals):
    cutoff = selectCutoffDate(closedDeals, 0.7)
    result = evaluateAtCutoff(closedDeals, cutoff, FEW_BOOTSTRAP_ROUNDS)
    assert result.trainingDeals == len(selectHistory(closedDeals, cutoff))
    assert 0 <= result.scoreWinRate <= 1
    assert 0 <= result.priceWinRate <= 1
    assert result.differenceLow <= result.differenceHigh
    assert result.evaluatedDeals > 0
