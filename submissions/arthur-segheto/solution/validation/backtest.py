from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd

from scoring.priority import prioritize
from scoring.probability import buildWinModel
from scoring.queues import ENGAGING_STAGE, WORK_NOW_QUEUE

TOP_SHARE = 0.2
CUTOFF_QUANTILES = (0.6, 0.7, 0.8)
BOOTSTRAP_ROUNDS = 2000
CONFIDENCE_LEVEL = 0.95
RANDOM_SEED = 0


@dataclass
class BacktestResult:
    cutoffDate: pd.Timestamp
    trainingDeals: int
    evaluatedDeals: int
    overallWinRate: float
    priceWinRate: float
    scoreWinRate: float
    priceRevenue: float
    scoreRevenue: float
    differenceLow: float
    differenceHigh: float


def summarizeBacktest(closedDeals, bootstrapRounds=BOOTSTRAP_ROUNDS):
    results = [
        evaluateAtCutoff(closedDeals, selectCutoffDate(closedDeals, quantile), bootstrapRounds)
        for quantile in CUTOFF_QUANTILES
    ]
    return pd.DataFrame([asdict(result) for result in results])


def selectCutoffDate(closedDeals, quantile):
    return closedDeals["close_date"].quantile(quantile).normalize()


def evaluateAtCutoff(closedDeals, cutoffDate, bootstrapRounds=BOOTSTRAP_ROUNDS):
    history = selectHistory(closedDeals, cutoffDate)
    openAtCutoff = presentAsOpen(selectDealsOpenAtCutoff(closedDeals, cutoffDate), cutoffDate)
    scored = prioritize(openAtCutoff, buildWinModel(history))
    evaluated = scored[scored["queue"] == WORK_NOW_QUEUE]
    byPrice = topDeals(evaluated, "sales_price")
    byScore = topDeals(evaluated, "score")
    differenceLow, differenceHigh = bootstrapWinRateDifference(evaluated, bootstrapRounds)
    return BacktestResult(
        cutoffDate=cutoffDate,
        trainingDeals=len(history),
        evaluatedDeals=len(evaluated),
        overallWinRate=evaluated["won"].mean(),
        priceWinRate=byPrice["won"].mean(),
        scoreWinRate=byScore["won"].mean(),
        priceRevenue=capturedRevenue(byPrice),
        scoreRevenue=capturedRevenue(byScore),
        differenceLow=differenceLow,
        differenceHigh=differenceHigh,
    )


def selectHistory(closedDeals, cutoffDate):
    return closedDeals[closedDeals["close_date"] <= cutoffDate]


def selectDealsOpenAtCutoff(closedDeals, cutoffDate):
    wasEngaged = closedDeals["engage_date"] < cutoffDate
    closedAfterCutoff = closedDeals["close_date"] > cutoffDate
    return closedDeals[wasEngaged & closedAfterCutoff]


def presentAsOpen(deals, cutoffDate):
    ageInDays = (cutoffDate - deals["engage_date"]).dt.days.astype(float)
    return deals.assign(deal_stage=ENGAGING_STAGE, age_days=ageInDays)


def topDeals(deals, orderColumn):
    topCount = int(len(deals) * TOP_SHARE)
    return deals.sort_values(orderColumn, ascending=False, kind="stable").head(topCount)


def capturedRevenue(deals):
    return deals.loc[deals["won"] == 1, "sales_price"].sum()


def winRateDifference(deals):
    return topDeals(deals, "score")["won"].mean() - topDeals(deals, "sales_price")["won"].mean()


def bootstrapWinRateDifference(deals, bootstrapRounds):
    generator = np.random.default_rng(RANDOM_SEED)
    differences = [
        winRateDifference(deals.iloc[generator.integers(0, len(deals), len(deals))])
        for _ in range(bootstrapRounds)
    ]
    tail = (1 - CONFIDENCE_LEVEL) / 2
    return tuple(np.quantile(differences, [tail, 1 - tail]))
