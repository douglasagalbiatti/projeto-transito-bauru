"""Indicadores e conclusões calculados da base, usados no README e no relatório."""

import pandas as pd

from src.metricas import (
    ANO_INICIO_COMPARAVEL,
    COLUNAS_MODAL,
    SEM_FERIDOS,
    SEM_INFORMACAO,
    base_comparavel,
    br,
    com_modal_informado,
    comparar_dias,
    normalizar_via,
    ranking_vias,
    razao_letalidade,
    tabela_letalidade,
)

DIAS_SEMANA = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"]
URBANA, RODOVIA = "VIAS URBANAS", "ESTRADAS E RODOVIAS"
RODOVIAS_PRINCIPAIS = ["SP 300", "SP 225", "SP 294"]
COLUNAS_VEICULO = [coluna for coluna in COLUNAS_MODAL if coluna != "qtd_pedestre"]
# Vantagem mínima de acurácia para dizer que o modelo supera a referência
MARGEM_REFERENCIA = 0.005


def _ic(razao: tuple) -> str:
    return f"IC95% {br(razao[1], 2)} a {br(razao[2], 2)}"


def _ic_1(razao: tuple) -> str:
    return f"IC95% {br(razao[1], 1)} a {br(razao[2], 1)}"


def _frase_atropelamento(geral: tuple, urbano: tuple) -> str:
    """Só ordena atropelamento e choque quando o intervalo da razão exclui 1."""
    detalhe = f"(razão {br(geral[0], 2)}; {_ic(geral)})"
    if geral[1] > 1:
        inicio = f"O atropelamento fica acima do choque na base toda {detalhe}"
    elif geral[2] < 1:
        inicio = f"O atropelamento fica abaixo do choque na base toda {detalhe}"
    else:
        inicio = f"Na base toda, atropelamento e choque não podem ser ordenados com segurança {detalhe}"
    detalhe_urbano = f"(razão {br(urbano[0], 2)}; {_ic(urbano)})"
    if urbano[1] > 1:
        return f"{inicio}. Nas vias urbanas, o atropelamento fica acima do choque {detalhe_urbano}."
    if urbano[2] < 1:
        return f"{inicio}. Nas vias urbanas, o atropelamento fica abaixo do choque {detalhe_urbano}."
    return f"{inicio}, mas nas vias urbanas os dois não podem ser ordenados com segurança {detalhe_urbano}."


def frase_notificacoes_veiculos(sem_veiculo: bool) -> str:
    return "nunca trazem veículos" if sem_veiculo else "raramente trazem veículos"


def frase_atropelamento_gestao(mais_letal: bool, taxa: float) -> str:
    """Só chama o atropelamento de tipo mais letal enquanto os dados sustentam isso."""
    inicio = "O tipo tem a maior letalidade da base comparável" if mais_letal else "O tipo tem letalidade relevante na base comparável"
    return f"{inicio} ({br(taxa, 2)}% dos sinistros)."


def frase_choque_urbano(razao: tuple) -> str:
    """Só afirma que o choque é mais letal se o intervalo da razão ficar acima de 1."""
    if razao[1] > 1:
        return f"Nas vias urbanas, o choque tem {br(razao[0], 1)} vezes a letalidade da colisão."
    return f"Nas vias urbanas, os dados não demonstram que o choque seja mais letal que a colisão (razão {br(razao[0], 1)}; {_ic_1(razao)})."


