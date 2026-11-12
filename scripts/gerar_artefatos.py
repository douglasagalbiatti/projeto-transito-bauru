"""
Gera gráficos, mapa, relatório e README a partir de data/bauru_limpo.csv.

Os notebooks 03 e 04 são executados antes, com os resultados guardados em output/notebooks.

Gráficos, mapa e notebooks executados não são versionados na main:
'scripts/publicar_artefatos.sh' os publica na branch 'artefatos'.
"""

import argparse
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker
import pandas as pd
import plotly.express as px
import seaborn as sns
from jinja2 import Environment, FileSystemLoader, StrictUndefined

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
from src.indicadores import calcular_indicadores
from src.metricas import (
    CORES_SEVERIDADE,
    ORDEM_SEVERIDADE,
    SEM_INFORMACAO,
    URL_ARTEFATOS,
    base_comparavel,
    br,
    com_modal_informado,
    ranking_vias,
    tabela_letalidade,
)
from src.modelo import NOMES_REFERENCIA, NOMES_VARIAVEIS_MODELO, treinar_modelo

DATA_FILE = os.path.join(BASE_DIR, "data", "bauru_limpo.csv")
GRAFICOS_DIR = os.path.join(BASE_DIR, "output", "graficos")
RELATORIO_MD = os.path.join(BASE_DIR, "output", "relatorios", "relatorio_final_bauru.md")
NOTEBOOKS_DIR = os.path.join(BASE_DIR, "notebooks")
NOTEBOOKS_EXECUTADOS_DIR = os.path.join(BASE_DIR, "output", "notebooks")
NOTEBOOKS = ["03-analise-bauru.ipynb", "04-visualizacoes.ipynb"]
# O GitHub não exibe esta saída, que só deixaria o notebook pesado demais para abrir lá
SAIDA_PLOTLY = "application/vnd.plotly.v1+json"
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
README_MD = os.path.join(BASE_DIR, "README.md")
ORDEM_DIAS = ["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira", "Sábado", "Domingo"]


def salvar(fig, nome):
    fig.tight_layout()
    fig.savefig(os.path.join(GRAFICOS_DIR, nome), dpi=300)
    plt.close(fig)


def grafico_anual(df, ano_parcial):
    resumo = df.groupby("ano").agg(
        sinistros=("tipo_registro", lambda s: int((s != "NOTIFICACAO").sum())),
        notificacoes=("tipo_registro", lambda s: int((s == "NOTIFICACAO").sum())),
        obitos=("obitos", "sum"),
    )
    fig, ax1 = plt.subplots(figsize=(12, 6))
    ax1.bar(resumo.index, resumo["sinistros"], color="#2b5c8f", width=0.6, label="Sinistros (fatais e não fatais)")
    ax1.bar(resumo.index, resumo["notificacoes"], bottom=resumo["sinistros"], color="#adb5bd", width=0.6, label="Notificações")
    ax1.set_xlabel("Ano")
    ax1.set_ylabel("Registros")
    ax1.set_xticks(resumo.index)
    ax1.yaxis.set_major_formatter(lambda v, _: br(v))
    ax2 = ax1.twinx()
    ax2.plot(resumo.index, resumo["obitos"], color="#d9383a", linewidth=3, marker="o", label="Óbitos")
    ax2.set_ylabel("Óbitos")
    ax2.set_ylim(0, resumo["obitos"].max() * 1.3)
    ax2.grid(False)
    for ano, obitos in resumo["obitos"].items():
        ax2.text(ano, obitos + 1.5, str(obitos), ha="center", fontweight="bold", color="#d9383a")
    linhas = ax1.get_legend_handles_labels(), ax2.get_legend_handles_labels()
    ax1.legend(linhas[0][0] + linhas[1][0], linhas[0][1] + linhas[1][1], loc="upper left")
    ax1.set_title(
        f"Registros e óbitos em Bauru/SP, até {pd.to_datetime(df['data_sinistro_dt']).max():%m/%Y}\n"
        "Até 2018 só há sinistros fatais; a proporção de notificações varia por ano"
        + (" e o último ano é parcial" if ano_parcial else ""),
        fontweight="bold",
    )
    salvar(fig, "acidentes_por_ano.png")


