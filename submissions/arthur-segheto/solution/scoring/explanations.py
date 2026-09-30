from scoring.probability import CYCLE_QUANTILE
from scoring.queues import QUALIFY_QUEUE, REQUALIFY_QUEUE, WORK_NOW_QUEUE


def addExplanations(deals, model):
    return deals.assign(reasons=deals.apply(explainDeal, axis=1, model=model))


def explainDeal(deal, model):
    return EXPLAINER_BY_QUEUE[deal["queue"]](deal, model)


def explainWorkNow(deal, model):
    daysOpen = int(deal["age_days"])
    daysLeft = int(deal["days_until_cycle_limit"])
    return [
        f"Em negociação há {daysOpen} dias. Faltam {daysLeft} dias para passar do ciclo típico "
        f"({explainCycleLimit(model)}).",
        f"Chance estimada de {deal['win_probability']:.0%}: é a taxa de vitória dos deals "
        f"fechados que chegaram a essa idade, contra {model.baseRate:.0%} no geral.",
        explainExpectedValue(deal),
    ]


def explainRequalify(deal, model):
    daysOpen = int(deal["age_days"])
    daysBeyondLimit = daysOpen - model.cycleLimitDays
    return [
        f"Aberto há {daysOpen} dias, {daysBeyondLimit} além do ciclo típico "
        f"({explainCycleLimit(model)}). Poucos deals fechados chegaram tão longe, "
        "então a chance de fechar não é estimada.",
        f"Valor em jogo: {formatMoney(deal['sales_price'])} ({deal['product']}). Por estar além "
        f"do ciclo, o deal entra no ranking com {deal['recovery_factor']:.0%} desse valor, "
        "e esse peso cai a cada dia que passa.",
        "Contatar para requalificar e, sem resposta, encerrar como perdido.",
    ]


def explainQualify(deal, model):
    reasons = [
        "Ainda em prospecção e sem data de entrada, então a idade do deal não entra no "
        f"cálculo. Chance base de {deal['win_probability']:.0%}.",
        explainExpectedValue(deal),
    ]
    if deal["account_multiplier"] > 1:
        reasons.append(explainAccountSize(deal))
    return reasons


EXPLAINER_BY_QUEUE = {
    WORK_NOW_QUEUE: explainWorkNow,
    REQUALIFY_QUEUE: explainRequalify,
    QUALIFY_QUEUE: explainQualify,
}


def explainCycleLimit(model):
    return f"{CYCLE_QUANTILE:.0%} dos deals fechados fecham em até {model.cycleLimitDays} dias"


def explainExpectedValue(deal):
    return (
        f"Valor de catálogo {formatMoney(deal['sales_price'])} ({deal['product']}), "
        f"valor esperado de {formatMoney(deal['expected_value'])}."
    )


def explainAccountSize(deal):
    bonus = deal["account_multiplier"] - 1
    return (
        f"A receita da conta está no percentil {deal['revenue_percentile'] * 100:.0f} entre as "
        f"contas, o que soma um bônus de {bonus:.0%} no ranking."
    )


def formatMoney(amount):
    return f"{amount:,.0f}".replace(",", ".")
