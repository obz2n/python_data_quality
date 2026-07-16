"""
Orquestrador do pipeline de qualidade de dados.

Executa os 6 pilares sobre um CSV, consolida um score geral ponderado
e persiste o resultado em JSON e SQLite (histórico de execuções).

Uso:
    python main.py
    python main.py --csv /caminho/para/arquivo.csv
"""
import argparse
import json
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from config import ARQUIVO_CSV, CONFIG, DIR_RESULTADOS
from leitura import carregar_csv, detectar_colunas_data
from completude import avaliar_completude
from consistencia import avaliar_consistencia
from conformidade import avaliar_conformidade
from integridade import avaliar_integridade
from precisao import avaliar_precisao
from atualidade import avaliar_atualidade

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def _limpar_para_json(obj):
    """Converte DataFrames e tipos numpy dentro do resultado para algo serializável em JSON."""
    if isinstance(obj, pd.DataFrame):
        return obj.to_dict(orient="records")
    if isinstance(obj, dict):
        return {k: _limpar_para_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_limpar_para_json(v) for v in obj]
    if hasattr(obj, "item"):  # tipos numpy (int64, float64...)
        return obj.item()
    return obj


def executar_pipeline(caminho_csv: str) -> dict:
    """Executa os 6 pilares sobre o CSV informado e retorna o resultado consolidado."""
    logger.info("Iniciando leitura do CSV: %s", caminho_csv)
    df = carregar_csv(caminho_csv)
    logger.info("CSV carregado: %d linhas x %d colunas", df.shape[0], df.shape[1])

    colunas_data = CONFIG["colunas_data"] or detectar_colunas_data(df)
    logger.info("Colunas de data detectadas: %s", colunas_data)

    resultados = {
        "completude": avaliar_completude(df),
        "consistencia": avaliar_consistencia(df),
        "conformidade": avaliar_conformidade(df, colunas_data),
        "integridade": avaliar_integridade(df),
        "precisao": avaliar_precisao(df),
        "atualidade": avaliar_atualidade(df, colunas_data),
    }

    pesos = CONFIG["pesos_score"]
    score_geral = sum(resultados[pilar]["score"] * peso for pilar, peso in pesos.items())

    pacote = {
        "executado_em": datetime.now(timezone.utc).isoformat(),
        "arquivo": str(caminho_csv),
        "linhas": int(df.shape[0]),
        "colunas": int(df.shape[1]),
        "colunas_data_detectadas": colunas_data,
        "score_geral": round(score_geral, 2),
        "scores_por_pilar": {p: resultados[p]["score"] for p in resultados},
        "detalhes": resultados,
    }
    return pacote


def salvar_json(pacote: dict, destino: Path) -> Path:
    destino.mkdir(parents=True, exist_ok=True)
    nome_arquivo = f"resultado_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    caminho = destino / nome_arquivo
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(_limpar_para_json(pacote), f, ensure_ascii=False, indent=2)
    logger.info("Resultado salvo em JSON: %s", caminho)
    return caminho


def salvar_sqlite(pacote: dict, destino: Path) -> Path:
    """Grava um resumo (score geral + score por pilar) em uma tabela de histórico.
    É essa tabela que o Streamlit vai consultar para montar o dashboard."""
    destino.mkdir(parents=True, exist_ok=True)
    caminho_db = destino / "historico_qualidade.db"

    with sqlite3.connect(caminho_db) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS execucoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                executado_em TEXT NOT NULL,
                arquivo TEXT NOT NULL,
                linhas INTEGER,
                colunas INTEGER,
                score_geral REAL,
                score_completude REAL,
                score_consistencia REAL,
                score_conformidade REAL,
                score_integridade REAL,
                score_precisao REAL,
                score_atualidade REAL,
                detalhes_json TEXT
            )
        """)
        scores = pacote["scores_por_pilar"]
        conn.execute("""
            INSERT INTO execucoes (
                executado_em, arquivo, linhas, colunas, score_geral,
                score_completude, score_consistencia, score_conformidade,
                score_integridade, score_precisao, score_atualidade, detalhes_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            pacote["executado_em"], pacote["arquivo"], pacote["linhas"], pacote["colunas"],
            pacote["score_geral"], scores["completude"], scores["consistencia"],
            scores["conformidade"], scores["integridade"], scores["precisao"],
            scores["atualidade"], json.dumps(_limpar_para_json(pacote["detalhes"]), ensure_ascii=False),
        ))
        conn.commit()
    logger.info("Resultado gravado em SQLite: %s", caminho_db)
    return caminho_db


def main():
    parser = argparse.ArgumentParser(description="Pipeline de qualidade de dados")
    parser.add_argument("--csv", default=str(ARQUIVO_CSV), help="Caminho do arquivo CSV a avaliar")
    parser.add_argument("--saida", default=str(DIR_RESULTADOS), help="Diretório para salvar os resultados")
    args = parser.parse_args()

    pacote = executar_pipeline(args.csv)

    destino = Path(args.saida)
    salvar_json(pacote, destino)
    salvar_sqlite(pacote, destino)

    logger.info("Score geral: %.2f / 100", pacote["score_geral"])
    for pilar, score in pacote["scores_por_pilar"].items():
        logger.info("  - %s: %.2f", pilar, score)

    return pacote


if __name__ == "__main__":
    main()
