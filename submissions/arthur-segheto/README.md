# Submissão: Arthur Segheto, Challenge 003 (Lead Scorer)

## Sobre mim

- **Nome:** Arthur Segheto
- **LinkedIn:** [PREENCHER]
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
```

A aplicação abre em `http://localhost:8501`. Com Docker:

```bash
docker build -t lead-scorer .
docker run --rm -p 8501:8501 lead-scorer
```

O rascunho de e-mail com IA é opcional. Para ativá-lo, defina a chave antes de subir o app (`$env:GEMINI_API_KEY = "..."` no PowerShell, ou `-e GEMINI_API_KEY=...` no `docker run`). Sem a chave, o botão continua funcionando com um modelo de texto fixo e avisa na tela que não usou IA. Nunca versione a chave. O modelo padrão é `gemini-3.5-flash`; para usar outro, defina `GEMINI_MODEL` (`$env:GEMINI_MODEL = "nome"`). Os nomes de modelo mudam com frequência (o `gemini-2.5-flash` já não está disponível para contas novas), e a lista do que a sua chave enxerga sai de `python -c "from google import genai; c = genai.Client(); [print(m.name) for m in c.models.list()]"`.

Testes e backtest:

```powershell
pytest -q
python -m validation.run
```

### Lógica de scoring

Os dados não sustentam um modelo estatístico (ver Resultados), então o score é um conjunto de regras explicáveis.

| Fila | Regra | Deals |
|---|---|---|
| Trabalhar agora | Engaging com idade até o ciclo típico (115 dias, percentil 95 dos ciclos fechados) | 189 |
| Requalificar ou encerrar | Engaging além do ciclo típico, sem histórico comparável | 1.400 |
| Qualificar | Prospecting (não tem data de entrada, então não tem idade) | 500 |

- **Chance de fechar:** em "Trabalhar agora", é a taxa histórica de vitória dos deals fechados que chegaram àquela idade (63% no geral, até cerca de 74% perto do limite). Em "Qualificar", a taxa base. Em "Requalificar", não é estimada. O vendedor não entra no cálculo: a conversão dele é mérito do vendedor e não propriedade do deal.
- **Valor de ranking:** em "Trabalhar agora", valor esperado (preço de catálogo vezes chance). Em "Requalificar", o preço com um peso que cai pela metade a cada ciclo além do limite, o que é uma premissa de negócio e não um achado dos dados. Em "Qualificar", o valor esperado com bônus de até 25% pelo percentil de receita da conta, neutro quando a conta não é conhecida.
- **Score de 0 a 100 dentro de cada fila:** 50% do ranking por valor e 50% do ranking por urgência (dias que faltam para o deal passar do limite). A urgência só existe em "Trabalhar agora".
- **Explicação por deal:** de duas a quatro frases com idade, chance, valor e a próxima ação sugerida.

Os pesos, a meia-vida do decaimento e o bônus de conta são constantes nomeadas em `solution/scoring/priority.py`. A data de referência para medir idades é 31/12/2017, o último `close_date` do dataset.

## Abordagem

1. Entendi o problema antes de abrir qualquer ferramenta: cruzei as quatro tabelas, medi nulos, ciclos e taxas de vitória.
2. Testei se havia sinal para prever fechamento (qui-quadrado por variável e um modelo logístico com split temporal). Não havia, e isso definiu a decisão de usar regras em vez de ML.
3. Descobri o pipeline inflado olhando a distribuição dos ciclos dos deals fechados contra a idade dos abertos, e organizei a ferramenta em torno dele (as três filas).
4. Escrevi o motor de scoring em módulos pequenos com testes, e a interface por cima. Fiz uma revisão crítica do motor e corrigi três fragilidades (ver o process log).
5. Validei com um backtest temporal e documentei o resultado como ele saiu.

## Resultados / Findings

**Os dados.** 8.800 oportunidades: 4.238 ganhas, 2.473 perdidas, 1.589 em negociação e 500 em prospecção. Taxa de vitória de 63,2% entre as fechadas.

**Sem sinal preditivo.** Vendedor, produto, setor, região, manager e receita da conta não têm relação estatística com ganhar (p-valores entre 0,26 e 0,97; a taxa de vitória é plana entre quartis de receita). Um modelo logístico treinado até 16/08/2017 e testado depois tem AUC de 0,50. A diferença entre vendedores (55% a 70%) cabe no ruído, com 150 a 275 deals fechados cada um. O dataset parece sintético.

**Pipeline inflado.** Os deals fechados levam 57 dias (mediana dos ganhos) e 14 dias (mediana dos perdidos), com 95% fechando em até 115 dias. Dos 1.589 em negociação, 1.400 já passaram disso. Esses deals somam 3,4 milhões de 5,0 milhões de valor de catálogo (69%).

**Backtest temporal.** Para cada data de corte, o modelo é treinado só com deals fechados até aquele dia e avalia os deals que estavam abertos nele (idade medida do corte, não da duração final, para não vazar o desfecho). Foram avaliados os deals da fila "Trabalhar agora", comparando o top 20% do score com o top 20% por preço:

| Corte | Deals | Vitória geral | Top 20% por preço | Top 20% por score | Diferença (IC 95%) | Receita preço | Receita score |
|---|---|---|---|---|---|---|---|
| 28/08/2017 | 855 | 70,1% | 73,7% | 78,4% | de -1,8 a +12,9 p.p. | 696.288 | 611.711 |
| 29/09/2017 | 905 | 61,1% | 56,9% | 58,0% | de -9,9 a +5,0 p.p. | 558.831 | 464.965 |
| 03/11/2017 | 1.003 | 64,1% | 62,5% | 56,0% | de -17,5 a -3,0 p.p. | 674.147 | 498.482 |