def calcular_indicadores(df: pd.DataFrame, resultado: dict) -> dict:
    """Calcula os números e as condições que sustentam os textos dos documentos."""
    datas = pd.to_datetime(df["data_sinistro_dt"])
    fim = datas.max()
    notificacao = df["tipo_registro"] == "NOTIFICACAO"
    comparavel = base_comparavel(df)
    recente = df[df["ano"] >= ANO_INICIO_COMPARAVEL]
    total_obitos = df["obitos"].sum()
    severidade = df["severidade_categoria"].value_counts()

    # O ano do último registro só está completo se os dados chegam a 31/12
    ano_parcial = (fim + pd.Timedelta(days=1)).year == fim.year
    pct_notif = recente.groupby("ano")["tipo_registro"].apply(lambda s: (s == "NOTIFICACAO").mean() * 100)
    teste = comparar_dias(recente)
    teste["significativo"] = teste["p_welch"] < 0.05
    por_dia = teste["media_por_dia"]
    destaque = por_dia.nlargest(2).sort_index()

    letalidade = tabela_letalidade(comparavel)
    taxa = letalidade.set_index("tipo_sinistro_simplificado")["letalidade_pct"]
    urbano = comparavel[comparavel["tipo_via"] == URBANA]
    rodovia = comparavel[comparavel["tipo_via"] == RODOVIA]
    choque_colisao = razao_letalidade(comparavel, "CHOQUE", "COLISAO")
    choque_urbano = razao_letalidade(urbano, "CHOQUE", "COLISAO")
    choque_rodovia = razao_letalidade(rodovia, "CHOQUE", "COLISAO")
    atrop_choque = razao_letalidade(comparavel, "ATROPELAMENTO", "CHOQUE")
    atrop_choque_urbano = razao_letalidade(urbano, "ATROPELAMENTO", "CHOQUE")
    choque_so_urbano = choque_urbano[1] > 1 and choque_rodovia[1] <= 1

    obitos_via = df.groupby("tipo_via")["obitos"].sum()
    registros_via = df["tipo_via"].value_counts(normalize=True) * 100
    letal_via = comparavel.groupby("tipo_via")["obitos"].apply(lambda s: (s > 0).mean() * 100)
    obitos_rodovias = df[normalizar_via(df["logradouro"]).isin(RODOVIAS_PRINCIPAIS)]["obitos"].sum()
    modal = com_modal_informado(df)
    motos_urbanas = urbano[urbano["envolve_moto"] == 1]

    supera_referencia = resultado["acuracia"] > resultado["referencia"] + MARGEM_REFERENCIA
    faixa = f"{br(choque_urbano[0], 1)} vezes nas vias urbanas ({_ic_1(choque_urbano)}) e {br(choque_rodovia[0], 1)} nas rodovias ({_ic_1(choque_rodovia)})"
    return {
        "data_inicio": f"{datas.min():%d/%m/%Y}",
        "data_fim": f"{fim:%d/%m/%Y}",
        "datas": datas,
        "ano_parcial": ano_parcial,
        "total": len(df),
        "notificacoes": int(notificacao.sum()),
        "notificacoes_pct": notificacao.mean() * 100,
        "notificacoes_sem_veiculo": df.loc[notificacao, COLUNAS_VEICULO].sum().sum() == 0,
        "frase_notificacoes_veiculos": frase_notificacoes_veiculos(df.loc[notificacao, COLUNAS_VEICULO].sum().sum() == 0),
        "obitos": int(total_obitos),
        "feridos_graves": int(df["feridos_graves"].sum()),
        "feridos_leves": int(df["feridos_leves"].sum()),
        "sem_informacao": int(severidade.get(SEM_INFORMACAO, 0)),
        "sem_informacao_pct": severidade.get(SEM_INFORMACAO, 0) / len(df) * 100,
        "sem_feridos": int(severidade.get(SEM_FERIDOS, 0)),
        "sem_feridos_pct": severidade.get(SEM_FERIDOS, 0) / len(df) * 100,
        "notif_pct_min": pct_notif.min(),
        "notif_pct_max": pct_notif.max(),
        "comparavel": comparavel,
        "letalidade": letalidade,
        "letalidade_tipo": taxa.to_dict(),
        "atropelamento_mais_letal": taxa.idxmax() == "ATROPELAMENTO",
        "frase_atropelamento_gestao": frase_atropelamento_gestao(taxa.idxmax() == "ATROPELAMENTO", taxa["ATROPELAMENTO"]),
        "frase_choque_urbano": frase_choque_urbano(choque_urbano),
        "via_motos_urbana": ranking_vias(motos_urbanas, n=1)["logradouro"].iloc[0],
        "choque_colisao": choque_colisao,
        "choque_so_urbano": choque_so_urbano,
        "frase_atropelamento": _frase_atropelamento(atrop_choque, atrop_choque_urbano),
        "frase_choque": (
            f"O choque tem {br(choque_colisao[0], 1)} vezes a letalidade da colisão ({_ic_1(choque_colisao)}), "
            + (f"mas essa diferença é urbana: {faixa}." if choque_so_urbano else f"com {faixa}.")
        ),
        "frase_choque_resumo": (
            ("A diferença entre choque e colisão é urbana: " if choque_so_urbano else "A razão de letalidade entre choque e colisão é de ")
            + f"{br(choque_urbano[0], 1)} vezes nas vias urbanas e {br(choque_rodovia[0], 1)} nas rodovias."
        ),
        "teste": teste,
        "por_dia": por_dia,
        "conclusao_dias": (
            "O intervalo exclui zero, o que indica diferença entre os dois blocos."
            if teste["significativo"]
            else "O intervalo inclui zero: os dados não demonstram diferença entre os dois blocos, o que não prova que as médias sejam iguais."
        ),
        "dias_destaque": [{"nome": DIAS_SEMANA[d], "media": v} for d, v in destaque.items()],
        "registros_via": registros_via,
        "obitos_via": obitos_via,
        "obitos_urbanas_pct": obitos_via[URBANA] / total_obitos * 100,
        "obitos_rodovias_pct": obitos_via[RODOVIA] / total_obitos * 100,
        "letal_urbana": letal_via[URBANA],
        "letal_rodovia": letal_via[RODOVIA],
        "rodovia_mais_letal": letal_via[RODOVIA] > letal_via[URBANA],
        "obitos_principais": int(obitos_rodovias),
        "obitos_principais_pct": obitos_rodovias / total_obitos * 100,
        "modal": modal,
        "modal_auto_pct": modal["envolve_auto"].mean() * 100,
        "modal_moto_pct": modal["envolve_moto"].mean() * 100,
        "modelo": resultado,
        "acuracia_pct": resultado["acuracia"] * 100,
        "referencia_pct": resultado["referencia"] * 100,
        "supera_referencia": supera_referencia,
    }
