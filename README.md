# Calculadora de Estimativa de Horas de Implantação de ERP

Projeto Integrador, disciplina Ciência de Dados Aplicada a Situações de Mercado, Tecnologia em Banco de Dados, Senac EAD.

## Descrição

Este projeto propõe a prova de conceito de um modelo de inteligência de negócio que estima o tempo de implantação de um sistema de gestão empresarial (ERP) a partir de características do cliente, como número de usuários, quantidade de filiais, add-ons contratados e volume de notas fiscais.

A estimativa de esforço em projetos de implantação costuma ser feita de forma empírica, sem um critério quantitativo definido, o que aumenta o risco de propostas comerciais subdimensionadas ou superdimensionadas. Este projeto propõe uma abordagem orientada por dados para apoiar esse processo.

Para o desenvolvimento e a validação da prova de conceito, o projeto utiliza como referência o SAP Business One e a metodologia SAP Accelerated Implementation Program (SAP AIP).

## Estrutura do repositório

```
├── app.py                                      Aplicação Streamlit (calculadora, dashboard e modelo)
├── .streamlit/config.toml                      Tema da aplicação
├── notebooks/
│   ├── 01_analise_exploratoria_etapa1.ipynb   Análise exploratória (1ª etapa)
│   └── 02_modelagem_machine_learning.ipynb    Modelo de aprendizado de máquina (2ª etapa)
├── src/
│   ├── gerar_dados.py                          Geração da fonte de dados sintética
│   ├── etl.py                                  Extração, limpeza, transformação e carga
│   └── modelo.py                               Treino, comparação e avaliação dos modelos
├── data/
│   ├── raw/projetos_implantacao.csv            Fonte de dados (exportação dos handovers)
│   ├── processed/                              Relatório do ETL e registros rejeitados
│   └── calculadora.db                          Banco SQLite (camada operacional + Data Warehouse)
├── sql/
│   ├── mysql/                                  Scripts do cenário real em MySQL 8.0
│   └── sqlite/schema.sql                       Schema usado pela prova de conceito
├── models/                                     Métricas, comparação e importância das variáveis
├── scripts/                                    Rotinas de backup full e incremental (MySQL)
└── requirements.txt                            Bibliotecas necessárias
```

## 1ª etapa (concluída)

- Definição da fonte de dados, um dataset sintético de 300 projetos de implantação, estruturado com base em variáveis reais de um documento de handover técnico-comercial
- Análise exploratória com Pandas e NumPy
- Cinco visualizações com Matplotlib, com justificativa de como cada uma auxilia a tomada de decisão
- Distribuição de horas pelas cinco fases da metodologia SAP AIP

## 2ª etapa 
### Fonte de dados e banco de dados

O script `src/gerar_dados.py` reproduz exatamente a base da 1ª etapa (mesma semente aleatória, mesmas variáveis e mesmos pesos), acrescentando apenas a data da proposta comercial, gerada com semente independente para alimentar a dimensão tempo do Data Warehouse.

O script `src/etl.py` executa o processo ETL e carrega o banco em duas camadas.

| Camada | Tabelas | Finalidade |
|---|---|---|
| Operacional (OLTP) | `projeto`, `tipo_ambiente`, `modalidade`, `faixa_volume_notas`, `fase_aip` | Registro normalizado dos projetos |
| Data Warehouse | `dw_fato_projeto`, `dw_fato_horas_fase` e sete dimensões | Consultas analíticas do dashboard e base do modelo |

O Data Warehouse segue o esquema estrela, com duas tabelas fato que compartilham dimensões (constelação de fatos). A tabela `dw_fato_projeto` tem grão de um projeto de implantação e a tabela `dw_fato_horas_fase` tem grão de um projeto em uma fase da metodologia SAP AIP.

### Modelo de aprendizado de máquina

Abordagem supervisionada, tarefa de regressão, com saída `horas_totais_implantacao`. O código está em `src/modelo.py` e a análise completa, com gráficos, em `notebooks/02_modelagem_machine_learning.ipynb`.

- Pré-processamento com One-Hot Encoding nas variáveis categóricas e padronização nas numéricas
- Variável criada `usuarios_x_filiais` (interação entre usuários e filiais)
- Exclusão de identificadores, colunas redundantes e das horas por fase, que derivam do rótulo
- Comparação entre Regressão Linear, Ridge (L2), Lasso (L1) e Random Forest com validação cruzada 5-fold
- Avaliação final em 20% da base reservados para teste, com MAE, MSE, RMSE e R²
- Importância das variáveis por permutação

| Modelo escolhido | MAE | RMSE | R² |
|---|---|---|---|
| Lasso (L1) | 23,9 h | 29,8 h | 0,89 |

Os relatórios gerados ficam na pasta `models/`.

### Aplicação Streamlit

O arquivo `app.py` reúne a solução em uma aplicação web com quatro abas.

- **Calculadora** recebe as informações do handover e devolve a estimativa de horas, a faixa provável e o rateio pelas fases da SAP AIP, com alerta quando a entrada está fora da faixa usada no treino
- **Dashboard** apresenta indicadores e gráficos interativos sobre o Data Warehouse, com filtros por modalidade, tipo de ambiente e porte do cliente
- **Modelo** mostra a comparação entre os modelos, o overfitting, as previsões no teste e a importância das variáveis
- **Sobre o projeto** resume o contexto, a arquitetura e as limitações

Link da aplicação publicada: [calculadora-implantacao-sap.streamlit.app](https://calculadora-implantacao-sap.streamlit.app/)

### SGBD

O cenário real especificado utiliza **MySQL 8.0** (scripts na pasta `sql/mysql`, testados em MySQL 8.0.46), com restrições de integridade, índices, views, usuários com privilégios mínimos, carga por `LOAD DATA INFILE`, auditoria por triggers, logs e rotinas de backup full e incremental. A prova de conceito publicada utiliza **SQLite** com o mesmo modelo, pois o plano gratuito do Streamlit Cloud não oferece servidor MySQL.

## Ferramentas utilizadas

- Python, Pandas, NumPy, Matplotlib, scikit-learn
- Streamlit e Altair
- SQLite e MySQL 8.0
- Google Colab / Jupyter Notebook

## Como executar

```bash
pip install -r requirements.txt
python src/gerar_dados.py     # gera data/raw/projetos_implantacao.csv
python src/etl.py             # recria data/calculadora.db e o relatório do ETL
python src/modelo.py          # treina, compara e avalia os modelos (pasta models/)
streamlit run app.py          # abre a aplicação no navegador
```

O notebook da 1ª etapa pode ser aberto diretamente no Google Colab e executado de cima para baixo, sem arquivos externos.

## Integrantes do grupo

- Daniel Vieira Bueno
- Danielly Mendes Moura
- Everton Glad
- Gabriel Polido
- Giovanna Dainezi Franci
- Luan Cunha de Farias
- Tainá Lima do Nascimento
- Walquiria M. N. do Nascimento

## Disciplina

Projeto Integrador, Ciência de Dados Aplicada a Situações de Mercado
Professor Engº Jean Carlo Wagner
Senac EAD, Tecnologia em Banco de Dados
