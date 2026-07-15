
import pandas as pd
import numpy as np


def avaliar_integridade(df: pd.DataFrame) -> dict:
    problemas = {}

    # Verifica valores negativos em colunas que deveriam ser positivas
    colunas_num = df.select_dtypes(include=[np.number]).columns
    palavras_positivas = ["valor", "preco", "preço", "quantidade", "qtd", "qtde",
                          "total", "age", "idade", "salario", "salário"]
    negativos = {}
    for col in colunas_num:
        if any(p in col.lower() for p in palavras_positivas):
            n_neg = int((df[col] < 0).sum())
            if n_neg > 0:
                negativos[col] = n_neg

    # Verifica strings vazias (whitespace only)
    strings_vazias = {}
    for col in df.select_dtypes(include="object").columns:
        n = int((df[col].astype(str).str.strip() == "").sum())
        if n > 0:
            strings_vazias[col] = n

    total_problemas = sum(negativos.values()) + sum(strings_vazias.values())
    total_registros = len(df)
    penalidade = min((total_problemas / total_registros) * 100, 100) if total_registros > 0 else 0
    score = max(0, 100 - penalidade)

    return {
        "score": round(score, 2),
        "valores_negativos_suspeitos": negativos,
        "strings_vazias": strings_vazias,
        "total_problemas": total_problemas,
    }
