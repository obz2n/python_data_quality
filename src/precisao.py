import numpy as np
import pandas as pd

from config import CONFIG


def avaliar_precisao(df: pd.DataFrame) -> dict:
    outliers = {}
    fator = CONFIG["outlier_iqr_fator"]
    colunas_num = df.select_dtypes(include=[np.number]).columns

    for col in colunas_num:
        serie = df[col].dropna()
        if len(serie) < 10:
            continue
        Q1 = serie.quantile(0.25)
        Q3 = serie.quantile(0.75)
        IQR = Q3 - Q1
        if IQR == 0:
            continue
        limite_inf = Q1 - fator * IQR
        limite_sup = Q3 + fator * IQR
        n_out = int(((serie < limite_inf) | (serie > limite_sup)).sum())
        if n_out > 0:
            outliers[col] = {
                "outliers": n_out,
                "pct": round(n_out / len(serie) * 100, 2),
                "limite_inf": round(float(limite_inf), 4),
                "limite_sup": round(float(limite_sup), 4),
                "min": round(float(serie.min()), 4),
                "max": round(float(serie.max()), 4),
            }

    total_out = sum(v["outliers"] for v in outliers.values())
    total_vals = sum(df[c].notna().sum() for c in colunas_num)
    pct_out = (total_out / total_vals * 100) if total_vals > 0 else 0
    score = max(0, 100 - pct_out * 2)

    return {
        "score": round(score, 2),
        "outliers_por_coluna": outliers,
        "total_outliers": total_out,
        "pct_outliers": round(pct_out, 2),
    }
