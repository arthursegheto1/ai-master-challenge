import pandas as pd

from scoring.queues import QUALIFY_QUEUE, REQUALIFY_QUEUE, WORK_NOW_QUEUE, assignQueue

CYCLE_LIMIT_DAYS = 115


def queueOf(stage, ageDays):
    deals = pd.DataFrame({"deal_stage": [stage], "age_days": [ageDays]})
    return assignQueue(deals, CYCLE_LIMIT_DAYS).iloc[0]


def testEngagingDealWithinTheTypicalCycleGoesToWorkNow():
    assert queueOf("Engaging", CYCLE_LIMIT_DAYS) == WORK_NOW_QUEUE


def testEngagingDealBeyondTheTypicalCycleGoesToRequalify():
    assert queueOf("Engaging", CYCLE_LIMIT_DAYS + 1) == REQUALIFY_QUEUE


def testProspectingDealGoesToQualify():
    assert queueOf("Prospecting", float("nan")) == QUALIFY_QUEUE
