import pandas as pd
import pytest

from scoring.priority import (
    EXPECTED_VALUE_WEIGHT,
    STALE_DEAL_HALF_LIFE_IN_CYCLES,
    URGENCY_WEIGHT,
    addAccountMultiplier,
    addRankingValue,
    addRecoveryFactor,
)
from scoring.probability import WinModel
from scoring.queues import QUALIFY_QUEUE, REQUALIFY_QUEUE, WORK_NOW_QUEUE

CYCLE_LIMIT_DAYS = 100


def modelWithCycleLimit():
    return WinModel(baseRate=0.6, cycleLimitDays=CYCLE_LIMIT_DAYS, winRateByAge=pd.Series(dtype=float))


def testEveryOpenDealReceivesOneQueue(prioritizedDeals):
    assert len(prioritizedDeals) == 2089
    assert set(prioritizedDeals["queue"]) == {WORK_NOW_QUEUE, REQUALIFY_QUEUE, QUALIFY_QUEUE}


def testDealsBeyondTheCycleHaveNoWinProbability(prioritizedDeals):
    requalify = prioritizedDeals[prioritizedDeals["queue"] == REQUALIFY_QUEUE]
    assert requalify["win_probability"].isna().all()


def testScoreStaysBetweenZeroAndOneHundred(prioritizedDeals):
    assert prioritizedDeals["score"].between(0, 100).all()


def testWeightsSumToOne():
    assert EXPECTED_VALUE_WEIGHT + URGENCY_WEIGHT == pytest.approx(1)


def testWorkNowScoreIsNotJustThePrice(prioritizedDeals):
    workNow = prioritizedDeals[prioritizedDeals["queue"] == WORK_NOW_QUEUE]
    correlation = workNow["score"].rank().corr(workNow["sales_price"].rank())
    assert correlation < 0.8


def testEveryDealHasReasonsAndNextAction(prioritizedDeals):
    assert (prioritizedDeals["reasons"].apply(len) >= 2).all()
    assert prioritizedDeals["next_action"].notna().all()


def testStaleDealsLoseWeightTheLongerTheyStayOpen():
    deals = pd.DataFrame({"queue": [REQUALIFY_QUEUE] * 2, "age_days": [150, 300]})
    recoveryFactors = addRecoveryFactor(deals, modelWithCycleLimit())["recovery_factor"]
    assert recoveryFactors.iloc[0] > recoveryFactors.iloc[1]


def testStaleDealKeepsHalfItsWeightAfterOneHalfLifeBeyondTheLimit():
    ageAtHalfLife = CYCLE_LIMIT_DAYS * (1 + STALE_DEAL_HALF_LIFE_IN_CYCLES)
    deals = pd.DataFrame({"queue": [REQUALIFY_QUEUE], "age_days": [ageAtHalfLife]})
    recoveryFactor = addRecoveryFactor(deals, modelWithCycleLimit())["recovery_factor"].iloc[0]
    assert recoveryFactor == pytest.approx(0.5)


def testDealsWithinTheCycleKeepFullWeight():
    deals = pd.DataFrame({"queue": [WORK_NOW_QUEUE], "age_days": [50]})
    assert addRecoveryFactor(deals, modelWithCycleLimit())["recovery_factor"].iloc[0] == 1.0


def testBiggerAccountBreaksTiesInTheQualifyQueue():
    deals = pd.DataFrame(
        {
            "queue": [QUALIFY_QUEUE] * 3,
            "revenue_percentile": [0.9, 0.2, float("nan")],
            "expected_value": [100.0] * 3,
            "sales_price": [158.0] * 3,
            "recovery_factor": [1.0] * 3,
        }
    )
    rankingValues = addRankingValue(addAccountMultiplier(deals))["ranking_value"]
    assert rankingValues.iloc[0] > rankingValues.iloc[1] > rankingValues.iloc[2]


def testAccountBonusIsNotAppliedOutsideTheQualifyQueue():
    deals = pd.DataFrame({"queue": [WORK_NOW_QUEUE], "revenue_percentile": [0.9]})
    assert addAccountMultiplier(deals)["account_multiplier"].iloc[0] == 1.0
