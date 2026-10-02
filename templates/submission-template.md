# Submissão: Arthur Segheto, Challenge 003 (Lead Scorer)

## Sobre mim

- **Nome:** Arthur Segheto
- **LinkedIn:** linkedin.com/in/arthur-segheto-554497248 
- **Challenge escolhido:** 003, Lead Scorer (Vendas/RevOps)

## Executive Summary

Construí uma ferramenta em Streamlit que separa os 2.089 deals abertos do CRM em três filas (trabalhar agora, qualificar, requalificar ou encerrar), dá a cada deal um score de 0 a 100 e explica em linguagem de vendedor por que ele está naquela posição. O achado principal é que o pipeline está inflado: com o ciclo típico em 115 dias, 1.400 dos 1.589 deals em negociação (88%) já passaram do prazo e concentram 69% do valor de catálogo do pipeline. Os dados não permitem prever quem vai fechar: nenhuma variável tem sinal estatístico, e em um backtest temporal sem vazamento o score não superou a ordenação por preço (capturou menos receita nos três cortes testados). A recomendação é usar a ferramenta como triagem e higiene de pipeline, e não como previsor de fechamento.

## Solução

**O que roda:** aplicação Streamlit (`solution/app.py`) com filtros em cascata (região, manager, vendedor), KPIs, uma visão de vendedor com as três filas e a explicação de cada deal, uma visão gerencial de deals parados ("zumbis") e um botão que rascunha um e-mail de follow-up com o Gemini (opcional).

### Setup

Requisitos: Python 3.13 e os dados já incluídos em `solution/data/` (dataset CRM Sales Predictive Analytics, CC0).

```powershell
cd submissions/arthur-segheto/solution
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py