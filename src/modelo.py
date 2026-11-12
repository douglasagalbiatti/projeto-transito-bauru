"""Modelo exploratório de gravidade, compartilhado por relatório, notebooks e dashboard."""

import numpy as np
import pandas as pd
from scipy.stats import norm
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    balanced_accuracy_score,
    brier_score_loss,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import RepeatedStratifiedKFold, train_test_split

from src.metricas import base_comparavel

FEATURES_NUMERICAS = [
    "envolve_moto", "envolve_auto", "envolve_pedestre", "envolve_bicicleta", "envolve_pesado",
    "is_fim_de_semana",
]
# Variáveis categóricas: (coluna, prefixo, categoria de referência). A referência é a categoria
# mais comum, para que cada razão de chance compare com a situação mais frequente.
CATEGORICAS = [
    ("tipo_via_simplificado", "via", "VIA URBANA"),
    ("tipo_sinistro_simplificado", "tipo", "COLISAO"),
    ("turno_ajustado", "turno", "TARDE"),
]
NOMES_VARIAVEIS_MODELO = {
    "envolve_moto": "Motocicleta envolvida",
    "envolve_auto": "Automóvel envolvido",
    "envolve_pedestre": "Pedestre envolvido",
    "envolve_bicicleta": "Bicicleta envolvida",
    "envolve_pesado": "Caminhão ou ônibus envolvido",
    "is_fim_de_semana": "Fim de semana",
    "via_VIA URBANA": "Via urbana",
    "via_RODOVIA / ESTRADA": "Rodovia",
    "tipo_ATROPELAMENTO": "Tipo: atropelamento",
    "tipo_CHOQUE": "Tipo: choque",
    "tipo_COLISAO": "Tipo: colisão",
    "tipo_OUTROS": "Tipo: outros",
    "tipo_OUTROS / NAO INFORMADO": "Tipo: não informado",
    "turno_MADRUGADA": "Madrugada (0h–6h)",
    "turno_MANHA": "Manhã (6h–12h)",
    "turno_TARDE": "Tarde (12h–18h)",
    "turno_NOITE": "Noite (18h–24h)",
}
NOMES_REFERENCIA = {
    "VIA URBANA": "via urbana",
    "RODOVIA / ESTRADA": "rodovia",
    "COLISAO": "colisão",
    "CHOQUE": "choque",
    "ATROPELAMENTO": "atropelamento",
    "OUTROS": "outros tipos",
    "TARDE": "tarde",
    "MANHA": "manhã",
    "NOITE": "noite",
    "MADRUGADA": "madrugada",
}
SEMENTE = 42
DOBRAS_CV = 5
REPETICOES_CV = 3
REAMOSTRAGENS_BOOTSTRAP = 1000
ANOS_MINIMOS_TREINO = 3

# Métricas mostradas na validação cruzada e na validação por ano, na ordem de exibição
METRICAS_VALIDACAO = ["auc", "pr_auc", "brier_skill", "sensibilidade", "precisao", "acuracia_balanceada"]


def referencias(df: pd.DataFrame) -> dict:
    """Categoria de referência de cada variável: a preferida, ou a mais comum se ela não estiver nos dados."""
    return {
        coluna: preferida if (df[coluna] == preferida).any() else df[coluna].mode().iloc[0]
        for coluna, _, preferida in CATEGORICAS
    }


def montar_features(df: pd.DataFrame, refs: dict = None) -> pd.DataFrame:
    """Indicadores 0/1: veículos, fim de semana e uma coluna por categoria, exceto a de referência."""
    refs = refs or referencias(df)
    partes = [df[FEATURES_NUMERICAS]]
    for coluna, prefixo, _ in CATEGORICAS:
        dummies = pd.get_dummies(df[coluna], prefix=prefixo)
        partes.append(dummies.drop(columns=f"{prefixo}_{refs[coluna]}", errors="ignore"))
    return pd.concat(partes, axis=1).astype(float)