def grafico_dia_hora(df):
    fig, eixos = plt.subplots(1, 2, figsize=(14, 5))
    dias = df["dia_da_semana_limpo"].value_counts().reindex(ORDEM_DIAS, fill_value=0)
    eixos[0].bar(dias.index, dias.values, color="#2b5c8f")
    eixos[0].set_title("Registros por dia da semana", fontweight="bold")
    eixos[0].tick_params(axis="x", rotation=30)
    for i, valor in enumerate(dias.values):
        eixos[0].text(i, valor, br(valor), ha="center", va="bottom", fontsize=9)
    horas = df["hora_num"].value_counts().reindex(range(24), fill_value=0)
    eixos[1].bar(horas.index, horas.values, color="#3b82f6")
    eixos[1].set_title("Registros por hora do dia", fontweight="bold")
    eixos[1].set_xlabel("Hora")
    eixos[1].set_xticks(range(0, 24, 2))
    for eixo in eixos:
        eixo.yaxis.set_major_formatter(lambda v, _: br(v))
        eixo.set_ylabel("Registros")
    salvar(fig, "acidentes_dia_e_hora.png")


def grafico_tipos_modais(df):
    letalidade = tabela_letalidade(base_comparavel(df))
    modal = com_modal_informado(df)
    modais = pd.Series({
        "Automóvel": modal["envolve_auto"].sum(),
        "Motocicleta": modal["envolve_moto"].sum(),
        "Pedestre": modal["envolve_pedestre"].sum(),
        "Caminhão/Ônibus": modal["envolve_pesado"].sum(),
        "Bicicleta": modal["envolve_bicicleta"].sum(),
    })
    fig, eixos = plt.subplots(1, 2, figsize=(15, 6))
    eixos[0].bar(letalidade["tipo_sinistro_simplificado"], letalidade["letalidade_pct"], color="#b91c1c")
    eixos[0].set_title("Sinistros com óbito (%) por tipo\nBase comparável: 2019+, sem notificações", fontweight="bold")
    eixos[0].set_ylabel("Letalidade (% dos sinistros)")
    eixos[0].tick_params(axis="x", rotation=20)
    for i, valor in enumerate(letalidade["letalidade_pct"]):
        eixos[0].text(i, valor, f"{br(valor, 2)}%", ha="center", va="bottom", fontweight="bold")
    eixos[1].bar(modais.index, modais.values, color="#0f766e")
    eixos[1].set_title("Presença de cada modal\nRegistros com veículo ou pedestre informado", fontweight="bold")
    eixos[1].set_ylabel("Registros")
    eixos[1].yaxis.set_major_formatter(lambda v, _: br(v))
    eixos[1].tick_params(axis="x", rotation=20)
    for i, valor in enumerate(modais.values):
        eixos[1].text(i, valor, f"{br(valor)}\n({br(valor / len(modal) * 100, 1)}%)", ha="center", va="bottom", fontsize=9)
    eixos[1].margins(y=0.12)
    salvar(fig, "tipos_e_veiculos.png")


def grafico_heatmap(df):
    matriz = df[df["hora_num"].notnull()].pivot_table(
        index="dia_da_semana_limpo", columns="hora_num", values="id_sinistro", aggfunc="count", fill_value=0
    ).reindex(index=ORDEM_DIAS, columns=range(24), fill_value=0)
    fig, eixo = plt.subplots(figsize=(15, 6))
    sns.heatmap(matriz, cmap="YlOrRd", linewidths=0.5, annot=True, fmt="d", cbar_kws={"label": "Registros"}, ax=eixo)
    eixo.set_title("Registros por dia da semana e hora do dia (Bauru/SP)", fontweight="bold")
    eixo.set_xlabel("Hora do dia")
    eixo.set_ylabel("")
    salvar(fig, "heatmap_dia_hora.png")


