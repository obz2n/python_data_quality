from pathlib import Path

# Diretório raiz do projeto (pasta que contém "src/")
BASE_DIR = Path(__file__).resolve().parent.parent

#  Constantes e configurações globais
CONFIG = {
    # Colunas que NUNCA devem ser nulas (lista de nomes exatos)
    "colunas_obrigatorias": [],

    # Colunas que devem ser únicas (ex: CPF, ID)
    "colunas_unicas": [],

    # Formatos de data aceitos (o script testa todos e usa o de maior taxa de acerto)
    "formatos_data": ["%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%Y/%m/%d", "%d.%m.%Y"],

    # Colunas que são datas (deixe vazio para detecção automática)
    "colunas_data": [],

    # Número de dias: registros mais antigos que isso geram alerta de atualidade
    "atualidade_limite_dias": 365,

    # Limiar de outlier via IQR (padrão 1.5)
    "outlier_iqr_fator": 1.5,

    # Porcentagem mínima aceitável de completude por coluna (0-100)
    "completude_minima_pct": 80.0,

    # Palavras-chave usadas para identificar colunas que deveriam ser positivas
    # (usado em integridade.py)
    "palavras_positivas": [
        "valor", "preco", "preço", "quantidade", "qtd", "qtde",
        "total", "age", "idade", "salario", "salário",
    ],

    # Peso de cada pilar no score consolidado (deve somar 1.0)
    "pesos_score": {
        "completude": 0.20,
        "consistencia": 0.15,
        "conformidade": 0.15,
        "integridade": 0.20,
        "precisao": 0.15,
        "atualidade": 0.15,
    },
}

# Entrada e saída (caminhos absolutos, resolvidos a partir da raiz do projeto
# em vez de caminho relativo, para funcionar igual local, via Airflow, etc.)
DIR_DATA = BASE_DIR / "data"
DIR_RESULTADOS = BASE_DIR / "resultados"

# Seleciona automaticamente o CSV mais recente em data/.
# Use --csv na linha de comando (main.py) para escolher um arquivo específico.
_csvs_disponiveis = sorted(DIR_DATA.glob("*.csv"), key=lambda p: p.stat().st_mtime, reverse=True)
ARQUIVO_CSV = _csvs_disponiveis[0] if _csvs_disponiveis else DIR_DATA / "dados.csv"
