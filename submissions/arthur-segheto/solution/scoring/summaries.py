from dataclasses import dataclass

from scoring.queues import QUALIFY_QUEUE, REQUALIFY_QUEUE, WORK_NOW_QUEUE


@dataclass
class PipelineSummary:
    openDeals: int
    pipelineValue: float
    workNowDeals: int
    staleDeals: int
    staleValue: float

    @property
    def staleShare(self):
        return self.staleDeals / self.openDeals if self.openDeals else 0.0


def filterByValues(deals, column, selectedValues):
    if not selectedValues:
        return deals
    return deals[deals[column].isin(selectedValues)]


def dealsInQueue(deals, queue):
    return deals[deals["queue"] == queue]


def summarizePipeline(deals):
    staleDeals = dealsInQueue(deals, REQUALIFY_QUEUE)
    return PipelineSummary(
        openDeals=len(deals),
        pipelineValue=deals["sales_price"].sum(),
        workNowDeals=len(dealsInQueue(deals, WORK_NOW_QUEUE)),
        staleDeals=len(staleDeals),
        staleValue=staleDeals["sales_price"].sum(),
    )


def summarizeStaleDealsBySalesAgent(deals):
    isStale = deals["queue"] == REQUALIFY_QUEUE
    summary = (
        deals.assign(
            is_stale=isStale,
            is_work_now=deals["queue"] == WORK_NOW_QUEUE,
            is_qualify=deals["queue"] == QUALIFY_QUEUE,
            stale_value=deals["sales_price"].where(isStale, 0),
        )
        .groupby(["sales_agent", "manager"], as_index=False)
        .agg(
            open_deals=("opportunity_id", "count"),
            work_now_deals=("is_work_now", "sum"),
            qualify_deals=("is_qualify", "sum"),
            stale_deals=("is_stale", "sum"),
            stale_value=("stale_value", "sum"),
        )
    )
    summary["stale_share"] = summary["stale_deals"] / summary["open_deals"]
    return summary.sort_values("stale_value", ascending=False)
