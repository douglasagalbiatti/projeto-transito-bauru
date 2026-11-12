# Relatório técnico: segurança viária em Bauru/SP

**Município:** Bauru/SP (`IBGE 3506003`)
**Fonte:** Infosiga SP
**Período dos dados:** 13/01/2015 a 30/09/2026

Este arquivo é gerado por `scripts/gerar_artefatos.py`. As correções do estudo de 30/09/2026 estão em [`ERRATA.md`](ERRATA.md).

## 1. Principais indicadores

* **Registros:** 19.056, dos quais 7.645 são notificações (40,1%).
* **Vítimas:** 496 óbitos, 1.147 feridos graves e 10.745 feridos leves.
* **Sem informação de vítimas:** 8.297 registros (43,5%). Isso não significa que ninguém se feriu. Só 615 (3,2%) registram apenas ilesos.
* **Coordenadas:** 17.532 registros (92,0%) ficam em um retângulo aproximado ao redor do município. Esse filtro não equivale ao limite municipal.

## 2. Método e comparabilidade

1. **2015 a 2018:** só há sinistros fatais (31 a 50 por ano).
2. **2019 em diante:** entram sinistros não fatais e notificações. Nos anos completos, o total varia de 2.190 a 2.835 registros.
3. **Notificações:** representam de 11,8% a 60,1% dos registros por ano e nunca trazem veículos. Por isso, o total anual não mede tendência.

Letalidade, perfis de gravidade e modelo usam a **base comparável**: 11.249 sinistros de 2019 em diante, sem notificações. Letalidade é a proporção de sinistros com ao menos um óbito, não o número de mortos dividido por sinistros.

## 3. Quando os registros ocorrem

Os maiores volumes ocorrem às 18h, 19h e 17h. Volume não equivale a risco, pois a base não traz o fluxo de veículos.

Teste de Welch com todos os dias do calendário desde 2019, inclusive os 1,1% sem registro:

* **Dias úteis:** 6,70 registros/dia
* **Fins de semana:** 6,63 registros/dia
* **Diferença:** -0,07 (IC95% -0,36 a 0,22; p = 0,634)

O intervalo inclui zero: os dados não demonstram diferença entre os dois blocos, o que não prova que as médias sejam iguais. Agrupar os dias em dois blocos esconde diferenças: sexta tem 7,75, sábado 7,35 e domingo 5,90, contra 6,43 de segunda a quinta.

A madrugada responde por 14,1% dos sinistros de fim de semana e 4,8% dos de dias úteis. A base não mede alcoolemia nem velocidade, então a causa desse padrão não pode ser afirmada.

## 4. Letalidade por tipo de sinistro (base comparável)

| Tipo | Sinistros | Sinistros com óbito | Óbitos (pessoas) | Feridos graves (pessoas) | Letalidade |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **ATROPELAMENTO** | 722 | 84 | 84 | 106 | **11,63%** |
| **CHOQUE** | 1.167 | 68 | 69 | 133 | **5,83%** |
| **OUTROS** | 2.151 | 58 | 63 | 185 | **2,70%** |
| **COLISAO** | 7.102 | 103 | 109 | 670 | **1,45%** |
| **OUTROS / NAO INFORMADO** | 107 | 0 | 0 | 13 | **0,00%** |

O atropelamento fica acima do choque na base toda (razão 2,00; IC95% 1,47 a 2,71), mas nas vias urbanas os dois não podem ser ordenados com segurança (razão 1,15; IC95% 0,76 a 1,72).

O choque tem 4,0 vezes a letalidade da colisão (IC95% 3,0 a 5,4), mas essa diferença é urbana: 5,9 vezes nas vias urbanas (IC95% 4,1 a 8,7) e 0,9 nas rodovias (IC95% 0,6 a 1,5). A base não informa qual objeto foi atingido.

## 5. Modais

Entre os 10.780 registros com veículo ou pedestre informado, há motocicleta em 64,3% e automóvel em 72,4%. Um mesmo registro pode ter os dois.

Na base comparável, sinistros com moto têm 13,3% de desfecho grave ou fatal, contra 9,9% dos demais, e 2,0% de letalidade, contra 4,0%. A base não liga cada vítima ao seu veículo nem traz frota ou quilômetros rodados, então não mede o risco individual do motociclista.

## 6. Onde ocorrem

As vias urbanas têm 87,7% dos registros e 264 dos 496 óbitos (53%). Estradas e rodovias têm 12,2% dos registros e 200 óbitos (40%). Os demais óbitos não têm tipo de via informado.

A letalidade por sinistro é maior nas rodovias (6,5%) do que nas vias urbanas (1,9%). SP-300, SP-225 e SP-294 somam 175 óbitos (35%). A velocidade não consta na base.

