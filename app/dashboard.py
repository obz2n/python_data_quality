"""Dashboard de Qualidade de Dados - lê o SQLite gerado pela DAG do Airflow."""
import json
import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Qualidade de Dados", layout="wide")

CAMINHO_DB = Path("/app/resultados/historico_qualidade.db")

st.title("📊 Painel de Qualidade de Dados")

if not CAMINHO_DB.exists():
    st.warning(
        "Ainda não há execuções registradas. Rode a DAG `data_quality_pipeline` "
        "no Airflow para gerar o primeiro resultado."
    )
    st.stop()

with sqlite3.connect(CAMINHO_DB) as conn:
    df = pd.read_sql_query("SELECT * FROM execucoes ORDER BY id DESC", conn)

if df.empty:
    st.info("Nenhuma execução encontrada ainda.")
    st.stop()

ultima = df.iloc[0]

col1, col2, col3 = st.columns(3)
col1.metric("Score geral (última execução)", f"{ultima['score_geral']:.1f} / 100")
col2.metric("Linhas avaliadas", int(ultima["linhas"]))
col3.metric("Execuções registradas", len(df))

st.subheader("Score por pilar — última execução")
pilares = ["completude", "consistencia", "conformidade", "integridade", "precisao", "atualidade"]
scores_atuais = {p: ultima[f"score_{p}"] for p in pilares}
st.bar_chart(pd.Series(scores_atuais))

st.subheader("Histórico do score geral")
historico = df[["executado_em", "score_geral"]].set_index("executado_em").sort_index()
st.line_chart(historico)

st.subheader("Detalhes da última execução")
with st.expander("Ver JSON completo"):
    st.json(json.loads(ultima["detalhes_json"]))

st.subheader("Todas as execuções")
st.dataframe(df.drop(columns=["detalhes_json"]), use_container_width=True)
