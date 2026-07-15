#  Constantes e configurações globais
CONFIG = {
    # Colunas que NUNCA devem ser nulas (lista de nomes exatos)
    "colunas_obrigatorias": [],

    # Colunas que devem ser únicas (ex: CPF, ID)
    "colunas_unicas": [],

    # Formatos de data aceitos (o script testa todos automaticamente)
    "formatos_data": ["%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%Y/%m/%d", "%d.%m.%Y"],

    # Colunas que são datas (deixe vazio para detecção automática)
    "colunas_data": [],

    # Número de dias: registros mais antigos que isso geram alerta de atualidade
    "atualidade_limite_dias": 365,

    # Limiar de outlier via IQR (padrão 1.5)
    "outlier_iqr_fator": 1.5,

    # Porcentagem mínima aceitável de completude por coluna (0–100)
    "completude_minima_pct": 80.0,
}


# Entrada e saída
ARQUIVO_CSV = r"../dataset/Cleaned_Laptop_data.csv"
ARQUIVO_PDF = None
