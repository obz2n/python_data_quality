import pandas as pd
from .config import CONFIG

def carregar_csv(caminho: str) -> pd.DataFrame:
    """Tenta ler o CSV com diferentes encodings e separadores."""
    encodings = ["utf-8", "latin-1", "cp1252", "utf-8-sig"]
    separadores = [",", ";", "\t", "|"]
    for enc in encodings:
        for sep in separadores:
            try:
                df = pd.read_csv(caminho, encoding=enc, sep=sep, low_memory=False)
                if df.shape[1] > 1:
                    return df
            except Exception:
                continue
    raise ValueError(f"Não foi possível ler o arquivo: {caminho}")


def detectar_colunas_data(df: pd.DataFrame) -> list:
    """Detecta automaticamente colunas que parecem conter datas."""
    candidatas = []
    palavras_chave = ["data", "date", "dt_", "_dt", "vencimento", "nascimento",
                      "criacao", "criação", "abertura", "fechamento", "prazo"]
    for col in df.columns:
        col_lower = col.lower()
        if any(k in col_lower for k in palavras_chave):
            candidatas.append(col)
            continue
        # Testa amostra da coluna
        amostra = df[col].dropna().astype(str).head(20)
        for fmt in CONFIG["formatos_data"]:
            try:
                pd.to_datetime(amostra, format=fmt, errors="raise")
                candidatas.append(col)
                break
            except Exception:
                continue
    return list(set(candidatas))


def tentar_parse_data(serie: pd.Series) -> pd.Series:
    """Tenta converter uma série para datetime usando os formatos configurados."""
    for fmt in CONFIG["formatos_data"]:
        try:
            return pd.to_datetime(serie, format=fmt, errors="coerce")
        except Exception:
            continue
    return pd.to_datetime(serie, infer_datetime_format=True, errors="coerce")
