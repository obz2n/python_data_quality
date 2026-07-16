import logging

import pandas as pd

from config import CONFIG

logger = logging.getLogger(__name__)


def carregar_csv(caminho: str) -> pd.DataFrame:
    """Tenta ler o CSV com diferentes encodings e separadores."""
    encodings = ["utf-8", "latin-1", "cp1252", "utf-8-sig"]
    separadores = [",", ";", "\t", "|"]
    tentativas_falhas = []

    for enc in encodings:
        for sep in separadores:
            try:
                df = pd.read_csv(caminho, encoding=enc, sep=sep, low_memory=False)
                if df.shape[1] > 1:
                    logger.info("CSV lido com sucesso: encoding=%s, sep=%r", enc, sep)
                    return df
            except Exception as e:
                tentativas_falhas.append((enc, sep, str(e)))
                continue

    detalhes = "\n".join(f"  encoding={e}, sep={s!r}: {err}" for e, s, err in tentativas_falhas)
    raise ValueError(
        f"Não foi possível ler o arquivo: {caminho}\nTentativas realizadas:\n{detalhes}"
    )


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
        # Testa amostra da coluna: se algum formato configurado bate bem, marca como data
        amostra = df[col].dropna().astype(str).head(20)
        if amostra.empty:
            continue
        for fmt in CONFIG["formatos_data"]:
            parsed = pd.to_datetime(amostra, format=fmt, errors="coerce")
            if parsed.notna().mean() >= 0.9:
                candidatas.append(col)
                break
    return list(dict.fromkeys(candidatas))  # remove duplicatas mantendo ordem


def tentar_parse_data(serie: pd.Series) -> pd.Series:
    """
    Tenta converter uma série para datetime testando cada formato configurado
    e ficando com o que obtiver a maior taxa de conversão bem-sucedida.

    OBS: `pd.to_datetime(..., errors="coerce")` nunca levanta exceção - valores
    que não batem viram NaT silenciosamente. Por isso não dá pra usar try/except
    para decidir qual formato "funcionou": é preciso medir a taxa de acerto de
    cada formato e escolher o melhor.
    """
    melhor_resultado = None
    melhor_taxa = -1.0

    for fmt in CONFIG["formatos_data"]:
        parsed = pd.to_datetime(serie, format=fmt, errors="coerce")
        taxa = parsed.notna().mean() if len(parsed) > 0 else 0.0
        if taxa > melhor_taxa:
            melhor_taxa, melhor_resultado = taxa, parsed
        if taxa == 1.0:
            break

    # Se nenhum formato configurado deu conta de pelo menos metade dos valores,
    # tenta inferência automática do pandas como última alternativa.
    if melhor_taxa < 0.5:
        parsed_inferido = pd.to_datetime(serie, errors="coerce")
        taxa_inferido = parsed_inferido.notna().mean() if len(parsed_inferido) > 0 else 0.0
        if taxa_inferido > melhor_taxa:
            melhor_resultado = parsed_inferido

    return melhor_resultado if melhor_resultado is not None else pd.to_datetime(pd.Series(dtype="object"))
