import streamlit as st

from scoring.data import REFERENCE_DATE, loadPipeline, splitClosedAndOpenDeals
from scoring.explanations import formatMoney
from scoring.priority import prioritize
from scoring.probability import CYCLE_QUANTILE, buildWinModel
from scoring.queues import QUALIFY_QUEUE, REQUALIFY_QUEUE, WORK_NOW_QUEUE
from scoring.summaries import (
    dealsInQueue,
    filterByValues,
    summarizePipeline,
    summarizeStaleDealsBySalesAgent,
)

PAGE_TITLE = "Lead Scorer"
REASONS_COLUMN = "Por quê"
STALE_AGENTS_SHOWN_IN_CHART = 15

COLUMNS_BY_QUEUE = {
    WORK_NOW_QUEUE: {
        "score": "Score",
        "product": "Produto",
        "sales_price": "Valor",
        "win_probability": "Chance",
        "days_until_cycle_limit": "Dias até o limite",
        "sales_agent": "Vendedor",
        "next_action": "Próxima ação",
    },
    QUALIFY_QUEUE: {
        "score": "Score",
        "product": "Produto",
        "sales_price": "Valor",
        "account": "Conta",
        "sales_agent": "Vendedor",
        "next_action": "Próxima ação",
    },
    REQUALIFY_QUEUE: {
        "score": "Score",
        "product": "Produto",
        "sales_price": "Valor",
        "age_days": "Dias em aberto",
        "sales_agent": "Vendedor",
        "next_action": "Próxima ação",
    },
}

QUEUE_COLUMN_CONFIG = {
    "Score": st.column_config.ProgressColumn("Score", min_value=0, max_value=100, format="%d"),
    "Valor": st.column_config.NumberColumn("Valor", format="localized"),
    "Chance": st.column_config.NumberColumn("Chance", format="percent"),
    "Dias até o limite": st.column_config.NumberColumn("Dias até o limite", format="%d"),
    "Dias em aberto": st.column_config.NumberColumn("Dias em aberto", format="%d"),
}

STALE_BY_AGENT_COLUMNS = {
    "sales_agent": "Vendedor",
    "manager": "Manager",
    "open_deals": "Deals abertos",
    "work_now_deals": "Trabalhar agora",
    "qualify_deals": "Qualificar",
    "stale_deals": "Zumbis",
    "stale_share": "% zumbis",
    "stale_value": "Valor parado",
}

STALE_BY_AGENT_COLUMN_CONFIG = {
    "% zumbis": st.column_config.NumberColumn("% zumbis", format="percent"),
    "Valor parado": st.column_config.NumberColumn("Valor parado", format="localized"),
}


@st.cache_data
def loadScoredPipeline():
    closedDeals, openDeals = splitClosedAndOpenDeals(loadPipeline())
    model = buildWinModel(closedDeals)
    return prioritize(openDeals, model), model.cycleLimitDays


def sortedUniqueValues(deals, column):
    return sorted(deals[column].dropna().unique())


def applySidebarFilters(deals):
    st.sidebar.header("Filtros")
    selectedRegions = st.sidebar.multiselect("Região", sortedUniqueValues(deals, "regional_office"))
    dealsInRegions = filterByValues(deals, "regional_office", selectedRegions)
    selectedManagers = st.sidebar.multiselect("Manager", sortedUniqueValues(dealsInRegions, "manager"))
    dealsOfManagers = filterByValues(dealsInRegions, "manager", selectedManagers)
    selectedAgents = st.sidebar.multiselect("Vendedor", sortedUniqueValues(dealsOfManagers, "sales_agent"))
    return filterByValues(dealsOfManagers, "sales_agent", selectedAgents)


def formatCount(count):
    return f"{count:,}".replace(",", ".")


def renderKpis(deals):
    summary = summarizePipeline(deals)
    openDealsColumn, valueColumn, workNowColumn, staleColumn = st.columns(4)
    openDealsColumn.metric("Deals abertos", formatCount(summary.openDeals))
    valueColumn.metric("Valor no pipeline", f"$ {formatMoney(summary.pipelineValue)}")
    workNowColumn.metric("Para trabalhar agora", formatCount(summary.workNowDeals))
    staleColumn.metric("Além do ciclo típico", f"{summary.staleShare:.0%}")