def grafico_razoes_chance(resultado):
    rc = resultado["razoes_chance"].sort_values("razao_chance")
    nomes = [NOMES_VARIAVEIS_MODELO.get(nome, nome) for nome in rc.index]
    cores = ["#c0392b" if l.ic_inf > 1 else "#2b5c8f" if l.ic_sup < 1 else "#95a5a6" for l in rc.itertuples()]
    fig, eixo = plt.subplots(figsize=(10, 7))
    for y, (l, cor) in enumerate(zip(rc.itertuples(), cores)):
        eixo.errorbar(l.razao_chance, y, xerr=[[l.razao_chance - l.ic_inf], [l.ic_sup - l.razao_chance]], fmt="o", color=cor, capsize=3)
    eixo.axvline(1, color="#555555", linestyle="--", linewidth=1)
    eixo.set_xscale("log")
    eixo.set_yticks(range(len(nomes)), nomes)
    marcas = [m for m in (0.25, 0.5, 1, 2, 4, 8, 16) if rc["ic_inf"].min() / 1.5 <= m <= rc["ic_sup"].max() * 1.5]
    eixo.set_xticks(marcas, [br(m, 2 if m < 0.5 else 1) for m in marcas])
    eixo.xaxis.set_minor_locator(matplotlib.ticker.NullLocator())
    refs = resultado["referencias"]
    eixo.set_title(
        "Razões de chance de desfecho grave ou fatal (regressão logística, IC 95%)\n"
        f"Referência: {NOMES_REFERENCIA[refs['tipo_via_simplificado']]}, {NOMES_REFERENCIA[refs['tipo_sinistro_simplificado']]}, "
        f"{NOMES_REFERENCIA[refs['turno_ajustado']]}; associação, não causa",
        fontweight="bold",
    )
    eixo.set_xlabel("Razão de chance (escala logarítmica)")
    salvar(fig, "razoes_chance_ml.png")


def gerar_mapa(df):
    geo = df[df["geo_valida"]]
    fig = px.scatter_map(
        geo,
        lat="lat",
        lon="lon",
        color="severidade_categoria",
        color_discrete_map=CORES_SEVERIDADE,
        category_orders={"severidade_categoria": ORDEM_SEVERIDADE},
        hover_name="tipo_sinistro_simplificado",
        hover_data={
            "lat": False, "lon": False, "data_sinistro": True, "tipo_registro": True, "tipo_via": True,
            "logradouro": True, "obitos": True, "feridos_graves": True, "envolve_moto": True,
        },
        zoom=11.5,
        center={"lat": -22.3145, "lon": -49.0587},
        map_style="carto-positron",
        title=f"Registros de trânsito em Bauru/SP, até {pd.to_datetime(df['data_sinistro_dt']).max():%m/%Y}",
        height=800,
    )
    fig.update_layout(
        margin=dict(l=0, r=0, t=40, b=0),
        separators=",.",
        legend=dict(title=dict(text="Severidade"), yanchor="top", y=0.98, xanchor="left", x=0.02,
                    bgcolor="rgba(255, 255, 255, 0.9)", bordercolor="#cbd5e1", borderwidth=1),
    )
    fig.write_html(os.path.join(GRAFICOS_DIR, "mapa_acidentes.html"))


def tabela_markdown(linhas, colunas):
    alinhamento = "| :--- |" + " :---: |" * (len(colunas) - 1)
    corpo = "\n".join("| " + " | ".join(linha) + " |" for linha in linhas)
    return f"| {' | '.join(colunas)} |\n{alinhamento}\n{corpo}"


