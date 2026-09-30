import numpy as np

from scoring.explanations import addExplanations
from scoring.probability import addWinProbability
from scoring.queues import QUALIFY_QUEUE, REQUALIFY_QUEUE, WORK_NOW_QUEUE, addQueue

EXPECTED_VALUE_WEIGHT = 0.5
URGENCY_WEIGHT = 0.5
STALE_DEAL_HALF_LIFE_IN_CYCLES = 1.0
ACCOUNT_SIZE_BONUS = 0.25
SCORE_SCALE = 100


def prioritize(openDeals, model):
    return (
        openDeals.pipe(addQueue, model.cycleLimitDays)
        .pipe(addWinProbability, model)
        .pipe(addExpectedValue)
        .pipe(addDaysUntilCycleLimit, model)
        .pipe(addRecoveryFactor, model)
        .pipe(addAccountMultiplier)
        .pipe(addRankingValue)
        .pipe(addScore)
        .pipe(addExplanations, model)
        .sort_values("score", ascending=False)
    )


def addExpectedValue(deals):
    return deals.assign(expected_value=deals["sales_price"] * deals["win_probability"])


def addDaysUntilCycleLimit(deals, model):
    isWorkNow = deals["queue"] == WORK_NOW_QUEUE
    daysLeft = model.cycleLimitDays - deals["age_days"]
    return deals.assign(days_until_cycle_limit=daysLeft.where(isWorkNow))


def addRecoveryFactor(deals, model):
    isRequalify = deals["queue"] == REQUALIFY_QUEUE
    cyclesBeyondLimit = (deals["age_days"] - model.cycleLimitDays) / model.cycleLimitDays
    recoveryFactor = np.exp2(-cyclesBeyondLimit / STALE_DEAL_HALF_LIFE_IN_CYCLES)
    return deals.assign(recovery_factor=recoveryFactor.where(isRequalify, 1.0))


def addAccountMultiplier(deals):
    isQualify = deals["queue"] == QUALIFY_QUEUE
    accountBonus = ACCOUNT_SIZE_BONUS * deals["revenue_percentile"].fillna(0)
    return deals.assign(account_multiplier=(1 + accountBonus).where(isQualify, 1.0))


def addRankingValue(deals):
    baseValue = deals["expected_value"].fillna(deals["sales_price"])
    rankingValue = baseValue * deals["recovery_factor"] * deals["account_multiplier"]
    return deals.assign(ranking_value=rankingValue)


def addScore(deals):
    valueRank = rankWithinQueue(deals["ranking_value"], deals["queue"])
    urgencyRank = rankWithinQueue(deals["days_until_cycle_limit"] * -1, deals["queue"])
    blendedRank = EXPECTED_VALUE_WEIGHT * valueRank + URGENCY_WEIGHT * urgencyRank.fillna(valueRank)
    return deals.assign(score=(blendedRank * SCORE_SCALE).round().astype(int))


def rankWithinQueue(values, queues):
    return values.groupby(queues).rank(pct=True)
