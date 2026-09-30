import numpy as np
import pandas as pd

WORK_NOW_QUEUE = "Trabalhar agora"
REQUALIFY_QUEUE = "Requalificar ou encerrar"
QUALIFY_QUEUE = "Qualificar"
ENGAGING_STAGE = "Engaging"

NEXT_ACTION_BY_QUEUE = {
    WORK_NOW_QUEUE: "Avançar a negociação",
    REQUALIFY_QUEUE: "Reativar ou encerrar",
    QUALIFY_QUEUE: "Agendar primeiro contato",
}


def addQueue(deals, cycleLimitDays):
    queue = assignQueue(deals, cycleLimitDays)
    return deals.assign(queue=queue, next_action=queue.map(NEXT_ACTION_BY_QUEUE))


def assignQueue(deals, cycleLimitDays):
    isEngaging = deals["deal_stage"] == ENGAGING_STAGE
    isWithinTypicalCycle = deals["age_days"] <= cycleLimitDays
    queue = np.select(
        [isEngaging & isWithinTypicalCycle, isEngaging],
        [WORK_NOW_QUEUE, REQUALIFY_QUEUE],
        default=QUALIFY_QUEUE,
    )
    return pd.Series(queue, index=deals.index)
