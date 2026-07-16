import pandas as pd
from config import CONFIG

def avaliar_completude(df: pd.DataFrame) -> dict:
    total_celulas = df.shape[0] * df.shape[1]
    nulos = df.isnull().sum()
    pct_nulo = (nulos / len(df) * 100).round(2)
    pct_preenchido = (100 - pct_nulo).round(2)

    # Colunas que ficam abaixo do mínimo configurado
    problemas = pct_preenchido[pct_preenchido < CONFIG["completude_minima_pct"]].to_dict()

    # Score: média ponderada de preenchimento
    score = float(pct_preenchido.mean())

    detalhe = pd.DataFrame({
        "Coluna": nulos.index,
        "Nulos": nulos.values,
        "% Preenchido": pct_preenchido.values
    }).sort_values("% Preenchido")

    # Alertas para colunas obrigatórias
    alertas_obrig = []
    for col in CONFIG["colunas_obrigatorias"]:
        if col in df.columns and df[col].isnull().any():
            n = int(df[col].isnull().sum())
            alertas_obrig.append(f"'{col}': {n} nulo(s) em coluna obrigatória")

    return {
        "score": round(score, 2),
        "total_nulos": int(nulos.sum()),
        "total_celulas": total_celulas,
        "detalhe": detalhe,
        "colunas_criticas": problemas,
        "alertas_obrigatorias": alertas_obrig,
    }
