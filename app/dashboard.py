"""Dashboard de Qualidade de Dados - lê o SQLite gerado pela DAG do Airflow."""
import json
import os
import sqlite3
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(
    page_title="Qualidade de Dados",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

PILARES = ["completude", "consistencia", "conformidade", "integridade", "precisao", "atualidade"]

# -----------------------------------------------------------------------------
# Carregamento de dados
# -----------------------------------------------------------------------------

# Resolve o caminho do banco de forma portável:
#   - Local (venv): app/dashboard.py → parent.parent = raiz do projeto
#   - Docker:       /app/app/dashboard.py → parent.parent = /app
# A variável de ambiente DQ_DB_PATH sobrescreve tudo, se definida.
_default_db = Path(__file__).resolve().parent.parent / "resultados" / "historico_qualidade.db"
CAMINHO_DB = Path(os.environ.get("DQ_DB_PATH", str(_default_db)))


@st.cache_data(ttl=60, show_spinner="Carregando execuções...")
def carregar_dados(caminho_db: str, mtime: float) -> pd.DataFrame:
    """Lê a tabela de execuções. `mtime` entra no cache key para invalidar
    o cache automaticamente sempre que o arquivo do banco mudar."""
    with sqlite3.connect(caminho_db) as conn:
        df = pd.read_sql_query("SELECT * FROM execucoes ORDER BY id DESC", conn)
    if not df.empty and "executado_em" in df.columns:
        df["executado_em"] = pd.to_datetime(df["executado_em"], errors="coerce")
    return df


def cor_por_score(score: float) -> str:
    if score >= 90:
        return "#2ecc71"  # verde
    if score >= 70:
        return "#f1c40f"  # amarelo
    return "#e74c3c"  # vermelho


st.title("📊 Painel de Qualidade de Dados")

if not CAMINHO_DB.exists():
    st.warning(
        "Ainda não há execuções registradas. Rode a DAG `data_quality_pipeline` "
        "no Airflow para gerar o primeiro resultado."
    )
    st.stop()

df = carregar_dados(str(CAMINHO_DB), CAMINHO_DB.stat().st_mtime)

if df.empty:
    st.info("Nenhuma execução encontrada ainda.")
    st.stop()

# -----------------------------------------------------------------------------
# Sidebar - filtros
# -----------------------------------------------------------------------------
with st.sidebar:
    st.header("Filtros")

    if pd.api.types.is_datetime64_any_dtype(df["executado_em"]):
        data_min = df["executado_em"].min().date()
        data_max = df["executado_em"].max().date()
        intervalo = st.date_input(
            "Período",
            value=(data_min, data_max),
            min_value=data_min,
            max_value=data_max,
        )
        if isinstance(intervalo, tuple) and len(intervalo) == 2:
            inicio, fim = intervalo
            mascara = (df["executado_em"].dt.date >= inicio) & (df["executado_em"].dt.date <= fim)
            df = df.loc[mascara]

    pilares_selecionados = st.multiselect(
        "Pilares exibidos",
        options=PILARES,
        default=PILARES,
    )

    st.caption(f"Banco: `{CAMINHO_DB}`")
    if st.button("🔄 Atualizar dados"):
        st.cache_data.clear()
        st.rerun()

if df.empty:
    st.info("Nenhuma execução no período selecionado.")
    st.stop()

df = df.sort_values("executado_em" if "executado_em" in df.columns else "id", ascending=False)
ultima = df.iloc[0]
anterior = df.iloc[1] if len(df) > 1 else None

# -----------------------------------------------------------------------------
# Métricas principais (com variação em relação à execução anterior)
# -----------------------------------------------------------------------------
col1, col2, col3, col4 = st.columns(4)

delta_score = f"{ultima['score_geral'] - anterior['score_geral']:+.1f}" if anterior is not None else None
delta_linhas = f"{int(ultima['linhas'] - anterior['linhas']):+d}" if anterior is not None else None

col1.metric("Score geral (última execução)", f"{ultima['score_geral']:.1f} / 100", delta_score)
col2.metric("Linhas avaliadas", f"{int(ultima['linhas']):,}".replace(",", "."), delta_linhas)
col3.metric("Execuções registradas", len(df))
if "executado_em" in df.columns and pd.notna(ultima["executado_em"]):
    col4.metric("Última execução", ultima["executado_em"].strftime("%d/%m/%Y %H:%M"))

st.divider()

# -----------------------------------------------------------------------------
# Score por pilar — última execução
# -----------------------------------------------------------------------------
st.subheader("Score por pilar — última execução")

scores_atuais = pd.Series({p: ultima[f"score_{p}"] for p in pilares_selecionados})
cores = [cor_por_score(v) for v in scores_atuais.values]

fig_pilares = go.Figure(
    go.Bar(
        x=scores_atuais.index,
        y=scores_atuais.values,
        marker_color=cores,
        text=[f"{v:.1f}" for v in scores_atuais.values],
        textposition="outside",
    )
)
fig_pilares.update_layout(
    yaxis_range=[0, 105],
    yaxis_title="Score",
    xaxis_title=None,
    xaxis_tickangle=0,  # nomes na horizontal
    margin=dict(t=10, b=10),
    height=400,
)
fig_pilares.add_hline(y=70, line_dash="dot", line_color="gray", annotation_text="meta mínima (70)")
st.plotly_chart(fig_pilares, use_container_width=True)

# -----------------------------------------------------------------------------
# Histórico do score geral
# -----------------------------------------------------------------------------
st.subheader("Histórico do score geral")

historico = df[["executado_em", "score_geral"]].sort_values("executado_em")
fig_historico = px.line(
    historico,
    x="executado_em",
    y="score_geral",
    markers=True,
    labels={"executado_em": "Execução", "score_geral": "Score geral"},
)
fig_historico.update_traces(line_color="#3498db", marker=dict(size=7))
fig_historico.update_layout(
    yaxis_range=[0, 105],
    xaxis_tickangle=0,  # datas na horizontal
    margin=dict(t=10, b=10),
    height=350,
)
fig_historico.add_hline(y=70, line_dash="dot", line_color="gray")
st.plotly_chart(fig_historico, use_container_width=True)

# -----------------------------------------------------------------------------
# Histórico por pilar (comparação entre execuções)
# -----------------------------------------------------------------------------
st.subheader("Histórico por pilar")

historico_pilares = df[["executado_em"] + [f"score_{p}" for p in pilares_selecionados]].sort_values("executado_em")
historico_pilares = historico_pilares.rename(columns={f"score_{p}": p for p in pilares_selecionados})
historico_pilares_long = historico_pilares.melt(
    id_vars="executado_em", var_name="pilar", value_name="score"
)

fig_pilares_hist = px.line(
    historico_pilares_long,
    x="executado_em",
    y="score",
    color="pilar",
    markers=True,
    labels={"executado_em": "Execução", "score": "Score", "pilar": "Pilar"},
)
fig_pilares_hist.update_layout(
    yaxis_range=[0, 105],
    xaxis_tickangle=0,
    margin=dict(t=10, b=10),
    height=400,
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
)
st.plotly_chart(fig_pilares_hist, use_container_width=True)

# -----------------------------------------------------------------------------
# Detalhes e tabela completa
# -----------------------------------------------------------------------------
st.subheader("Detalhes da última execução")
with st.expander("Ver JSON completo"):
    try:
        st.json(json.loads(ultima["detalhes_json"]))
    except (TypeError, json.JSONDecodeError):
        st.warning("Não foi possível interpretar o JSON de detalhes desta execução.")

st.subheader("Todas as execuções")
tabela = df.drop(columns=["detalhes_json"])
st.dataframe(tabela, use_container_width=True, hide_index=True)

st.download_button(
    "⬇️ Baixar histórico completo (CSV)",
    data=tabela.to_csv(index=False).encode("utf-8"),
    file_name="historico_qualidade.csv",
    mime="text/csv",
)
