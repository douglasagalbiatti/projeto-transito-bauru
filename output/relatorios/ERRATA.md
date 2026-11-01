# Errata do estudo de 30/09/2026

Vale para `relatorio_bauru.pdf`, mantido como registro histórico, e para as versões anteriores do relatório, do README e do painel. Os valores corrigidos usam os dados até 30/09/2026.

| Afirmação original | Correção |
| :--- | :--- |
| Os dados cobrem de março de 2015 a agosto de 2026 | O primeiro registro é de 13/01/2015 |
| 2019 em diante inclui acidentes "sem vítimas" | 43,5% dos registros não informam vítimas, o que não significa que ninguém se feriu; só 3,2% registram apenas ilesos |
| Desde 2019, o volume fica entre 2.200 e 2.800 por ano, apresentado como série de sinistros | Os anos completos vão de 2.190 a 2.835 registros, e as notificações vão de 11,8% a 60,1% dos registros por ano, então o total anual não mede tendência desde 2019 |
| Letalidade de 9,09% em atropelamentos, 7,45% em choques e 2,36% em colisões | O cálculo dividia pessoas mortas por sinistros e misturava os anos só com casos fatais e as notificações. Na base comparável: 11,63%, 5,83% e 1,45% dos sinistros têm óbito |
| Choque é de 3 a 4 vezes mais letal que colisão | A razão de 4,0 vem das vias urbanas (5,9); nas rodovias, as taxas são próximas (0,9; IC95% 0,6 a 1,5) |
| Choque "contra obstáculo fixo" (postes, árvores, defensas) | A base não informa qual objeto foi atingido |
| Média idêntica de 6,98 e 7,07 acidentes/dia, em dias úteis e fins de semana (p = 0,55) | 6,70 e 6,63 registros/dia, contando os dias sem registro (p = 0,634). O resultado não demonstra diferença nem prova igualdade; sexta e sábado ficam acima dos demais dias |
| Picos às 12h e às 18h, e entre 11h e 13h | Os maiores volumes são às 18h, 19h e 17h, com um pico matinal às 7h |
| Madrugadas de fim de semana associadas a álcool e alta velocidade | Há mais registros nesse período, mas a base não mede alcoolemia nem velocidade |
| Motos em 36,2% dos sinistros | O denominador incluía notificações, que nunca trazem veículos. Entre registros com modal informado, são 64,3% (automóveis: 72,4%) |
| Motos são menos numerosas na frota, o que indica risco desproporcional | A base não traz frota nem quilômetros rodados, e o número de frota não tinha fonte |
| A moto é o principal preditor e o motociclista é o mais vulnerável | A importância de 0,246 refletia em boa parte as notificações, sem veículo e quase sempre sem desfecho grave. A base não liga cada vítima ao seu veículo. Sinistros com moto têm 13,3% de desfecho grave ou fatal, contra 9,9%, e 2,0% de letalidade, contra 4,0% |
| Modelo com ROC-AUC de 0,80 e bom para apoiar decisões | Na base comparável, o ROC-AUC é 0,683, e a acurácia de 88,4% é praticamente a de sempre prever a classe mais comum (88,2%) |
| O simulador estima a probabilidade de lesão grave ou morte | Com `class_weight='balanced'`, os valores superestimavam essa probabilidade; a média era de 33%, contra 7,9% observados |
| As rodovias concentram as mortes em alta velocidade | 53% dos óbitos ocorrem em vias urbanas e 40% em estradas e rodovias, que têm maior letalidade por sinistro (6,5%, contra 1,9%). A velocidade não consta na base |
| Registros "dentro dos limites territoriais" | A validação usa um retângulo aproximado ao redor do município |
| Feridos graves "hospitalizados" | A base não informa internação |
| Recomendações apresentadas como conclusões, como motofaixas, defensas e radares | São hipóteses a validar em campo, pois a base não mede fluxo, velocidade nem objeto atingido |
