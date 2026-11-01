# 🚦 Análise de Sinistros de Trânsito em Bauru/SP

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Pandas](https://img.shields.io/badge/pandas-2.0%2B-150458.svg)](https://pandas.pydata.org/)
[![Scikit-Learn](https://img.shields.io/badge/scikit--learn-1.4%2B-orange.svg)](https://scikit-learn.org/)
[![Plotly](https://img.shields.io/badge/plotly-5.24%2B-3F4F75.svg)](https://plotly.com/)

Estudo de Ciência de Dados sobre os registros de trânsito de **Bauru/SP** no Infosiga SP, com ingestão de dados estaduais, análise estatística, modelo exploratório de gravidade, mapa interativo e painel em Streamlit.

Os números abaixo usam os dados de 13/01/2015 a 30/09/2026. O painel calcula seus indicadores a partir da base atual, e o [relatório técnico](output/relatorios/relatorio_final_bauru.md) traz a análise completa. As correções ao estudo de 30/09/2026 estão na [errata](output/relatorios/ERRATA.md).

---

## 📌 Principais resultados

- **Base:** 19.056 registros (`cod_ibge == 3506003`), dos quais 7.645 são notificações (40,1%). Há 496 óbitos, 1.147 feridos graves e 10.745 feridos leves.
- **Dados de vítimas:** 43,5% dos registros não informam vítimas, o que não significa que ninguém se feriu.
- **Letalidade:** atropelamentos têm 11,63% de sinistros com óbito, choques 5,83% e colisões 1,45%. A diferença entre choque e colisão é urbana: 5,9 vezes nas vias urbanas e 0,9 nas rodovias.
- **Vias:** as vias urbanas têm 53% dos óbitos, e estradas e rodovias, 40%. A letalidade por sinistro é maior nas rodovias (6,5%, contra 1,9%). SP-300, SP-225 e SP-294 somam 35% dos óbitos.
- **Dias:** a média é de 6,70 registros/dia em dias úteis e 6,63 em fins de semana (p = 0,634). Isso não prova igualdade, e sexta (7,75) e sábado (7,35) ficam acima dos demais dias.
- **Modais:** entre registros com modal informado, há automóvel em 72,4% e motocicleta em 64,3%. A base não liga cada vítima ao seu veículo nem traz frota, então não mede o risco de cada modal.
- **Modelo:** a acurácia de 88,4% é praticamente a de sempre prever a classe mais comum (88,2%), com ROC-AUC de 0,683. O modelo é exploratório e não prevê acidentes.

### Comparabilidade

De 2015 a 2018, só há sinistros fatais. A partir de 2019, entram sinistros não fatais e notificações, que vão de 11,8% a 60,1% dos registros por ano. Por isso, o total anual não mede tendência. Letalidade, perfis de gravidade e modelo usam a **base comparável**: sinistros de 2019 em diante, sem notificações.

### Limitações

A base não traz fluxo de veículos, frota, velocidade, alcoolemia nem o objeto atingido em choques. Volumes não medem risco, e as recomendações são hipóteses a validar em campo.

---

## 📊 Visualizações

![Registros e óbitos por ano](output/graficos/acidentes_por_ano.png)

![Registros por dia e hora](output/graficos/acidentes_dia_e_hora.png)

![Letalidade por tipo e presença de modais](output/graficos/tipos_e_veiculos.png)

![Registros por dia da semana e hora](output/graficos/heatmap_dia_hora.png)

![Importância de permutação no modelo](output/graficos/importancia_features_ml.png)

O mapa interativo está em `output/graficos/mapa_acidentes.html`.

---

## 📂 Estrutura do Projeto

```text
projeto_transito_bauru/
├── app.py                               # Painel em Streamlit
├── data/
│   ├── bauru_limpo.csv                  # Base tratada, versionada
│   └── sinistros_*.csv                  # Arquivos brutos do Infosiga, fora do Git
├── notebooks/                           # Exploração, limpeza, análise e mapa
├── output/
│   ├── graficos/                        # Figuras PNG e mapa HTML
│   └── relatorios/
│       ├── relatorio_final_bauru.md     # Relatório técnico atual
│       ├── resumo_anual_bauru.csv       # Tabela anual
│       ├── relatorio_bauru.pdf          # Estudo de 30/09/2026 (histórico)
│       └── ERRATA.md                    # Correções ao estudo de 30/09/2026
├── scripts/
│   ├── atualizar_dados_infosiga.py      # Atualização incremental pela API do Infosiga
│   ├── gerar_artefatos.py               # Gráficos, mapa e relatório a partir da base
│   ├── process_bauru_pipeline.py        # Reconstrução a partir dos arquivos brutos
│   └── create_notebooks.py              # Gerador dos notebooks
├── src/
│   ├── metricas.py                      # Regras estatísticas compartilhadas
│   └── modelo.py                        # Modelo exploratório
└── tests/
```

---

## 🛠️ Como Reproduzir

```bash
python3 -m venv .venv
```

```bash
source .venv/bin/activate
```

```bash
pip install -r requirements.txt
```

Atualizar a base com os meses novos, reprocessando os três mais recentes para incorporar revisões da fonte:

```bash
python scripts/atualizar_dados_infosiga.py --automatico
```

Regenerar gráficos, mapa e relatório. A atualização mensal automática grava só a base e o resumo anual, então rode este comando para atualizar também esses arquivos e confira os números deste README:

```bash
python scripts/gerar_artefatos.py
```

Abrir o painel:

```bash
streamlit run app.py
```

Rodar os testes:

```bash
python -m unittest discover -s tests
```

Para reconstruir a base do zero, coloque os arquivos brutos em `data/sinistros_*.csv` e execute `python scripts/process_bauru_pipeline.py`.