def novo_classificador() -> LogisticRegression:
    # Sem regularização (C infinito), para que os coeficientes e seus intervalos sejam os da regressão clássica
    return LogisticRegression(C=np.inf, max_iter=5000)


def razoes_de_chance(clf: LogisticRegression, X: pd.DataFrame) -> pd.DataFrame:
    """
    Razão de chance de cada variável com intervalo de Wald de 95% e valor-p.

    A covariância vem da inversa da matriz de informação de Fisher (X' W X), com W = p (1 - p).
    """
    Xd = np.column_stack([np.ones(len(X)), X.to_numpy()])
    p = clf.predict_proba(X)[:, 1]
    informacao = Xd.T @ (Xd * (p * (1 - p))[:, None])
    erro_padrao = np.sqrt(np.diag(np.linalg.pinv(informacao)))[1:]
    coef = clf.coef_[0]
    z = coef / erro_padrao
    return pd.DataFrame({
        "razao_chance": np.exp(coef),
        "ic_inf": np.exp(coef - 1.96 * erro_padrao),
        "ic_sup": np.exp(coef + 1.96 * erro_padrao),
        "p_valor": 2 * norm.sf(np.abs(z)),
        "n_casos": X.sum().astype(int).to_numpy(),
    }, index=X.columns).sort_values("razao_chance", ascending=False)


def prever_probabilidade(resultado: dict, casos: pd.DataFrame) -> np.ndarray:
    """Probabilidade estimada para casos descritos pelas colunas originais da base (usada no simulador)."""
    X = montar_features(casos, resultado["referencias"]).reindex(columns=resultado["features"], fill_value=0.0)
    return resultado["modelo"].predict_proba(X)[:, 1]


def metricas_classe_rara(y_real, prob, prevalencia_treino: float) -> dict:
    """
    Métricas adequadas a uma classe rara.

    O limiar de classificação é a prevalência do treino: um sinistro é marcado como grave
    quando o modelo estima risco acima da média, em vez do 0,5 padrão, que quase nunca é atingido.
    O Brier skill compara o erro das probabilidades com o de sempre prever a prevalência do treino
    (0 = igual à referência, positivo = melhor).
    """
    y_real = np.asarray(y_real)
    prob = np.asarray(prob)
    pred = (prob >= prevalencia_treino).astype(int)
    brier = brier_score_loss(y_real, prob)
    brier_ref = brier_score_loss(y_real, np.full(len(y_real), prevalencia_treino))
    return {
        "auc": roc_auc_score(y_real, prob),
        "pr_auc": average_precision_score(y_real, prob),
        "brier": brier,
        "brier_ref": brier_ref,
        "brier_skill": 1 - brier / brier_ref,
        "sensibilidade": recall_score(y_real, pred, zero_division=0),
        "precisao": precision_score(y_real, pred, zero_division=0),
        "acuracia_balanceada": balanced_accuracy_score(y_real, pred),
        "limiar": prevalencia_treino,
    }


def intervalo_bootstrap(y_real, prob, metrica, n: int = REAMOSTRAGENS_BOOTSTRAP) -> tuple:
    """Intervalo de 95% de uma métrica no teste, reamostrando os sinistros de teste com reposição."""
    y_real, prob = np.asarray(y_real), np.asarray(prob)
    rng = np.random.default_rng(SEMENTE)
    valores = []
    for _ in range(n):
        idx = rng.integers(0, len(y_real), len(y_real))
        if y_real[idx].min() == y_real[idx].max():
            continue
        valores.append(metrica(y_real[idx], prob[idx]))
    return tuple(np.percentile(valores, [2.5, 97.5]))


