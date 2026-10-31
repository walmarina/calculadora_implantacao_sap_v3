"""
Processo ETL (Extração, Limpeza, Transformação e Carga) da Calculadora de
Estimativa de Horas de Implantação de ERP.

Fonte    data/raw/projetos_implantacao.csv (exportação dos handovers)
Destino  data/calculadora.db (SQLite), com duas camadas
           1. Operacional (OLTP), tabelas normalizadas
           2. Data Warehouse, esquema estrela com duas tabelas fato

Etapas, conforme Pegetti (2021)
  1. Extração       leitura do arquivo da fonte
  2. Limpeza        validação de tipos, nulos, duplicados, domínios e faixas
  3. Transformação  padronização, chaves substitutas, dimensões e fatos
  4. Carga          atualização total do banco e conferência de integridade

Execução:  python src/etl.py
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
ARQUIVO_FONTE = RAIZ / "data" / "raw" / "projetos_implantacao.csv"
ARQUIVO_SCHEMA = RAIZ / "sql" / "sqlite" / "schema.sql"
ARQUIVO_BANCO = RAIZ / "data" / "calculadora.db"
PASTA_PROCESSADOS = RAIZ / "data" / "processed"

# Regras de negócio e domínios válidos -------------------------------------

DOMINIOS = {
    "tipo_ambiente": ["Dedicado", "Compartilhado"],
    "modalidade": ["Cloud", "On Premise"],
    "usa_van_bancaria": ["Sim", "Não"],
    "plano_contas_customizado": ["Sim", "Não"],
}

FAIXAS_NOTAS = [  # (descricao, limite_inferior, limite_superior)
    ("Até 1.000", 0, 1000),
    ("1.001 a 4.000", 1001, 4000),
    ("4.001 a 8.000", 4001, 8000),
    ("8.001 a 15.000", 8001, 15000),
    ("Acima de 15.000", 15001, None),
]

FASES_AIP = [  # (nome, ordem, percentual das horas totais)
    ("Project Preparation", 1, 0.10),
    ("Business Blueprint", 2, 0.20),
    ("Project Realization", 3, 0.35),
    ("Final Preparation", 4, 0.25),
    ("Go-Live and Support", 5, 0.10),
]

PORTES = [  # (porte, usuarios_min, usuarios_max)
    ("Pequeno (até 20 usuários)", 1, 20),
    ("Médio (21 a 50 usuários)", 21, 50),
    ("Grande (acima de 50 usuários)", 51, None),
]

FAIXAS_VALIDAS = {  # coluna: (mínimo, máximo)
    "numero_usuarios": (1, 1000),
    "numero_filiais": (1, 200),
    "qtd_addons": (0, 30),
    "qtd_modulos": (1, 6),
    "complexidade_importacao": (1, 10),
    "notas_mensal_num": (0, 1_000_000),
    "horas_totais_implantacao": (1, 10_000),
}

MESES = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho",
         "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]


# 1. EXTRAÇÃO ---------------------------------------------------------------

def extrair() -> pd.DataFrame:
    return pd.read_csv(ARQUIVO_FONTE, encoding="utf-8")


# 2. LIMPEZA ----------------------------------------------------------------

def limpar(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Valida os registros e separa os rejeitados, com o motivo da rejeição."""
    relatorio = {"registros_extraidos": int(len(df))}
    df = df.copy()

    # Padronização de texto (espaços extras)
    for col in df.columns:
        if pd.api.types.is_string_dtype(df[col]):
            df[col] = df[col].astype(str).str.strip()

    motivos = pd.Series("", index=df.index)

    # Nulos
    nulos = df.isna().any(axis=1)
    motivos[nulos] += "valor nulo; "

    # Duplicados pela chave do projeto
    duplicados = df.duplicated(subset=["projeto_id"], keep="first")
    motivos[duplicados] += "projeto duplicado; "

    # Domínios das variáveis categóricas
    for col, validos in DOMINIOS.items():
        invalidos = ~df[col].isin(validos)
        motivos[invalidos] += f"{col} fora do domínio; "

    # Faixas válidas das variáveis numéricas
    for col, (minimo, maximo) in FAIXAS_VALIDAS.items():
        valores = pd.to_numeric(df[col], errors="coerce")
        fora = valores.isna() | (valores < minimo) | (valores > maximo)
        motivos[fora] += f"{col} fora da faixa; "

    # Data válida
    datas = pd.to_datetime(df["data_proposta"], errors="coerce", format="%Y-%m-%d")
    motivos[datas.isna()] += "data inválida; "

    rejeitados = df[motivos != ""].assign(motivo_rejeicao=motivos[motivos != ""])
    validos = df[motivos == ""].copy()

    relatorio["registros_rejeitados"] = int(len(rejeitados))
    relatorio["registros_validos"] = int(len(validos))
    return validos, rejeitados, relatorio


# 3. TRANSFORMAÇÃO ------------------------------------------------------------

