# Sistema de Qualidade de Dados — 6 Pilares

Este repositório implementa um pipeline simples de avaliação de qualidade de dados em CSVs. Ele calcula um score por 6 pilares (completude, consistência, conformidade, integridade, precisão e atualidade), salva um relatório JSON e mantém um histórico em SQLite, que é consumido por um dashboard Streamlit.

Principais objetivos
- Fornecer um conjunto de regras automatizadas para avaliar a qualidade de um CSV.
- Orquestrar a execução com Airflow (DAG pronta).
- Expor um dashboard (Streamlit) que lê o histórico em SQLite e mostra métricas e detalhes.

Resumo dos 6 pilares
- Completude — valores ausentes / nulos
- Consistência — duplicatas, conflitos de tipo
- Conformidade — formatos esperados (datas, padrões)
- Integridade — relacionamentos e valores inválidos / regras de negócio simples
- Precisão — detecção de outliers (IQR) e valores suspeitos
- Atualidade — quão recentes são os registros (limiar configurável)

Estrutura do projeto
```
python_data_quality/
├── app/                       # Dashboard Streamlit
│   └── dashboard.py
├── dag/                       # DAG(s) para Airflow (montado em /opt/airflow/dags)
│   └── dag_data_quality.py
├── docker/                    # Dockerfiles para Airflow / Streamlit
│   ├── Dockerfile.airflow
│   └── Dockerfile.streamlit
├── src/                       # Implementação dos 6 pilares + orquestrador local
│   ├── main.py                # CLI para rodar a avaliação localmente
│   ├── leitura.py
│   ├── completude.py
│   ├── consistencia.py
│   ├── conformidade.py
│   ├── integridade.py
│   ├── precisao.py
│   └── atualidade.py
├── data/                      # Pasta para colocar arquivos .csv (montada no container do Airflow)
├── resultados/                # Resultados (JSON + historico_qualidade.db)
├── logs/                      # Logs do Airflow (volume)
├── plugins/                   # Plugins do Airflow (volume)
├── docker-compose.yml         # Orquestração (Airflow + Postgres + Streamlit)
├── requirements.txt           # Dependências para desenvolvimento local
├── requirements-dag.txt       # Dependências instaladas na imagem do Airflow (sem apache-airflow)
├── requirements-streamlit.txt # Dependências do dashboard
└── README.md
```

Como funciona (visão geral)
- Coloque um ou mais arquivos CSV em `data/` (cada arquivo pode ter nome diferente).
- A DAG do Airflow procura, por padrão, o CSV mais recentemente modificado em `/opt/airflow/data/` (mapeado para a pasta `data/` do projeto).
- A DAG executa as 6 tasks em paralelo, consolida um score ponderado, grava um JSON com detalhes e atualiza `resultados/historico_qualidade.db`.
- O Streamlit lê `resultados/historico_qualidade.db` e exibe o dashboard.

Quickstart (Docker)
1. Crie um arquivo `.env` com o UID do usuário atual (necessário para permissões do Airflow):

   ```bash
   echo "AIRFLOW_UID=$(id -u)" > .env
   ```

2. Coloque seus CSVs em `data/`.

3. Inicialize o banco do Airflow (rodar a primeira vez):

   ```bash
   docker compose up airflow-init
   ```

4. Suba os serviços:

   ```bash
   docker compose up -d
   ```

5. Acesse:
   - Airflow UI: http://localhost:8080  (usuário/senha: airflow / airflow)
   - Streamlit:  http://localhost:8501

Rodando localmente (sem Docker)
- Avaliar um CSV específico:

  ```bash
  # com venv ativado
  python src/main.py --csv data/seu_arquivo.csv
  ```

- Rodar o dashboard localmente:

  ```bash
  streamlit run app/dashboard.py
  ```

Integração com Airflow (variáveis úteis)
- `dq_data_dir` (opcional): diretório usado para procurar CSVs dentro do container (padrão `/opt/airflow/data`).
- `dq_csv_path` (opcional): caminho absoluto para um CSV específico. Se definido, a DAG usará esse arquivo em vez de auto-detectar.
- `dq_resultados_dir` (opcional): diretório onde ficam os resultados (padrão `/opt/airflow/resultados`).

Observações e dicas
- Os Dockerfiles estão em `docker/` — o `docker-compose.yml` foi ajustado para usar esses caminhos.
- `requirements-dag.txt` NÃO deve incluir `apache-airflow` (a imagem oficial já fornece o Airflow). Use esse arquivo apenas para libs do seu código (pandas, numpy, pandera etc.).
- Se você encontrar pastas vazias `dags/` ou `dataset/` com dono `root` (criadas acidentalmente pelos volumes), remova-as na raiz do projeto antes de subir o compose, para evitar confusão:

  ```bash
  sudo rm -rf dags/ dataset/
  ```

- Para forçar o uso de um CSV específico pela DAG sem alterar a DAG, defina a Airflow Variable `dq_csv_path` na UI (Admin → Variables) com o caminho absoluto no container (ex: `/opt/airflow/data/outro.csv`).

Contribuições
- Correções, melhorias nos checks e testes automatizados são bem-vindos. Abra issues ou PRs.

Licença
- MIT (ou especifique a licença que preferir).

---

## Autor

[Juliano Laurentino](https://www.linkedin.com/in/julianolaurentinodasilva/)
