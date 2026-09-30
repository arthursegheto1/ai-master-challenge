import pandas as pd
import numpy as np
from scoring.data import loadPipeline, splitClosedAndOpenDeals
from scoring.probability import buildWinModel
from scoring.priority import prioritize

def runValidation():
    print("Iniciando validação do modelo de priorização...")
    allDeals = loadPipeline()
    closedDeals, _ = splitClosedAndOpenDeals(allDeals)
    
    # Ordena pelo fechamento para simular o tempo real
    closedDeals = closedDeals.sort_values("close_date")
    
    # Split: Treina com os primeiros 70% (passado), testa com os 30% mais recentes (futuro)
    splitIdx = int(len(closedDeals) * 0.7)
    trainDeals = closedDeals.iloc[:splitIdx].copy()
    testDeals = closedDeals.iloc[splitIdx:].copy()
    
    print(f"Treinando com {len(trainDeals)} deals do passado...")
    model = buildWinModel(trainDeals)
    
    # SIMULAÇÃO: Vamos fingir que os deals do teste estão 'Abertos' e 'Engaging'
    # Sorteamos uma 'idade' aleatória entre 1 dia e o ciclo real de fechamento deles
    np.random.seed(42)
    testDeals["deal_stage"] = "Engaging"
    testDeals["is_open"] = True
    testDeals["age_days"] = np.random.uniform(1, testDeals["cycle_days"] + 1)
    
    print(f"Avaliando priorização em {len(testDeals)} deals do futuro...")
    scoredTest = prioritize(testDeals, model)
    
    #  Top 20% de deals do pipeline futuro
    top20Cutoff = int(len(scoredTest) * 0.20)
    
    # Grupo 1:  Top 20% usando o Score inteligente
    topByScore = scoredTest.sort_values("score", ascending=False).head(top20Cutoff)
    
    # Grupo 2: O Baseline burro (ordenando apenas pelo valor mais caro)
    topByPrice = scoredTest.sort_values("sales_price", ascending=False).head(top20Cutoff)
    
    print("\n--- RESULTADOS DA VALIDAÇÃO (TOP 20% DO PIPELINE) ---")
    print(f"Taxa de Vitória Global no período de Teste: {testDeals['won'].mean():.1%}")
    print(f"Taxa de Vitória do Top 20% (Apenas Preço): {topByPrice['won'].mean():.1%}")
    print(f"Taxa de Vitória do Top 20% (Nosso Score): {topByScore['won'].mean():.1%}")
    
    # Cálculo de receita capturada nos deals ganhos dentro desse top 20%
    precoGanhoPreco = (topByPrice['sales_price'] * topByPrice['won']).sum()
    precoGanhoScore = (topByScore['sales_price'] * topByScore['won']).sum()
    
    print("\n--- IMPACTO FINANCEIRO ESTIMADO ---")
    print(f"Receita capturada ordenando por Preço: $ {precoGanhoPreco:,.0f}")
    print(f"Receita capturada com o Novo Score:  $ {precoGanhoScore:,.0f}")
    print("-----------------------------------------------------")

if __name__ == "__main__":
    runValidation()