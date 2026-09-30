import math
from dataclasses import dataclass

import pandas as pd

from scoring.queues import REQUALIFY_QUEUE, WORK_NOW_QUEUE

CYCLE_QUANTILE = 0.95
MIN_DEALS_TO_TRUST_AN_AGE = 150


@dataclass
class WinModel:
    baseRate: float
    cycleLimitDays: int
    winRateByAge: pd.Series


def buildWinModel(closedDeals):
    cycleLimitDays = calculateCycleLimitDays(closedDeals)
    return WinModel(
        baseRate=closedDeals["won"].mean(),
        cycleLimitDays=cycleLimitDays,
        winRateByAge=calculateWinRateByAge(closedDeals, cycleLimitDays),
    )


def calculateCycleLimitDays(closedDeals):
    return math.ceil(closedDeals["cycle_days"].quantile(CYCLE_QUANTILE))


def calculateWinRateByAge(closedDeals, cycleLimitDays):
    outcomesOfLongerDeals = countOutcomesOfDealsLongerThanEachAge(closedDeals)
    winRate = outcomesOfLongerDeals["wins"] / outcomesOfLongerDeals["deals"]
    hasEnoughDeals = outcomesOfLongerDeals["deals"] >= MIN_DEALS_TO_TRUST_AN_AGE
    return winRate.where(hasEnoughDeals).ffill().loc[:cycleLimitDays]


def countOutcomesOfDealsLongerThanEachAge(closedDeals):
    maxObservedCycleDays = int(closedDeals["cycle_days"].max())
    outcomesByCycle = (
        closedDeals.groupby("cycle_days")["won"]
        .agg(wins="sum", deals="count")
        .reindex(range(maxObservedCycleDays + 1), fill_value=0)
    )
    fromLongestToShortest = outcomesByCycle[::-1]
    return fromLongestToShortest.cumsum()[::-1].shift(-1, fill_value=0)


def winRateAtAge(ages, model):
    cappedAges = ages.clip(upper=model.cycleLimitDays)
    return cappedAges.map(model.winRateByAge)


def addWinProbability(deals, model):
    isWorkNow = deals["queue"] == WORK_NOW_QUEUE
    isRequalify = deals["queue"] == REQUALIFY_QUEUE
    probability = winRateAtAge(deals["age_days"], model).where(isWorkNow, model.baseRate)
    return deals.assign(win_probability=probability.where(~isRequalify))
