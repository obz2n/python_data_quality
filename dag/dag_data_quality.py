"""
DAG de Qualidade de Dados
=========================

Lê um CSV, roda os 6 pilares de qualidade em paralelo, consolida um score
geral ponderado e persiste o resultado (JSON + SQLite) para o dashboard
Streamlit consumir.

Estrutura:
    verificar_arquivo  ->  [completude, consistencia, conformidade,
                             integridade, precisao, atualidade]  ->  consolidar  ->  alerta_qualidade

Requisitos:
    - O código de `src/` deste projeto deve estar disponível no PYTHONPATH
      do worker do Airflow (ver docker-compose.yaml / Dockerfile).
    - Variáveis de execução configuráveis via Airflow Variables (ver função
      `_get_config` abaixo) para não precisar alterar a DAG a cada novo CSV.
"""
from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

from airflow.decorators import dag, task
from airflow.exceptions import AirflowException
from airflow.models import Variable
from airflow.operators.python import get_current_context

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuração
# ---------------------------------------------------------------------------

DEFAULT_ARGS = {
    "owner": "data-quality-team",
    "retries": 1,
    "retry_delay": timedelta(minutes=2),
    "email_on_failure": False,
}

# Threshold abaixo do qual a DAG sinaliza falha de qualidade (task de alerta)
SCORE_MINIMO_ACEITAVEL = 70.0

PESOS_SCORE = {
    "completude": 0.20,
    "consistencia": 0.15,
    "conformidade": 0.15,
    "integridade": 0.20,
    "precisao": 0.15,
    "atualidade": 0.15,
}


def _get_config() -> dict:
    """
    Lê caminho do CSV e diretório de resultados a partir de Airflow Variables.
    Se `dq_csv_path` não estiver definida, seleciona automaticamente o CSV
    modificado mais recentemente em `dq_data_dir` (padrão: /opt/airflow/data).
    """
    data_dir = Path(Variable.get("dq_data_dir", default_var="/opt/airflow/data"))

    csv_path = Variable.get("dq_csv_path", default_var="")
    if not csv_path:
        csvs = sorted(data_dir.glob("*.csv"), key=lambda p: p.stat().st_mtime, reverse=True)
        csv_path = str(csvs[0]) if csvs else str(data_dir / "dados.csv")

    return {
        "csv_path": csv_path,
        "data_dir": str(data_dir),
        "resultados_dir": Variable.get("dq_resultados_dir", default_var="/opt/airflow/resultados"),
    }


# ---------------------------------------------------------------------------
# DAG
# ---------------------------------------------------------------------------