| Vias com mais sinistros | Sinistros | Óbitos | Feridos graves |
| :--- | :---: | :---: | :---: |
| SP 300 | 1.042 | 80 | 172 |
| AVENIDA NACOES UNIDAS | 711 | 21 | 53 |
| AVENIDA DUQUE DE CAXIAS | 375 | 7 | 25 |
| AVENIDA RODRIGUES ALVES | 343 | 9 | 39 |
| SP 225 | 315 | 53 | 66 |
| SP 294 | 227 | 42 | 53 |
| AVENIDA CASTELO BRANCO QUADRA | 218 | 5 | 15 |
| AVENIDA CRUZEIRO DO SUL | 198 | 9 | 11 |
| AVENIDA GETULIO VARGAS | 182 | 4 | 15 |
| AVENIDA NUNO DE ASSIS | 172 | 2 | 15 |

| Vias com mais óbitos | Óbitos | Sinistros | Feridos graves |
| :--- | :---: | :---: | :---: |
| SP 300 | 80 | 1.042 | 172 |
| SP 225 | 53 | 315 | 66 |
| SP 294 | 42 | 227 | 53 |
| AVENIDA NACOES UNIDAS | 21 | 711 | 53 |
| SP 321 | 16 | 105 | 17 |
| RUA MONSENHOR CLARO | 14 | 45 | 3 |
| AVENIDA RODRIGUES ALVES | 9 | 343 | 39 |
| AVENIDA CRUZEIRO DO SUL | 9 | 198 | 11 |
| AVENIDA DUQUE DE CAXIAS | 7 | 375 | 25 |
| AVENIDA CASTELO BRANCO QUADRA | 5 | 218 | 15 |

Os rankings excluem notificações e são contagens brutas, sem fluxo de veículos.

## 7. Modelo exploratório

Regressão logística para estimar se o desfecho foi grave ou fatal (11,8% dos casos). As métricas abaixo vêm de 8.424 sinistros de treino e 2.808 de teste; as razões de chance, do ajuste nos 11.232 sinistros da base comparável.

* **Acurácia:** 88,2%, contra 88,2% de sempre prever a classe mais comum. O modelo não supera a referência de sempre prever a classe mais comum.
* **Acurácia balanceada (limiar de 50%):** 50,7%
* **ROC-AUC:** 0,695 (IC 95%: 0,667 a 0,723)
* **PR-AUC:** 0,242, contra 0,118 do acaso
* **Com limiar no risco médio:** sensibilidade de 53,9% e precisão de 21,7%
* **Validação cruzada (15 rodadas):** ROC-AUC de 0,693 ± 0,010
* **Validação por ano:** treinado só com anos anteriores, ROC-AUC de 0,681 em 2022, 0,716 em 2023, 0,686 em 2024, 0,660 em 2025, 0,694 em 2026 (2026 até 09/2026).

Razões de chance com intervalo de 95%, mantendo as demais variáveis iguais (referência: via urbana, colisão e tarde):

* **Aumentam a chance de desfecho grave ou fatal:** pedestre envolvido: 3,45 (IC 95%: 1,65 a 7,21); rodovia: 3,04 (IC 95%: 2,63 a 3,52); bicicleta envolvida: 2,35 (IC 95%: 1,64 a 3,36); motocicleta envolvida: 2,26 (IC 95%: 1,93 a 2,64); madrugada (0h–6h): 2,13 (IC 95%: 1,72 a 2,64); caminhão ou ônibus envolvido: 1,91 (IC 95%: 1,51 a 2,41); tipo: choque: 1,44 (IC 95%: 1,18 a 1,76); noite (18h–24h): 1,30 (IC 95%: 1,12 a 1,51); fim de semana: 1,27 (IC 95%: 1,12 a 1,46).
* **Reduzem a chance:** manhã (6h–12h): 0,82 (IC 95%: 0,69 a 0,96).

O modelo usa dados conhecidos só depois do sinistro, então não prevê acidentes. As razões de chance são associações nesta base, não causas, e fatores ausentes como velocidade e alcoolemia podem explicar parte delas.

## 8. Hipóteses para a gestão pública

As ações abaixo devem ser validadas com contagem de tráfego, inspeção em campo e dados de velocidade e alcoolemia, que não constam nesta base.

1. **Pedestres:** priorizar a análise dos locais de atropelamento, o tipo com maior letalidade (11,63%).
2. **Rodovias:** revisar com DER e concessionárias os trechos de SP-300, SP-225 e SP-294, que somam 35% dos óbitos.
3. **Vias urbanas:** inspecionar os locais de choque para identificar os objetos atingidos antes de instalar defensas, e avaliar medidas para motociclistas nas vias com mais registros.
4. **Coleta de dados:** obter fluxo de veículos e medições de velocidade, para calcular risco e não apenas volume.

## 9. Limitações

* Notificações quase sempre vêm sem dados de vítimas, e parte pode repetir sinistros já registrados.
* Não há fluxo de veículos, frota, velocidade nem alcoolemia.
* A base não indica em qual veículo cada vítima estava.
* Contagens vazias viram zero, o que pode subestimar envolvidos.
* O último mês pode ser revisado pela fonte, e o último ano é parcial. Óbitos por ano: 2015: 41, 2016: 52, 2017: 44, 2018: 34, 2019: 37, 2020: 41, 2021: 34, 2022: 60, 2023: 37, 2024: 42, 2025: 44, 2026: 30.
