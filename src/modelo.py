"""Modelo exploratório de gravidade, compartilhado por relatório, notebooks e dashboard."""

import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.inspection import permutation_importance
from sklearn.metrics import accuracy_score, balanced_accuracy_score, roc_auc_score
from sklearn.model_selection import train_test_split

from src.metricas import base_comparavel

FEATURES_NUMERICAS = [
    "envolve_moto", "envolve_auto", "envolve_pedestre", "envolve_bicicleta", "envolve_pesado",
    "is_fim_de_semana", "hora_num",
]


def montar_features(df: pd.DataFrame) -> pd.DataFrame:
    return pd.concat([
        df[FEATURES_NUMERICAS],
        pd.get_dummies(df["tipo_via_simplificado"], prefix="via", drop_first=True),
        pd.get_dummies(df["tipo_sinistro_simplificado"], prefix="tipo", drop_first=True),
        pd.get_dummies(df["turno_ajustado"], prefix="turno", drop_first=True),
    ], axis=1)


def treinar_modelo(df: pd.DataFrame) -> dict:
    """Treina e avalia o Random Forest na base comparável, com conjunto de teste separado."""
    base = base_comparavel(df)
    base = base[base["hora_num"].notnull()]
    X, y = montar_features(base), base["severidade_grave_ou_fatal"]
    X_treino, X_teste, y_treino, y_teste = train_test_split(X, y, test_size=0.25, random_state=42, stratify=y)

    # Sem class_weight, para que predict_proba reflita a frequência das classes
    clf = RandomForestClassifier(n_estimators=150, max_depth=10, min_samples_leaf=5, random_state=42, n_jobs=-1)
    clf.fit(X_treino, y_treino)
    pred = clf.predict(X_teste)

    permutacao = permutation_importance(clf, X_teste, y_teste, n_repeats=10, random_state=42, scoring="neg_log_loss")
    return {
        "modelo": clf,
        "features": X.columns.tolist(),
        "importancias": pd.Series(permutacao.importances_mean, index=X.columns).sort_values(ascending=False),
        "n_treino": len(y_treino),
        "n_teste": len(y_teste),
        "prevalencia": y.mean(),
        "acuracia": accuracy_score(y_teste, pred),
        "acuracia_balanceada": balanced_accuracy_score(y_teste, pred),
        "referencia": y_teste.value_counts(normalize=True).max(),
        "auc": roc_auc_score(y_teste, clf.predict_proba(X_teste)[:, 1]),
    }
