
import pandas as pd
import numpy as np

from config import CONFIG


def avaliar_atualidade(df: pd.DataFrame, colunas_data: list) -> dict:
    hoje = pd.Timestamp.today()
    limite_dias = CONFIG["atualidade_limite_dias"]
    analise = {}

    for col in colunas_data:
        if col not in df.columns:
            continue
        parsed = tentar_parse_data(df[col].dropna().astype(str))
        parsed = parsed.dropna()
        if len(parsed) == 0:
            continue
        diff = (hoje - parsed).dt.days
        desatualizados = int((diff > limite_dias).sum())
        media_dias = float(diff.mean())
        mais_recente = parsed.max()
        mais_antigo = parsed.min()
        analise[col] = {
            "registros_analisados": len(parsed),
            "desatualizados": desatualizados,
            "pct_desatualizados": round(desatualizados / len(parsed) * 100, 2),
            "media_dias_atraso": round(media_dias, 1),
            "data_mais_recente": str(mais_recente.date()),
            "data_mais_antiga": str(mais_antigo.date()),
        }

    if analise:
        media_pct = np.mean([v["pct_desatualizados"] for v in analise.values()])
        score = max(0, 100 - media_pct)
    else:
        score = 100.0

    return {
        "score": round(score, 2),
        "analise_por_coluna": analise,
        "limite_dias": limite_dias,
    }
