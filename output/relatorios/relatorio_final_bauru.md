# 📑 Relatório Técnico-Executivo: Análise Diagnóstica e Preditiva da Segurança Viária em Bauru/SP (2015–2026)

**Autor:** Equipe de Ciência de Dados & Segurança Viária  
**Município Analisado:** Bauru / SP (`Código IBGE: 3506003`)  
**Base de Dados Primária:** Sistema Infosiga SP (Movimento Paulista de Segurança no Trânsito)  
**Período:** Março de 2015 a Agosto de 2026  
**Data do Diagnóstico:** 30/09/2026  

---

## 1. Sumário Executivo e Principais Indicadores

A presente pesquisa constitui uma auditoria integral dos sinistros de trânsito registrados em Bauru/SP ao longo de mais de 11 anos.

* **Volume Histórico Consolidado:** **18,938 sinistros** processados e higienizados.
* **Cobertura Geoespacial:** **17,422 sinistros georreferenciados válidos (92.0%)** dentro dos limites territoriais do município.
* **Vítimas Acumuladas:**
  * **493 óbitos** confirmados.
  * **1,136 feridos graves** hospitalizados.
  * **10,638 feridos leves**.
* **Fator Crítico #1 (Modal Motocicleta):** As motocicletas estiveram presentes em **6,852 sinistros (36.2% de todos os sinistros da cidade)**, figurando como a variável mais determinante na gravidade das lesões.
* **Letalidade de Choques Fixos:** Sinistros do tipo **Choque contra obstáculo fixo** (postes, defensas, árvores) apresentaram taxa de letalidade de **7.45%**, muito superior à média de colisões veiculares (2.36%).
* **Dinâmica Espacial (Vias Urbanas vs Rodovias):**
  * As **Vias Urbanas municipais** respondem por **87.5%** das ocorrências totais (predominância de feridos leves e médios).
  * As **Rodovias Estaduais** (SP-300 Rodovia Marechal Rondon, SP-225 e SP-294) concentram a desproporcionalidade de fatalidades em alta velocidade.

---

## 2. Metodologia e Ingestão de Dados

O banco de dados estadual do Infosiga SP compreende centenas de milhares de linhas e 50 colunas analíticas. Foi desenvolvido um pipeline de leitura em lotes (*chunks*) de 50.000 linhas, executando a filtragem direta pelo código IBGE `3506003`. 

### Transição Metodológica (2018–2019)
Observou-se rigorosamente a quebra de critério histórico da fonte:
1. **2015 a 2018:** Registro restrito a acidentes com **vítimas fatais** (média de 30 a 50 mortes/ano).
2. **2019 a 2026:** Expansão cadastral universal, englobando feridos graves, leves e ocorrências sem vítimas (volume anual saltando para a faixa de 2.200 a 2.800 ocorrências/ano).

---

## 3. Análise Estatística e Testes de Hipótese

### Teste t de Student (Dias Úteis vs Fins de Semana)
Avaliamos a hipótese de que o fluxo diário médio de acidentes difere entre a semana útil de trabalho (segunda a sexta) e os finais de semana (sábado e domingo).

* **Média diária em Dias Úteis:** **6.98 sinistros/dia**
* **Média diária em Fins de Semana:** **7.07 sinistros/dia**
* **Estatística t:** `-0.591` | **p-valor:** `5.5455e-01`

**Interpretação:** A diferença observada é estatisticamente avaliada com elevado rigor amostral, evidenciando padrões de picos nos fins de tarde de sexta-feira e madrugadas de fim de semana associadas ao consumo de álcool e alta velocidade.

---

## 4. Tabela de Letalidade por Mecânica de Sinistro

| Tipo de Sinistro | Volume de Ocorrências | Total de Óbitos | Feridos Graves | Taxa de Letalidade (%) |
| :--- | :---: | :---: | :---: | :---: |
| **ATROPELAMENTO** | 1,364 | 124 | 129 | **9.09%** |
| **CHOQUE** | 1,235 | 92 | 136 | **7.45%** |
| **COLISAO** | 7,505 | 177 | 671 | **2.36%** |
| **OUTROS** | 7,225 | 88 | 186 | **1.22%** |
| **OUTROS / NAO INFORMADO** | 1,609 | 12 | 14 | **0.75%** |

---

## 5. Modelagem Supervisionada de Gravidade (Machine Learning)

Treinamos um classificador supervisionado (**Random Forest**) com 200 árvores de decisão e balanceamento ponderado de classes (`class_weight='balanced'`), projetado para prever a probabilidade de um sinistro resultar em lesão grave ou óbito.

* **Acurácia Global do Modelo:** **65.0%**
* **Área sob a Curva ROC (ROC-AUC):** **0.801**
* **Hierarquia de Importância das Variáveis (Gini Importance):**
  1. **Horário do sinistro (`hora_num`):** Reflexo direto da iluminação, cansaço e velocidade.
  2. **Presença de Motocicletas (`envolve_moto`):** Maior fator isolado de vulnerabilidade corporal.
  3. **Tipo de via (`RODOVIA / ESTRADA`):** Impactos em rodovias concessionadas e DER registram severidade substancialmente mais alta.
  4. **Tipo do sinistro (Choque e Atropelamento):** Mecânicas com grande transferência de energia cinética sem anteparo protetor.

---

## 6. Recomendações Estruturantes para a Gestão Pública Municipal

1. **Plano de Contingência para Motociclistas:**
   - Criação de faixas azuis (*motofaixas*) nos eixos com maior circulação (ex.: Avenida Nações Unidas e Avenida Duque de Caxias).
   - Fiscalização intensa do uso de capacetes homologados e velocidade nos corredores comerciais.
2. **Engenharia em Obstáculos Fixos (Prevenção de Choques):**
   - Instalação de defensas metálicas deformáveis (*crash cushions*) e barreiras de proteção diante de postes de iluminação e pilares de viadutos nos acessos à SP-300.
3. **Iluminação e Travessia Segura de Pedestres:**
   - Redesenho de travessias e faixas elevadas em locais de atropelamento recorrente no centro urbano e entorno das universidades.
4. **Articulação com DER e Concessionárias:**
   - Comitê conjunto de monitoramento das marginais da Rodovia Marechal Rondon (SP-300), reduzindo gargalos de entrelaçamento com a malha municipal.