Em dois cortes a diferença de taxa de vitória é indistinguível de zero, e no terceiro o score é pior que o preço. Em todos, o score captura menos receita (de 12% a 26% a menos). Uma análise de sensibilidade mostra por quê: com peso zero para a urgência, o top 20% do score é idêntico ao do preço, porque a chance estimada varia pouco (67% a 74%) perto da diferença de preços entre produtos (de 55 a 26.768). O que diferencia o score do preço é a urgência, e os dados não mostram que urgência prediga fechamento.

**Artefato nos dados, região Central.** Os 500 deals em prospecção são todos da região Central, e os 408 deals em negociação de lá foram engajados entre 19/07 e 15/08/2017, então nenhum cai no ciclo típico. East e West não têm prospecção. Por isso um gestor de Central vê a fila "Trabalhar agora" vazia, e 29% dos deals zumbis vêm dessa única janela de quatro semanas. Isso parece resultado de como a base foi gerada e distorce a leitura do "pipeline inflado".

## Recomendações

1. **Higienizar o pipeline.** Requalificar ou encerrar os 1.400 deals além do ciclo típico, começando pelos de maior valor. Esse é o ganho operacional mais claro que os dados sustentam.
2. **Não vender o score como previsão.** Usá-lo para triagem e transparência, e revisitar o peso da urgência (hoje 50%) conforme a empresa decidir se evitar deals parados vale mais do que capturar receita no topo da lista.
3. **Registrar conta e data de entrada já na prospecção.** Hoje 68% dos deals abertos não têm conta e a prospecção não tem data, o que limita qualquer priorização.
4. **Repetir o backtest com dados reais** da empresa, que provavelmente têm sinal que este dataset não tem.

## Limitações

- O decaimento dos deals parados e o bônus de conta são premissas de negócio, não achados. A receita da conta não mostrou relação com fechar.
- A curva de vitória por idade assume que deals abertos se comportam como os já fechados, e tem viés de sobrevivência (os perdidos fecham cedo).
- O percentil 95, a data de referência e os pesos são decisões minhas, documentadas e ajustáveis, mas não calibradas.
- Nas filas "Qualificar" e "Requalificar" o ranking continua muito correlacionado com o preço do produto (Spearman de 0,985 e 0,93).
- O backtest usa um corte por vez e avalia só a fila "Trabalhar agora"; a tese dos deals zumbis não é testável com deals fechados.
- O serviço do Gemini pode responder com erro de sobrecarga (503). Nesse caso o botão mostra um modelo de texto fixo e informa o motivo na tela, em vez de fingir que a IA respondeu.
- O rascunho de e-mail envia ao Gemini o produto, a fila, os dias em aberto, o valor e o nome da conta quando existe. Não vai nenhum dado pessoal, mas o texto gerado deve ser revisado antes de enviar. A chamada real à API do Gemini não é exercitada pelos testes automáticos (eles usam um escritor simulado): [CONFIRMAR com a chave real].
- O Dockerfile não foi executado no ambiente em que o código foi escrito: [CONFIRMAR após testar o build].

## Process Log: Como usei IA

O detalhamento está em [`process-log/log.md`](process-log/log.md). Resumo:

### Ferramentas usadas

| Ferramenta | Para que usou |
|---|---|
| Claude (Anthropic) | Exploração dos dados executando código sobre os CSVs, desenho do scoring, geração e teste do código, reprodução e crítica do backtest, revisão do módulo de e-mail |
| Gemini (Google) | Revisão crítica da estratégia e do código, versão inicial do módulo de e-mail com IA, [PREENCHER] |
| PowerShell, Git, VS Code, pytest | Execução, versionamento e verificação local de cada etapa |

### Workflow

Exploração e decisão de não usar ML, desenho das filas, implementação em fases com testes, revisão crítica, validação, interface e recurso de IA. Cada fase foi aplicada e testada localmente antes da seguinte.

### Onde a IA errou e como corrigi

- A primeira versão do score era quase só ordenar por preço (correlação de 0,98). Foi medido, e o desenho passou a misturar valor e urgência.
- Ajuste por vendedor e limite de ciclo pelo máximo: a minha revisão crítica identificou os dois como fragilidades, e foram trocados por remoção do ajuste e percentil 95.
- Minha primeira leitura do backtest ("ganho real de 2,3 p.p.") foi contestada: a diferença está dentro do ruído, e simular deals fechados como abertos exige medir a idade a partir de uma data de corte, não da duração final. Refiz com corte temporal e intervalo de confiança.
- O módulo de e-mail usava um SDK descontinuado e escondia falhas atrás de um modelo fixo apresentado como IA. Foi reescrito com o SDK atual e passou a avisar na tela quando não usa IA.
- Comandos do assistente em bash que não funcionavam no PowerShell, incluindo pastas criadas por engano em `C:\`, e um `.gitignore` da raiz que escondia a pasta da submissão.

### O que adicionei que a IA sozinha não faria

Os padrões de código (camelCase e Clean Code), a revisão crítica do motor com as três correções, a decisão de recusar a interpretação otimista do backtest e documentá-lo como resultado nulo, a escolha dos parâmetros de negócio (pesos, meia-vida, bônus) e a verificação de cada etapa no meu ambiente real.

### Evidências

- [x] Git history (commits por fase na branch `submission/arthur-segheto`)
- [ ] Chat exports em `process-log/chat-exports/` [PREENCHER]
- [ ] Screenshots do app e dos testes em `process-log/screenshots/` [PREENCHER]

**Submissão enviada em:** [PREENCHER]