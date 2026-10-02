# Process log: Challenge 003 (Lead Scorer)

Registro de como usei IA para chegar na solução.

## 1. Ferramentas e por quê

| Ferramenta | Uso |
|---|---|
| Claude (Anthropic, claude.ai) | Escolha do desafio, exploração dos dados executando código nos CSVs, desenho do scoring, geração e teste do código em fases, reprodução e crítica do meu backtest, revisão do módulo de e-mail, rascunho da documentação |
| Gemini (Google) | Segunda opinião: revisão crítica da estratégia e do código, versão inicial do módulo de e-mail com IA, |
| PowerShell, Git, VS Code, pytest, Streamlit | Execução, versionamento e verificação de cada etapa no meu ambiente (Windows) |

Usei duas IAs de propósito: uma para construir e testar com execução de código, outra para questionar o que foi construído. Os pontos em que as duas divergiram ou em que eu discordei de uma delas estão na seção 3.

## 2. Como decompus o problema antes de promptar

1. **Escolha do desafio.** Comparei os quatro desafios com a minha stack (Python, SQL, React, Docker) e com o formato da vaga. Escolhi o 003 porque o entregável é software funcionando e o enunciado aceita qualquer stack.
2. **Entender os dados antes de modelar.** Pedi a análise das quatro tabelas: nulos por estágio, divergências de nomes, durações dos ciclos e taxa de vitória por vendedor, produto, setor e região. Daí saíram os achados que definiram o projeto: 68% dos deals abertos sem conta, ciclo máximo de 138 dias contra deals abertos com mais de 400, e nenhuma variável com sinal estatístico (AUC 0,50 num split temporal).
3. **Decidir o tipo de solução.** Com a falta de sinal, descartei ML e adotei regras explicáveis, que é o que o enunciado de qualquer forma valoriza.
4. **Dividir em fases**: dados, motor de scoring, validação, interface, recurso de IA, empacotamento e documentação. Cada fase foi aplicada e testada localmente antes da seguinte.
5. **Padrões de código definidos por mim**: camelCase em Python, Clean Code de Robert C. Martin, sem comentários desnecessários, sem `main()` explícito e revisão do código antes de aplicar.

## 3. Onde a IA errou e como corrigi

| O que aconteceu | Como foi detectado | Correção |
|---|---|---|
| Comandos em bash no meu PowerShell (`mkdir -p` com chaves, variável `$base` vazia). O comando criou três pastas em `C:\` | Mensagem de erro no terminal e um `Test-Path` que retornou `True` | O assistente tinha dito que provavelmente falhariam por permissão e estava errado. Verifiquei datas e conteúdo das pastas e as apaguei com segurança |
| `git add` com `:(exclude)` não adicionou nada, e o `git status` veio vazio | Saída vazia no terminal e o Explorer do VS Code mostrando os arquivos como adicionados | Passei a adicionar arquivo por arquivo |
| O `.gitignore` da raiz do repositório ignora `submissions/` | `git status --ignored` e `git check-ignore -v` | `git add -f` por arquivo, sem nunca adicionar a pasta inteira (a `.venv` entraria) |
| Primeira versão do score ficou quase igual a ordenar por preço (correlação de Spearman de 0,98) | O assistente mediu a correlação depois de rodar o código | Score com valor esperado e urgência (correlação de 0,64 a 0,68 em "Trabalhar agora") e um teste de regressão |
| Código em snake_case e com funções longas, contra o meu padrão | Revisão minha | Reescrita em camelCase, funções pequenas, constantes nomeadas |
| Limite de ciclo pelo máximo (frágil a outliers), ajuste da chance pela taxa do vendedor (viés conceitual: punir júnior) e ranking que virava só preço nas filas sem urgência | Minha revisão crítica, junto com o Gemini | Percentil 95, remoção do ajuste por vendedor, decaimento de tempo na fila de requalificar e bônus por receita da conta na fila de qualificar. O assistente discordou em parte (o decaimento é premissa, não achado; a receita não tem sinal) e isso foi documentado |
| Minha leitura do backtest: "ganho real de 2,3 p.p. de eficiência" | O assistente reproduziu o método e calculou o intervalo de confiança: de -5,0 a +4,7 p.p., ou seja, ruído | Backtest refeito com corte temporal sem vazamento, três cortes e intervalo de confiança. Resultado: o score não supera o preço. Documentado como resultado nulo |
| Módulo de e-mail com IA: SDK `google-generativeai` descontinuado, falha escondida atrás de um modelo fixo apresentado como IA, assinatura com o meu nome fixa no código e rascunho que sumia ao editar [CONFIRMAR cada ponto no seu código] | Revisão do código colado na conversa e checagem da documentação do Gemini | Reescrita com o SDK `google-genai`, aviso na tela quando não usa IA, assinatura pelo vendedor do deal e rascunho preservado entre interações |

## 4. O que eu adicionei que a IA sozinha não faria

- **Padrões e disciplina de código.** Exigi camelCase, Clean Code e revisão antes de aplicar, e rejeitei o primeiro código quando não seguia isso.
- **Revisão crítica do motor de scoring** com olhar de RevOps, que levou às três correções da seção 3.
- **Decisões de negócio:** aprovei os pesos 50/50 entre valor e urgência, a meia-vida do decaimento e o bônus de conta de 25%, e aceitei documentá-los como premissas.
- **Rodar a validação por conta própria** e depois aceitar que a minha interpretação estava errada e que um resultado nulo bem reportado vale mais do que um ganho que não se sustenta.
- **Verificação no ambiente real:** terminal do Windows, Git com o `.gitignore` da raiz, testes e app rodando na minha máquina.
- **A ideia do recurso de e-mail com IA**, para mostrar IA generativa embutida no fluxo do vendedor, mantido opcional e sinalizado quando cai no texto fixo.

## 5. Iterações

- **Scoring:** 3 versões (valor esperado puro, mistura valor e urgência, versão após a revisão crítica).
- **Validação:** 3 rodadas (meu script, reprodução com intervalo de confiança, backtest limpo com três cortes e sensibilidade ao peso da urgência).
- **Interface:** 1 versão principal e ajustes em cima de testes automatizados.
- **Recurso de e-mail:** versão inicial com o Gemini e uma reescrita após revisão.
- **Testes:** de 4 testes (módulo de dados) até a suíte final com 60 testes, incluindo testes headless do Streamlit.
- **Tempo total:**. O desafio recomenda 4 a 6 horas; a solução passou disso e o motivo está na quantidade de ciclos de revisão e de validação.

## 6. Evidências

- Histórico do git na branch `submission/arthur-segheto`, com commits por fase.
- Screenshots do app, dos testes e do backtest: `screenshots/`.