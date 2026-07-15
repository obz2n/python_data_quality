import pandas as pd
from config import CONFIG

def avaliar_consistencia(df: pd.DataFrame) -> dict:
    # Duplicatas completas
    dup_completas = int(df.duplicated().sum())
    pct_dup = round(dup_completas / len(df) * 100, 2)

    # Duplicatas por colunas únicas configuradas
    dup_unicas = {}
    for col in CONFIG["colunas_unicas"]:
        if col in df.columns:
            n = int(df[col].dropna().duplicated().sum())
            if n > 0:
                dup_unicas[col] = n

    # Inconsistências de tipo: colunas numéricas com strings misturadas
    tipo_misto = {}
    for col in df.select_dtypes(include="object").columns:
        amostra = df[col].dropna().head(500)
        n_num = amostra.apply(lambda x: str(x).replace(",", ".").replace("-", "")
                               .replace(" ", "").isnumeric()).sum()
        if 0 < n_num < len(amostra) * 0.9 and n_num > len(amostra) * 0.1:
            tipo_misto[col] = {"numerico": int(n_num), "texto": int(len(amostra) - n_num)}

    penalidade = (pct_dup / 100) * 50 + min(len(dup_unicas) * 10, 30) + min(len(tipo_misto) * 5, 20)
    score = max(0, 100 - penalidade)

    return {
        "score": round(score, 2),
        "duplicatas_completas": dup_completas,
        "pct_duplicatas": pct_dup,
        "duplicatas_colunas_unicas": dup_unicas,
        "tipo_misto": tipo_misto,
    }