def gerar_relatorio(df, indicadores):
    i = indicadores
    resultado, comparavel, datas = i["modelo"], i["comparavel"], i["datas"]
    teste, por_dia, letalidade, modal = i["teste"], i["por_dia"], i["letalidade"], i["modal"]
    # Grave ou fatal só entre sinistros com vítimas informadas; letalidade em toda a base comparável
    informados = comparavel[comparavel["severidade_categoria"] != SEM_INFORMACAO]
    moto = pd.DataFrame({
        "letal": comparavel.groupby("envolve_moto")["obitos"].apply(lambda s: (s > 0).mean() * 100),
        "grave": informados.groupby("envolve_moto")["severidade_grave_ou_fatal"].mean() * 100,
    })
    horas = df["hora_num"].value_counts().head(3).index.astype(int)
    madrugada = comparavel.groupby("is_fim_de_semana")["turno_ajustado"].apply(lambda s: (s == "MADRUGADA").mean() * 100)
    ultimo_completo = datas.max().year - 1 if i["ano_parcial"] else datas.max().year
    completos = df[(df["ano"] >= 2019) & (df["ano"] <= ultimo_completo)]["ano"].value_counts()
    obitos_ano = df.groupby("ano")["obitos"].sum()
    fatais_ate_2018 = df[df["ano"] <= 2018].groupby("ano")["id_sinistro"].count()
    aviso_modelo = (
        "O modelo supera a referência de sempre prever a classe mais comum."
        if i["supera_referencia"]
        else "O modelo não supera a referência de sempre prever a classe mais comum."
    )
    cv = resultado["validacao_cruzada"]
    temporal = resultado["temporal"]
    frase_temporal = (
        "não há anos suficientes."
        if temporal.empty
        else "treinado só com anos anteriores, ROC-AUC de "
        + ", ".join(f"{br(l.auc, 3)} em {l.ano}" for l in temporal.itertuples())
        + (f" ({temporal['ano'].max()} até {datas.max():%m/%Y})." if i["ano_parcial"] else ".")
    )
    rc = resultado["razoes_chance"]

    def _lista_rc(linhas):
        return "; ".join(
            f"{NOMES_VARIAVEIS_MODELO.get(nome, nome).lower()}: {br(l.razao_chance, 2)} (IC 95%: {br(l.ic_inf, 2)} a {br(l.ic_sup, 2)})"
            for nome, l in linhas.iterrows()
        ) or "nenhuma"

    aumentam = _lista_rc(rc[rc["ic_inf"] > 1])
    reduzem = _lista_rc(rc[rc["ic_sup"] < 1].sort_values("razao_chance"))
    refs = resultado["referencias"]
    referencias_modelo = (
        f"{NOMES_REFERENCIA[refs['tipo_via_simplificado']]}, {NOMES_REFERENCIA[refs['tipo_sinistro_simplificado']]} "
        f"e {NOMES_REFERENCIA[refs['turno_ajustado']]}"
    )
    vias = ranking_vias(df[df["tipo_registro"] != "NOTIFICACAO"])
    vias_obitos = ranking_vias(df[df["tipo_registro"] != "NOTIFICACAO"], por="obitos")
    frase_letalidade_via = (
        f"A letalidade por sinistro é maior nas rodovias ({br(i['letal_rodovia'], 1)}%) do que nas vias urbanas ({br(i['letal_urbana'], 1)}%)."
        if i["rodovia_mais_letal"]
        else f"A letalidade por sinistro é de {br(i['letal_rodovia'], 1)}% nas rodovias e {br(i['letal_urbana'], 1)}% nas vias urbanas."
    )
    taxa_atropelamento = br(i["letalidade_tipo"]["ATROPELAMENTO"], 2)

    texto = f"""# Relatório técnico: segurança viária em Bauru/SP

**Município:** Bauru/SP (`IBGE 3506003`)
**Fonte:** Infosiga SP
**Período dos dados:** {i['data_inicio']} a {i['data_fim']}

Este arquivo é gerado por `scripts/gerar_artefatos.py`. As correções do estudo de 30/09/2026 estão em [`ERRATA.md`](ERRATA.md).

## 1. Principais indicadores

* **Registros:** {br(i['total'])}, dos quais {br(i['notificacoes'])} são notificações ({br(i['notificacoes_pct'], 1)}%).
* **Vítimas:** {br(i['obitos'])} óbitos, {br(i['feridos_graves'])} feridos graves e {br(i['feridos_leves'])} feridos leves.
* **Sem informação de vítimas:** {br(i['sem_informacao'])} registros ({br(i['sem_informacao_pct'], 1)}%). Isso não significa que ninguém se feriu. Só {br(i['sem_feridos'])} ({br(i['sem_feridos_pct'], 1)}%) registram apenas ilesos.
* **Coordenadas:** {br(df['geo_valida'].sum())} registros ({br(df['geo_valida'].mean() * 100, 1)}%) ficam em um retângulo aproximado ao redor do município. Esse filtro não equivale ao limite municipal.

## 2. Método e comparabilidade

1. **2015 a 2018:** só há sinistros fatais ({fatais_ate_2018.min()} a {fatais_ate_2018.max()} por ano).
2. **2019 em diante:** entram sinistros não fatais e notificações. Nos anos completos, o total varia de {br(completos.min())} a {br(completos.max())} registros.
3. **Notificações:** representam de {br(i['notif_pct_min'], 1)}% a {br(i['notif_pct_max'], 1)}% dos registros por ano e {i['frase_notificacoes_veiculos']}. Por isso, o total anual não mede tendência.

Letalidade, perfis de gravidade e modelo usam a **base comparável**: {br(len(comparavel))} sinistros de 2019 em diante, sem notificações. Letalidade é a proporção de sinistros com ao menos um óbito, não o número de mortos dividido por sinistros.

## 3. Quando os registros ocorrem

Os maiores volumes ocorrem às {horas[0]}h, {horas[1]}h e {horas[2]}h. Volume não equivale a risco, pois a base não traz o fluxo de veículos.

Teste de Welch com todos os dias do calendário desde 2019, inclusive os {br(teste['dias_sem_registro_pct'], 1)}% sem registro:

* **Dias úteis:** {br(teste['media_uteis'], 2)} registros/dia
* **Fins de semana:** {br(teste['media_fds'], 2)} registros/dia
* **Diferença:** {br(teste['diferenca'], 2)} (IC95% {br(teste['ic95'][0], 2)} a {br(teste['ic95'][1], 2)}; p = {br(teste['p_welch'], 3)})

{i['conclusao_dias']} Agrupar os dias em dois blocos esconde diferenças: sexta tem {br(por_dia[4], 2)}, sábado {br(por_dia[5], 2)} e domingo {br(por_dia[6], 2)}, contra {br(por_dia[[0, 1, 2, 3]].mean(), 2)} de segunda a quinta.

A madrugada responde por {br(madrugada[1], 1)}% dos sinistros de fim de semana e {br(madrugada[0], 1)}% dos de dias úteis. A base não mede alcoolemia nem velocidade, então a causa desse padrão não pode ser afirmada.

## 4. Letalidade por tipo de sinistro (base comparável)

{tabela_markdown(
    [[f"**{l.tipo_sinistro_simplificado}**", br(l.sinistros), br(l.sinistros_fatais), br(l.obitos), br(l.feridos_graves), f"**{br(l.letalidade_pct, 2)}%**"] for l in letalidade.itertuples()],
    ["Tipo", "Sinistros", "Sinistros com óbito", "Óbitos (pessoas)", "Feridos graves (pessoas)", "Letalidade"],
)}

{i['frase_atropelamento']}

{i['frase_choque']} A base não informa qual objeto foi atingido.

## 5. Modais

Entre os {br(len(modal))} registros com veículo ou pedestre informado, há motocicleta em {br(modal['envolve_moto'].mean() * 100, 1)}% e automóvel em {br(modal['envolve_auto'].mean() * 100, 1)}%. Um mesmo registro pode ter os dois.

Entre os sinistros da base comparável com vítimas informadas, os com moto têm {br(moto.loc[1, 'grave'], 1)}% de desfecho grave ou fatal, contra {br(moto.loc[0, 'grave'], 1)}% dos demais. Em toda a base comparável, têm {br(moto.loc[1, 'letal'], 1)}% de letalidade, contra {br(moto.loc[0, 'letal'], 1)}%. A base não liga cada vítima ao seu veículo nem traz frota ou quilômetros rodados, então não mede o risco individual do motociclista.

## 6. Onde ocorrem

As vias urbanas têm {br(i['registros_via']['VIAS URBANAS'], 1)}% dos registros e {br(i['obitos_via']['VIAS URBANAS'])} dos {br(i['obitos'])} óbitos ({br(i['obitos_urbanas_pct'], 0)}%). Estradas e rodovias têm {br(i['registros_via']['ESTRADAS E RODOVIAS'], 1)}% dos registros e {br(i['obitos_via']['ESTRADAS E RODOVIAS'])} óbitos ({br(i['obitos_rodovias_pct'], 0)}%). Os demais óbitos não têm tipo de via informado.

{frase_letalidade_via} SP-300, SP-225 e SP-294 somam {br(i['obitos_principais'])} óbitos ({br(i['obitos_principais_pct'], 0)}%). A velocidade não consta na base.

{tabela_markdown(
    [[l.logradouro, br(l.sinistros), br(l.obitos), br(l.feridos_graves)] for l in vias.itertuples()],
    ["Vias com mais sinistros", "Sinistros", "Óbitos", "Feridos graves"],
)}

{tabela_markdown(
    [[l.logradouro, br(l.obitos), br(l.sinistros), br(l.feridos_graves)] for l in vias_obitos.itertuples()],
    ["Vias com mais óbitos", "Óbitos", "Sinistros", "Feridos graves"],
)}

Os rankings excluem notificações e são contagens brutas, sem fluxo de veículos.

## 7. Modelo exploratório

Regressão logística para estimar se o desfecho foi grave ou fatal ({br(resultado['prevalencia'] * 100, 1)}% dos casos). As métricas abaixo vêm de {br(resultado['n_treino'])} sinistros de treino e {br(resultado['n_teste'])} de teste; as razões de chance, do ajuste nos {br(resultado['n_total'])} sinistros da base comparável com vítimas informadas. Os sinistros sem informação de vítimas ficam de fora, porque não se sabe se foram graves.

* **Acurácia:** {br(resultado['acuracia'] * 100, 1)}%, contra {br(resultado['referencia'] * 100, 1)}% de sempre prever a classe mais comum. {aviso_modelo}
* **Acurácia balanceada (limiar de 50%):** {br(resultado['acuracia_balanceada'] * 100, 1)}%
* **ROC-AUC:** {br(resultado['auc'], 3)} (IC 95%: {br(resultado['auc_ic'][0], 3)} a {br(resultado['auc_ic'][1], 3)})
* **PR-AUC:** {br(resultado['pr_auc'], 3)}, contra {br(resultado['prevalencia'], 3)} do acaso
* **Com limiar no risco médio:** sensibilidade de {br(resultado['teste']['sensibilidade'] * 100, 1)}% e precisão de {br(resultado['teste']['precisao'] * 100, 1)}%
* **Validação cruzada ({cv['rodadas'].iloc[0]} rodadas):** ROC-AUC de {br(cv.loc['auc', 'media'], 3)} ± {br(cv.loc['auc', 'desvio'], 3)}
* **Validação por ano:** {frase_temporal}

Razões de chance com intervalo de 95%, mantendo as demais variáveis iguais (referência: {referencias_modelo}):

* **Aumentam a chance de desfecho grave ou fatal:** {aumentam}.
* **Reduzem a chance:** {reduzem}.

O modelo usa dados conhecidos só depois do sinistro, então não prevê acidentes. As razões de chance são associações nesta base, não causas, e fatores ausentes como velocidade e alcoolemia podem explicar parte delas.

## 8. Hipóteses para a gestão pública

As ações abaixo devem ser validadas com contagem de tráfego, inspeção em campo e dados de velocidade e alcoolemia, que não constam nesta base.

1. **Pedestres:** priorizar a análise dos locais de atropelamento, {'o tipo com maior letalidade' if i['atropelamento_mais_letal'] else 'um tipo de alta letalidade'} ({taxa_atropelamento}%).
2. **Rodovias:** revisar com DER e concessionárias os trechos de SP-300, SP-225 e SP-294, que somam {br(i['obitos_principais_pct'], 0)}% dos óbitos.
3. **Vias urbanas:** inspecionar os locais de choque para identificar os objetos atingidos antes de instalar defensas, e avaliar medidas para motociclistas nas vias com mais registros.
4. **Coleta de dados:** obter fluxo de veículos e medições de velocidade, para calcular risco e não apenas volume.

## 9. Limitações

* Notificações quase sempre vêm sem dados de vítimas, e parte pode repetir sinistros já registrados.
* Não há fluxo de veículos, frota, velocidade nem alcoolemia.
* A base não indica em qual veículo cada vítima estava.
* Contagens vazias viram zero, o que pode subestimar envolvidos.
* O último mês pode ser revisado pela fonte{', e o último ano é parcial' if i['ano_parcial'] else ''}. Óbitos por ano: {", ".join(f"{ano}: {valor}" for ano, valor in obitos_ano.items())}.
"""
    with open(RELATORIO_MD, "w", encoding="utf-8") as arquivo:
        arquivo.write(texto)