def validacao_cruzada(X: pd.DataFrame, y: pd.Series) -> pd.DataFrame:
    """Validação cruzada estratificada repetida: média e desvio padrão de cada métrica entre as rodadas."""
    divisor = RepeatedStratifiedKFold(n_splits=DOBRAS_CV, n_repeats=REPETICOES_CV, random_state=SEMENTE)
    rodadas = []
    for idx_treino, idx_teste in divisor.split(X, y):
        y_treino, y_teste = y.iloc[idx_treino], y.iloc[idx_teste]
        clf = novo_classificador().fit(X.iloc[idx_treino], y_treino)
        prob = clf.predict_proba(X.iloc[idx_teste])[:, 1]
        rodadas.append(metricas_classe_rara(y_teste, prob, y_treino.mean()))
    rodadas = pd.DataFrame(rodadas)[METRICAS_VALIDACAO]
    return pd.DataFrame({"media": rodadas.mean(), "desvio": rodadas.std(ddof=1), "rodadas": len(rodadas)})


def validacao_temporal(base: pd.DataFrame, X: pd.DataFrame, y: pd.Series) -> pd.DataFrame:
    """
    Validação por período em janela crescente: para cada ano, treina com todos os anos anteriores
    e testa nesse ano. Mede se o padrão aprendido no passado se mantém depois.
    """
    anos = sorted(base["ano"].unique())
    linhas = []
    for ano in anos[ANOS_MINIMOS_TREINO:]:
        treino, teste = (base["ano"] < ano).to_numpy(), (base["ano"] == ano).to_numpy()
        y_treino, y_teste = y[treino], y[teste]
        if y_teste.nunique() < 2 or y_treino.nunique() < 2:
            continue
        clf = novo_classificador().fit(X[treino], y_treino)
        prob = clf.predict_proba(X[teste])[:, 1]
        linhas.append({
            "ano": int(ano),
            "anos_treino": f"{anos[0]}–{ano - 1}",
            "n_teste": int(teste.sum()),
            "prevalencia": y_teste.mean(),
            **metricas_classe_rara(y_teste, prob, y_treino.mean()),
        })
    return pd.DataFrame(linhas)


def treinar_modelo(df: pd.DataFrame) -> dict:
    """
    Ajusta e avalia a regressão logística na base comparável.

    As métricas de teste vêm de uma divisão aleatória 75/25. O modelo devolvido, usado nas razões
    de chance e no simulador, é ajustado na base comparável inteira. A validação cruzada repetida e
    a validação por ano medem a estabilidade das métricas e se o padrão se mantém nos anos seguintes.
    """
    base = base_comparavel(df)
    base = base[base["hora_num"].notnull()].reset_index(drop=True)
    refs = referencias(base)
    X, y = montar_features(base, refs), base["severidade_grave_ou_fatal"]
    X_treino, X_teste, y_treino, y_teste = train_test_split(X, y, test_size=0.25, random_state=SEMENTE, stratify=y)

    clf_teste = novo_classificador().fit(X_treino, y_treino)
    pred = clf_teste.predict(X_teste)
    prob = clf_teste.predict_proba(X_teste)[:, 1]
    metricas_teste = metricas_classe_rara(y_teste, prob, y_treino.mean())

    clf = novo_classificador().fit(X, y)
    return {
        "modelo": clf,
        "features": X.columns.tolist(),
        "referencias": refs,
        "razoes_chance": razoes_de_chance(clf, X),
        "n_total": len(y),
        "n_treino": len(y_treino),
        "n_teste": len(y_teste),
        "prevalencia": y.mean(),
        "acuracia": accuracy_score(y_teste, pred),
        "acuracia_balanceada": balanced_accuracy_score(y_teste, pred),
        "referencia": y_teste.value_counts(normalize=True).max(),
        "teste": metricas_teste,
        "auc": metricas_teste["auc"],
        "auc_ic": intervalo_bootstrap(y_teste, prob, roc_auc_score),
        "pr_auc": metricas_teste["pr_auc"],
        "pr_auc_ic": intervalo_bootstrap(y_teste, prob, average_precision_score),
        "validacao_cruzada": validacao_cruzada(X, y),
        "temporal": validacao_temporal(base, X, y),
    }
