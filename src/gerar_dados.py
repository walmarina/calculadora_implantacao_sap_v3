"""
Geração da fonte de dados sintética de projetos de implantação do SAP Business One.

Este script reproduz exatamente a base construída na 1ª etapa do Projeto Integrador
(notebook notebooks/01_analise_exploratoria_etapa1.ipynb): mesma semente aleatória,
mesmas variáveis, mesma ordem de geração e mesmos pesos da variável alvo.

A única novidade da 2ª etapa é a coluna data_proposta, criada com um gerador
aleatório independente (semente própria), para alimentar a dimensão tempo do
Data Warehouse sem alterar nenhum valor da base original.

Saída: data/raw/projetos_implantacao.csv  (simula a exportação dos handovers
técnico-comerciais, que é a fonte de dados do processo ETL)

Execução:  python src/gerar_dados.py
"""

from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
ARQUIVO_SAIDA = RAIZ / "data" / "raw" / "projetos_implantacao.csv"

SEMENTE_ETAPA1 = 42      # semente usada na 1ª etapa (não alterar)
SEMENTE_DATAS = 2026     # semente independente, usada só para data_proposta
N_PROJETOS = 300


def gerar_base(n: int = N_PROJETOS) -> pd.DataFrame:
    """Gera a base exatamente como no notebook da 1ª etapa."""
    np.random.seed(SEMENTE_ETAPA1)

    df = pd.DataFrame({
        "projeto_id": [f"PRJ{1000 + i}" for i in range(n)],
        "numero_usuarios": np.random.randint(3, 90, n),
        "numero_filiais": np.random.randint(1, 12, n),
        "tipo_ambiente": np.random.choice(["Dedicado", "Compartilhado"], n, p=[0.4, 0.6]),
        "modalidade": np.random.choice(["Cloud", "On Premise"], n, p=[0.7, 0.3]),
        "usa_van_bancaria": np.random.choice(["Sim", "Não"], n, p=[0.35, 0.65]),
        "qtd_addons": np.random.randint(0, 7, n),
        "plano_contas_customizado": np.random.choice(["Sim", "Não"], n, p=[0.45, 0.55]),
        "qtd_modulos": np.random.randint(1, 7, n),
        "complexidade_importacao": np.random.randint(1, 11, n),
    })

    # Faixa de volume de notas fiscais, mesmo padrão de faixas do handover real
    notas_mensal = np.random.randint(50, 16000, n)
    faixas = pd.cut(
        notas_mensal,
        bins=[0, 1000, 4000, 8000, 15000, np.inf],
        labels=["Até 1.000", "1.001 a 4.000", "4.001 a 8.000",
                "8.001 a 15.000", "Acima de 15.000"],
    )
    df["volume_notas_mensal"] = faixas.astype(str)
    df["notas_mensal_num"] = notas_mensal

    # Variável alvo (horas totais de implantação), mesmos pesos da 1ª etapa
    base = 80
    horas = (
        base
        + df["numero_usuarios"] * 1.6
        + df["numero_filiais"] * 9
        + (df["numero_usuarios"] * df["numero_filiais"]) * 0.15
        + df["qtd_addons"] * 14
        + df["qtd_modulos"] * 11
        + df["complexidade_importacao"] * 4.5
        + np.where(df["tipo_ambiente"] == "Dedicado", 18, 0)
        + np.where(df["plano_contas_customizado"] == "Sim", 22, 0)
        + np.where(df["usa_van_bancaria"] == "Sim", 12, 0)
        + df["notas_mensal_num"] * 0.003
        + np.random.normal(0, 30, n)
    )
    df["horas_totais_implantacao"] = horas.clip(lower=60).round(1)

    # Novidade da 2ª etapa: data da proposta comercial (gerador independente)
    rng_datas = np.random.default_rng(SEMENTE_DATAS)
    inicio = np.datetime64("2023-01-01")
    dias = rng_datas.integers(0, (np.datetime64("2026-06-30") - inicio).astype(int) + 1, n)
    df["data_proposta"] = pd.to_datetime(inicio + dias).strftime("%Y-%m-%d")

    return df


def main() -> None:
    df = gerar_base()
    ARQUIVO_SAIDA.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(ARQUIVO_SAIDA, index=False, encoding="utf-8")
    print(f"Base gerada com {len(df)} projetos em {ARQUIVO_SAIDA.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