def remover_saidas_plotly(notebook):
    """Retira do notebook executado as saídas que o GitHub não consegue exibir."""
    for celula in notebook.cells:
        if celula.cell_type == "code":
            celula.outputs = [saida for saida in celula.outputs if SAIDA_PLOTLY not in saida.get("data", {})]
    return notebook


def executar_notebooks():
    """Executa os notebooks e guarda as cópias com resultados, sem alterar os originais."""
    import nbformat
    from nbconvert.preprocessors import ExecutePreprocessor

    os.makedirs(NOTEBOOKS_EXECUTADOS_DIR, exist_ok=True)
    for nome in NOTEBOOKS:
        notebook = nbformat.read(os.path.join(NOTEBOOKS_DIR, nome), as_version=4)
        ExecutePreprocessor(timeout=600, kernel_name="python3").preprocess(notebook, {"metadata": {"path": NOTEBOOKS_DIR}})
        nbformat.write(remover_saidas_plotly(notebook), os.path.join(NOTEBOOKS_EXECUTADOS_DIR, nome))


def gerar_readme(indicadores, destino=README_MD):
    """Preenche o modelo do README com os indicadores da base."""
    ambiente = Environment(
        loader=FileSystemLoader(TEMPLATES_DIR),
        undefined=StrictUndefined,
        keep_trailing_newline=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    ambiente.filters["br"] = br
    conteudo = ambiente.get_template("README.md.j2").render(i=indicadores, url=URL_ARTEFATOS)
    with open(destino, "w", encoding="utf-8") as arquivo:
        arquivo.write(conteudo)
    return conteudo


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sem-notebooks", action="store_true", help="Não executa os notebooks.")
    args = parser.parse_args()
    # Antes do restante, pois o notebook 04 também grava o mapa, e o publicado é o do gerador
    if not args.sem_notebooks:
        executar_notebooks()
    df = pd.read_csv(DATA_FILE, sep=";", encoding="utf-8", low_memory=False)
    os.makedirs(GRAFICOS_DIR, exist_ok=True)
    resultado = treinar_modelo(df)
    indicadores = calcular_indicadores(df, resultado)
    grafico_anual(df, indicadores["ano_parcial"])
    grafico_dia_hora(df)
    grafico_tipos_modais(df)
    grafico_heatmap(df)
    grafico_razoes_chance(resultado)
    gerar_mapa(df)
    gerar_relatorio(df, indicadores)
    gerar_readme(indicadores)
    print(f"Gráficos, mapa, relatório e README atualizados com dados até {indicadores['data_fim']}.")


if __name__ == "__main__":
    main()
