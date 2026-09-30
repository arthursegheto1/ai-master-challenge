from scoring.explanations import formatMoney
from scoring.queues import REQUALIFY_QUEUE, WORK_NOW_QUEUE


def testMoneyUsesDotAsThousandsSeparator():
    assert formatMoney(26768) == "26.768"


def testWorkNowExplanationStatesTheCycleLimit(prioritizedDeals, winModel):
    workNow = prioritizedDeals[prioritizedDeals["queue"] == WORK_NOW_QUEUE]
    statesLimit = workNow["reasons"].apply(lambda reasons: f"{winModel.cycleLimitDays} dias" in reasons[0])
    assert statesLimit.all()


def testRequalifyExplanationAsksForADecision(prioritizedDeals):
    requalify = prioritizedDeals[prioritizedDeals["queue"] == REQUALIFY_QUEUE]
    asksForDecision = requalify["reasons"].apply(lambda reasons: "encerrar" in reasons[-1])
    assert asksForDecision.all()
