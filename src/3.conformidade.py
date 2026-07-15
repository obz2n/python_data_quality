
import pandas as pd
from config import CONFIG

def avaliar_conformidade(df: pd.DataFrame, colunas_data: list) -> dict:
    problemas_data = {}
    datas_invalidas_total = 0

    for col in colunas_data:
        if col not in df.columns:
            continue
        serie = df[col].dropna().astype(str)
        parsed = tentar_parse_data(serie)
        invalidas = int(parsed.isnull().sum())
        if invalidas > 0:
            problemas_data[col] = invalidas
            datas_invalidas_total += invalidas

    total_datas = sum(df[c].notna().sum() for c in colunas_data if c in df.columns)
    pct_invalido = (datas_invalidas_total / total_datas * 100) if total_datas > 0 else 0
    score = max(0, 100 - pct_invalido)

    return {
        "score": round(score, 2),
        "colunas_data_analisadas": colunas_data,
        "datas_invalidas": problemas_data,
        "total_datas_invalidas": datas_invalidas_total,
        "total_datas": int(total_datas),
    }
