import pandas as pd
import pytest

from scoring.queues import QUALIFY_QUEUE, REQUALIFY_QUEUE, WORK_NOW_QUEUE
from scoring.summaries import (
    filterByValues,
    summarizePipeline,
    summarizeStaleDealsBySalesAgent,
)


def buildDeals():
    return pd.DataFrame(
        {
            "opportunity_id": ["a", "b", "c", "d"],
            "sales_agent": ["Ana", "Ana", "Bia", "Bia"],
            "manager": ["Carlos", "Carlos", "Dora", "Dora"],
            "queue": [WORK_NOW_QUEUE, REQUALIFY_QUEUE, REQUALIFY_QUEUE, QUALIFY_QUEUE],
            "sales_price": [100.0, 200.0, 300.0, 400.0],
        }
    )


def testEmptySelectionKeepsEveryDeal():
    assert len(filterByValues(buildDeals(), "manager", [])) == 4


def testSelectionKeepsOnlyTheChosenValues():
    filtered = filterByValues(buildDeals(), "manager", ["Dora"])
    assert set(filtered["sales_agent"]) == {"Bia"}


def testPipelineSummaryCountsDealsAndValues():
    summary = summarizePipeline(buildDeals())
    assert summary.openDeals == 4
    assert summary.pipelineValue == 1000
    assert summary.workNowDeals == 1
    assert summary.staleDeals == 2
    assert summary.staleValue == 500


def testStaleShareIsZeroForAnEmptyPipeline():
    assert summarizePipeline(buildDeals().iloc[0:0]).staleShare == 0.0


def testStaleSummaryIsSortedByStaleValue():
    bySalesAgent = summarizeStaleDealsBySalesAgent(buildDeals())
    assert list(bySalesAgent["sales_agent"]) == ["Bia", "Ana"]


def testStaleShareIsTheFractionOfOpenDeals():
    bySalesAgent = summarizeStaleDealsBySalesAgent(buildDeals()).set_index("sales_agent")
    assert bySalesAgent.loc["Ana", "stale_share"] == pytest.approx(0.5)