def buildQueueTable(queueDeals, queue):
    table = queueDeals[list(COLUMNS_BY_QUEUE[queue])].rename(columns=COLUMNS_BY_QUEUE[queue])
    return table.assign(**{REASONS_COLUMN: queueDeals["reasons"].apply(" ".join)})


def renderDealDetails(deal):
    st.markdown(f"**Por que este deal tem score {deal['score']}**")
    for reason in deal["reasons"]:
        st.markdown(f"- {reason}")
    st.caption(f"Próxima ação sugerida: {deal['next_action']}")


def renderQueue(deals, queue, key):
    queueDeals = dealsInQueue(deals, queue).sort_values("score", ascending=False)
    if queueDeals.empty:
        st.info("Nenhum deal nesta fila com os filtros atuais.")
        return
    event = st.dataframe(
        buildQueueTable(queueDeals, queue),
        column_config=QUEUE_COLUMN_CONFIG,
        hide_index=True,
        width="stretch",
        on_select="rerun",
        selection_mode="single-row",
        key=key,
    )
    selectedRows = event.selection.rows
    if selectedRows:
        renderDealDetails(queueDeals.iloc[selectedRows[0]])
    else:
        st.caption("Selecione uma linha para ver por que o deal está nesta posição.")


def renderSalesView(deals):
    st.subheader(f"{WORK_NOW_QUEUE}")
    st.caption("Deals dentro do ciclo típico, ordenados pelo score. Comece por aqui.")
    renderQueue(deals, WORK_NOW_QUEUE, key="work-now-queue")
    with st.expander(f"{QUALIFY_QUEUE}: prospecções sem data de entrada"):
        renderQueue(deals, QUALIFY_QUEUE, key="qualify-queue")
    with st.expander(f"{REQUALIFY_QUEUE}: deals além do ciclo típico"):
        renderQueue(deals, REQUALIFY_QUEUE, key="requalify-queue")


def renderManagementView(deals, cycleLimitDays):
    summary = summarizePipeline(deals)
    staleDealsColumn, staleValueColumn, staleShareColumn = st.columns(3)
    staleDealsColumn.metric("Deals zumbis", formatCount(summary.staleDeals))
    staleValueColumn.metric("Valor parado", f"$ {formatMoney(summary.staleValue)}")
    staleShareColumn.metric("% do pipeline", f"{summary.staleShare:.0%}")
    st.caption(
        f"Zumbi é o deal em Engaging aberto além do ciclo típico: {CYCLE_QUANTILE:.0%} dos deals "
        f"fechados fecham em até {cycleLimitDays} dias. Idades medidas até {REFERENCE_DATE:%d/%m/%Y}."
    )
    staleBySalesAgent = summarizeStaleDealsBySalesAgent(deals)
    st.subheader("Pipeline parado por vendedor")
    st.dataframe(
        staleBySalesAgent[list(STALE_BY_AGENT_COLUMNS)].rename(columns=STALE_BY_AGENT_COLUMNS),
        column_config=STALE_BY_AGENT_COLUMN_CONFIG,
        hide_index=True,
        width="stretch",
    )
    st.bar_chart(
        staleBySalesAgent.head(STALE_AGENTS_SHOWN_IN_CHART),
        x="sales_agent",
        y="stale_value",
        x_label="Vendedor",
        y_label="Valor parado",
    )


st.set_page_config(page_title=PAGE_TITLE, layout="wide")
scoredDeals, cycleLimitDays = loadScoredPipeline()
filteredDeals = applySidebarFilters(scoredDeals)

st.title(PAGE_TITLE)
st.caption("Priorização do pipeline aberto: onde focar primeiro e por quê.")

if filteredDeals.empty:
    st.warning("Nenhum deal aberto com os filtros atuais.")
    st.stop()

renderKpis(filteredDeals)
salesTab, managementTab = st.tabs(["Fila de trabalho", "Visão gerencial"])
with salesTab:
    renderSalesView(filteredDeals)
with managementTab:
    renderManagementView(filteredDeals, cycleLimitDays)