def _id_faixa_notas(valor: int) -> int:
    for i, (_, inferior, superior) in enumerate(FAIXAS_NOTAS, start=1):
        if valor >= inferior and (superior is None or valor <= superior):
            return i
    raise ValueError(valor)


def _sk_porte(usuarios: int) -> int:
    for i, (_, minimo, maximo) in enumerate(PORTES, start=1):
        if usuarios >= minimo and (maximo is None or usuarios <= maximo):
            return i
    raise ValueError(usuarios)


def transformar(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Monta as tabelas da camada operacional e do Data Warehouse."""
    t = {}

    # Tabelas de domínio (OLTP)
    t["tipo_ambiente"] = pd.DataFrame(
        {"id_tipo_ambiente": [1, 2], "descricao": DOMINIOS["tipo_ambiente"]})
    t["modalidade"] = pd.DataFrame(
        {"id_modalidade": [1, 2], "descricao": DOMINIOS["modalidade"]})
    t["faixa_volume_notas"] = pd.DataFrame(
        [(i, d, inf, sup) for i, (d, inf, sup) in enumerate(FAIXAS_NOTAS, start=1)],
        columns=["id_faixa", "descricao", "limite_inferior", "limite_superior"])
    t["fase_aip"] = pd.DataFrame(
        [(i, n, o, p) for i, (n, o, p) in enumerate(FASES_AIP, start=1)],
        columns=["id_fase", "nome", "ordem", "percentual_horas"])

    mapa_amb = dict(zip(t["tipo_ambiente"].descricao, t["tipo_ambiente"].id_tipo_ambiente))
    mapa_mod = dict(zip(t["modalidade"].descricao, t["modalidade"].id_modalidade))
    sim_nao = {"Sim": 1, "Não": 0}

    projeto = pd.DataFrame({
        "id_projeto": df["projeto_id"],
        "data_proposta": df["data_proposta"],
        "numero_usuarios": df["numero_usuarios"].astype(int),
        "numero_filiais": df["numero_filiais"].astype(int),
        "id_tipo_ambiente": df["tipo_ambiente"].map(mapa_amb),
        "id_modalidade": df["modalidade"].map(mapa_mod),
        "usa_van_bancaria": df["usa_van_bancaria"].map(sim_nao),
        "qtd_addons": df["qtd_addons"].astype(int),
        "plano_contas_customizado": df["plano_contas_customizado"].map(sim_nao),
        "qtd_modulos": df["qtd_modulos"].astype(int),
        "complexidade_importacao": df["complexidade_importacao"].astype(int),
        "notas_mensal": df["notas_mensal_num"].astype(int),
        "id_faixa": df["notas_mensal_num"].astype(int).map(_id_faixa_notas),
        "horas_totais_implantacao": df["horas_totais_implantacao"].astype(float),
    })
    t["projeto"] = projeto

    # Dimensões do Data Warehouse
    datas = pd.to_datetime(projeto["data_proposta"]).drop_duplicates().sort_values()
    t["dw_dim_tempo"] = pd.DataFrame({
        "sk_tempo": datas.dt.strftime("%Y%m%d").astype(int),
        "data": datas.dt.strftime("%Y-%m-%d"),
        "ano": datas.dt.year,
        "semestre": (datas.dt.month > 6).astype(int) + 1,
        "trimestre": datas.dt.quarter,
        "mes": datas.dt.month,
        "nome_mes": datas.dt.month.map(lambda m: MESES[m - 1]),
    })
    t["dw_dim_ambiente"] = t["tipo_ambiente"].rename(
        columns={"id_tipo_ambiente": "sk_ambiente", "descricao": "tipo_ambiente"})
    t["dw_dim_modalidade"] = t["modalidade"].rename(
        columns={"id_modalidade": "sk_modalidade", "descricao": "modalidade"})
    t["dw_dim_porte"] = pd.DataFrame(
        [(i, p, mn, mx) for i, (p, mn, mx) in enumerate(PORTES, start=1)],
        columns=["sk_porte", "porte", "usuarios_min", "usuarios_max"])
    t["dw_dim_faixa_notas"] = pd.DataFrame(
        [(i, d, i) for i, (d, _, _) in enumerate(FAIXAS_NOTAS, start=1)],
        columns=["sk_faixa_notas", "faixa", "ordem"])
    combinacoes = [(v, p) for v in ["Sim", "Não"] for p in ["Sim", "Não"]]
    t["dw_dim_indicadores"] = pd.DataFrame(
        [(i, v, p) for i, (v, p) in enumerate(combinacoes, start=1)],
        columns=["sk_indicadores", "usa_van_bancaria", "plano_contas_customizado"])
    t["dw_dim_fase"] = t["fase_aip"].rename(columns={"id_fase": "sk_fase", "nome": "fase"})

    mapa_ind = {(v, p): i for i, (v, p) in enumerate(combinacoes, start=1)}

    # Fato 1  um registro por projeto
    fato = pd.DataFrame({
        "id_projeto": projeto["id_projeto"],
        "sk_tempo": pd.to_datetime(projeto["data_proposta"]).dt.strftime("%Y%m%d").astype(int),
        "sk_ambiente": projeto["id_tipo_ambiente"],
        "sk_modalidade": projeto["id_modalidade"],
        "sk_porte": projeto["numero_usuarios"].map(_sk_porte),
        "sk_faixa_notas": projeto["id_faixa"],
        "sk_indicadores": [mapa_ind[(v, p)] for v, p in
                           zip(df["usa_van_bancaria"], df["plano_contas_customizado"])],
        "numero_usuarios": projeto["numero_usuarios"],
        "numero_filiais": projeto["numero_filiais"],
        "qtd_addons": projeto["qtd_addons"],
        "qtd_modulos": projeto["qtd_modulos"],
        "complexidade_importacao": projeto["complexidade_importacao"],
        "notas_mensal": projeto["notas_mensal"],
        "horas_totais_implantacao": projeto["horas_totais_implantacao"],
    })
    t["dw_fato_projeto"] = fato

    # Fato 2  um registro por projeto e fase (rateio pela metodologia SAP AIP)
    linhas = []
    for sk_fase, (_, _, percentual) in enumerate(FASES_AIP, start=1):
        parte = fato[["id_projeto", "sk_tempo", "sk_ambiente", "sk_modalidade", "sk_porte"]].copy()
        parte["sk_fase"] = sk_fase
        parte["horas_fase"] = (fato["horas_totais_implantacao"] * percentual).round(2)
        linhas.append(parte)
    t["dw_fato_horas_fase"] = pd.concat(linhas, ignore_index=True)[
        ["id_projeto", "sk_fase", "sk_tempo", "sk_ambiente", "sk_modalidade", "sk_porte", "horas_fase"]]

    return t


# 4. CARGA ------------------------------------------------------------------

ORDEM_CARGA = [
    "tipo_ambiente", "modalidade", "faixa_volume_notas", "fase_aip", "projeto",
    "dw_dim_tempo", "dw_dim_ambiente", "dw_dim_modalidade", "dw_dim_porte",
    "dw_dim_faixa_notas", "dw_dim_indicadores", "dw_dim_fase",
    "dw_fato_projeto", "dw_fato_horas_fase",
]


def carregar(tabelas: dict[str, pd.DataFrame]) -> dict:
    """Atualização total: recria o banco e insere todas as tabelas."""
    if ARQUIVO_BANCO.exists():
        ARQUIVO_BANCO.unlink()

    con = sqlite3.connect(ARQUIVO_BANCO)
    try:
        con.executescript(ARQUIVO_SCHEMA.read_text(encoding="utf-8"))
        con.execute("PRAGMA foreign_keys = ON;")
        for nome in ORDEM_CARGA:
            df = tabelas[nome].astype(object).where(tabelas[nome].notna(), None)
            colunas = ", ".join(df.columns)
            marcadores = ", ".join("?" for _ in df.columns)
            con.executemany(f"INSERT INTO {nome} ({colunas}) VALUES ({marcadores})",
                            df.itertuples(index=False, name=None))
        con.commit()

        # Conferência de integridade após a carga
        violacoes_fk = con.execute("PRAGMA foreign_key_check;").fetchall()
        contagens = {nome: con.execute(f"SELECT COUNT(*) FROM {nome}").fetchone()[0]
                     for nome in ORDEM_CARGA}
        soma_fato = con.execute(
            "SELECT ROUND(SUM(horas_totais_implantacao), 1) FROM dw_fato_projeto").fetchone()[0]
        soma_fases = con.execute(
            "SELECT ROUND(SUM(horas_fase), 1) FROM dw_fato_horas_fase").fetchone()[0]
        con.execute("VACUUM;")
    finally:
        con.close()

    return {
        "violacoes_chave_estrangeira": len(violacoes_fk),
        "linhas_por_tabela": contagens,
        "soma_horas_fato_projeto": soma_fato,
        "soma_horas_fato_fases": soma_fases,
    }


def main() -> None:
    inicio = datetime.now()

    bruto = extrair()
    validos, rejeitados, relatorio = limpar(bruto)
    tabelas = transformar(validos)
    relatorio.update(carregar(tabelas))

    PASTA_PROCESSADOS.mkdir(parents=True, exist_ok=True)
    rejeitados.to_csv(PASTA_PROCESSADOS / "registros_rejeitados.csv", index=False)
    relatorio["executado_em"] = inicio.strftime("%Y-%m-%d %H:%M:%S")
    (PASTA_PROCESSADOS / "relatorio_etl.json").write_text(
        json.dumps(relatorio, ensure_ascii=False, indent=2), encoding="utf-8")

    # Reconciliação com a fonte (Pegetti, 2021)
    assert relatorio["registros_validos"] == relatorio["linhas_por_tabela"]["dw_fato_projeto"]
    assert relatorio["violacoes_chave_estrangeira"] == 0

    print(json.dumps(relatorio, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
