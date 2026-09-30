import pandas as pd
import pytest

from scoring.probability import CYCLE_QUANTILE, addWinProbability, calculateCycleLimitDays
from scoring.queues import WORK_NOW_QUEUE


def testWinRateOfAgeZeroEqualsTheBaseRate(winModel):
    assert winModel.winRateByAge.iloc[0] == pytest.approx(winModel.baseRate)


def testWinRateByAgeCoversExactlyTheCycleLimit(winModel):
    assert winModel.winRateByAge.index.max() == winModel.cycleLimitDays
    assert winModel.winRateByAge.notna().all()


def testCycleLimitCoversTheChosenShareOfClosedDeals(winModel, closedDeals):
    shareWithinLimit = (closedDeals["cycle_days"] <= winModel.cycleLimitDays).mean()
    assert shareWithinLimit >= CYCLE_QUANTILE


def testCycleLimitIgnoresASingleExtremeOutlier(closedDeals):
    outlier = closedDeals.iloc[[0]].assign(cycle_days=5000)
    withOutlier = pd.concat([closedDeals, outlier])
    assert calculateCycleLimitDays(withOutlier) == calculateCycleLimitDays(closedDeals)


def testWinProbabilityDoesNotDependOnTheSalesAgent(winModel):
    deals = pd.DataFrame(
        {
            "queue": [WORK_NOW_QUEUE, WORK_NOW_QUEUE],
            "age_days": [60, 60],
            "sales_agent": ["Agent A", "Agent B"],
        }
    )
    probabilities = addWinProbability(deals, winModel)["win_probability"]
    assert probabilities.nunique() == 1