@dag(
    dag_id="data_quality_pipeline",
    description="Avalia qualidade de um CSV em 6 pilares e consolida um score geral",
    schedule="@daily",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args=DEFAULT_ARGS,
    tags=["data-quality", "csv"],
)
def data_quality_pipeline():

    @task
    def verificar_arquivo() -> dict:
        """Confere se o CSV existe e consegue ser lido antes de disparar as tasks paralelas."""
        # import feito dentro da task para garantir que o PYTHONPATH do worker já
        # foi resolvido no momento da execução (boa prática em DAGs com código externo)
        from leitura import carregar_csv

        config = _get_config()
        caminho = config["csv_path"]
        data_dir = Path(config["data_dir"])

        # Lista todos os CSVs disponíveis para facilitar o diagnóstico nos logs
        csvs_disponiveis = sorted(data_dir.glob("*.csv"), key=lambda p: p.stat().st_mtime, reverse=True)
        if csvs_disponiveis:
            logger.info("CSVs disponíveis em %s: %s", data_dir,
                        ", ".join(p.name for p in csvs_disponiveis))
        logger.info("CSV selecionado: %s", caminho)

        if not Path(caminho).exists():
            raise AirflowException(
                f"Arquivo não encontrado: {caminho}. "
                f"CSVs disponíveis: {[p.name for p in csvs_disponiveis] or 'nenhum'}"
            )

        df = carregar_csv(caminho)
        logger.info("Arquivo validado: %s (%d linhas x %d colunas)", caminho, *df.shape)
        return {"csv_path": caminho, "linhas": df.shape[0], "colunas": df.shape[1]}

    def _carregar_df_e_colunas_data():
        """Helper reaproveitado pelas tasks de pilar (cada task carrega o CSV de novo -
        é mais barato e robusto do que passar o DataFrame inteiro via XCom)."""
        from leitura import carregar_csv, detectar_colunas_data
        from config import CONFIG

        config = _get_config()
        df = carregar_csv(config["csv_path"])
        colunas_data = CONFIG["colunas_data"] or detectar_colunas_data(df)
        return df, colunas_data

    @task
    def checar_completude(_: dict) -> dict:
        from completude import avaliar_completude
        df, _cd = _carregar_df_e_colunas_data()
        resultado = avaliar_completude(df)
        resultado.pop("detalhe", None)  # DataFrame não serializa bem em XCom; fica só no relatório final se precisar
        return resultado

    @task
    def checar_consistencia(_: dict) -> dict:
        from consistencia import avaliar_consistencia
        df, _cd = _carregar_df_e_colunas_data()
        return avaliar_consistencia(df)

    @task
    def checar_conformidade(_: dict) -> dict:
        from conformidade import avaliar_conformidade
        df, colunas_data = _carregar_df_e_colunas_data()
        return avaliar_conformidade(df, colunas_data)

    @task
    def checar_integridade(_: dict) -> dict:
        from integridade import avaliar_integridade
        df, _cd = _carregar_df_e_colunas_data()
        return avaliar_integridade(df)

    @task
    def checar_precisao(_: dict) -> dict:
        from precisao import avaliar_precisao
        df, _cd = _carregar_df_e_colunas_data()
        return avaliar_precisao(df)

    @task
    def checar_atualidade(_: dict) -> dict:
        from atualidade import avaliar_atualidade
        df, colunas_data = _carregar_df_e_colunas_data()
        return avaliar_atualidade(df, colunas_data)

    @task
    def consolidar(info_arquivo: dict, completude: dict, consistencia: dict,
                    conformidade: dict, integridade: dict, precisao: dict,
                    atualidade: dict) -> dict:
        """Calcula o score geral ponderado e persiste em JSON + SQLite."""
        scores = {
            "completude": completude["score"],
            "consistencia": consistencia["score"],
            "conformidade": conformidade["score"],
            "integridade": integridade["score"],
            "precisao": precisao["score"],
            "atualidade": atualidade["score"],
        }
        score_geral = round(sum(scores[p] * peso for p, peso in PESOS_SCORE.items()), 2)

        pacote = {
            "executado_em": datetime.now(timezone.utc).isoformat(),
            "arquivo": info_arquivo["csv_path"],
            "linhas": info_arquivo["linhas"],
            "colunas": info_arquivo["colunas"],
            "score_geral": score_geral,
            "scores_por_pilar": scores,
            "detalhes": {
                "completude": completude,
                "consistencia": consistencia,
                "conformidade": conformidade,
                "integridade": integridade,
                "precisao": precisao,
                "atualidade": atualidade,
            },
        }

        config = _get_config()
        destino = Path(config["resultados_dir"])
        destino.mkdir(parents=True, exist_ok=True)

        # JSON (histórico legível / consumo eventual por outras ferramentas)
        contexto = get_current_context()
        run_id = contexto["run_id"].replace(":", "-").replace("+", "_")
        caminho_json = destino / f"resultado_{run_id}.json"
        def _limpar_para_json(obj):
            """Converte tipos numpy não-serializáveis antes do json.dump."""
            import numpy as np
            if isinstance(obj, dict):
                return {k: _limpar_para_json(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [_limpar_para_json(v) for v in obj]
            if isinstance(obj, (np.integer,)):
                return int(obj)
            if isinstance(obj, (np.floating,)):
                return float(obj)
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            return obj

        pacote = _limpar_para_json(pacote)

        with open(caminho_json, "w", encoding="utf-8") as f:
            json.dump(pacote, f, ensure_ascii=False, indent=2)

        # SQLite (fonte de dados do dashboard Streamlit)
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
                scores["atualidade"], json.dumps(pacote["detalhes"], ensure_ascii=False),
            ))
            conn.commit()

        logger.info("Score geral: %.2f | JSON: %s | SQLite: %s", score_geral, caminho_json, caminho_db)
        return pacote

    @task.branch
    def avaliar_threshold(pacote: dict) -> str:
        """Decide se segue para 'qualidade_ok' ou 'qualidade_baixa' com base no score geral."""
        if pacote["score_geral"] < SCORE_MINIMO_ACEITAVEL:
            return "qualidade_baixa"
        return "qualidade_ok"

    @task
    def qualidade_ok(pacote: dict) -> None:
        logger.info("✅ Qualidade dentro do esperado: score %.2f (mínimo %.2f)",
                     pacote["score_geral"], SCORE_MINIMO_ACEITAVEL)

    @task
    def qualidade_baixa(pacote: dict) -> None:
        # Ponto de extensão: plugar aqui alerta real (Slack, e-mail, etc.)
        logger.warning("⚠️ Qualidade ABAIXO do mínimo: score %.2f (mínimo %.2f)",
                        pacote["score_geral"], SCORE_MINIMO_ACEITAVEL)

    # ---- montagem do grafo ----
    info_arquivo = verificar_arquivo()

    resultado_completude = checar_completude(info_arquivo)
    resultado_consistencia = checar_consistencia(info_arquivo)
    resultado_conformidade = checar_conformidade(info_arquivo)
    resultado_integridade = checar_integridade(info_arquivo)
    resultado_precisao = checar_precisao(info_arquivo)
    resultado_atualidade = checar_atualidade(info_arquivo)

    pacote_final = consolidar(
        info_arquivo,
        resultado_completude,
        resultado_consistencia,
        resultado_conformidade,
        resultado_integridade,
        resultado_precisao,
        resultado_atualidade,
    )

    decisao = avaliar_threshold(pacote_final)
    decisao >> [qualidade_ok(pacote_final), qualidade_baixa(pacote_final)]


data_quality_pipeline()
