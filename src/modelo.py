"""
Modelo de aprendizado de máquina da Calculadora de Estimativa de Horas.

Abordagem   aprendizado supervisionado, tarefa de regressão (Ferreira, 2024)
Entrada     características do cliente e do escopo, lidas do Data Warehouse
Saída       horas_totais_implantacao (valor numérico contínuo)

Etapas
  1. Carga dos dados a partir da view vw_projetos_analitico
  2. Seleção de características (exclusão de identificadores, redundâncias
     e de qualquer coluna derivada do rótulo, para evitar vazamento)
  3. Extração de característica (interação usuários × filiais)
  4. Pré-processamento (One-Hot Encoding e padronização)
  5. Treino e comparação de modelos com validação cruzada k-fold
  6. Avaliação final no conjunto de teste (MAE, MSE, RMSE e R²)
  7. Importância das variáveis por permutação (interpretabilidade)

Execução:  python src/modelo.py   (gera os relatórios na pasta models/)
"""

import json
import sqlite3
from contextlib import closing
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LassoCV, LinearRegression, RidgeCV
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import KFold, cross_val_predict, cross_validate, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, OneHotEncoder, StandardScaler

RAIZ = Path(__file__).resolve().parents[1]
ARQUIVO_BANCO = RAIZ / "data" / "calculadora.db"
PASTA_MODELOS = RAIZ / "models"

SEMENTE = 42
ALVO = "horas_totais_implantacao"

# Variáveis de entrada do modelo
NUMERICAS = [
    "numero_usuarios", "numero_filiais", "qtd_addons", "qtd_modulos",
    "complexidade_importacao", "notas_mensal",
]
CATEGORICAS = [
    "tipo_ambiente", "modalidade", "usa_van_bancaria", "plano_contas_customizado",
]
ENTRADAS = NUMERICAS + CATEGORICAS

# Colunas da view que NÃO entram no modelo, com a justificativa
EXCLUIDAS = {
    "id_projeto": "identificador, não ajuda a generalizar",
    "data_proposta": "data da proposta, sem relação causal com o esforço",
    "ano": "derivada da data da proposta",
    "trimestre": "derivada da data da proposta",
    "porte": "derivada de numero_usuarios (redundância)",
    "volume_notas_mensal": "faixa derivada de notas_mensal (redundância)",
}

FASES_AIP = [
    ("Project Preparation", 0.10),
    ("Business Blueprint", 0.20),
    ("Project Realization", 0.35),
    ("Final Preparation", 0.25),
    ("Go-Live and Support", 0.10),
]


# 1. Dados ------------------------------------------------------------------

def carregar_dados(caminho_banco: Path = ARQUIVO_BANCO) -> pd.DataFrame:
    with closing(sqlite3.connect(caminho_banco)) as con:
        return pd.read_sql("SELECT * FROM vw_projetos_analitico", con)


# 3. Extração de característica -------------------------------------------------

def adicionar_interacao(X: pd.DataFrame) -> pd.DataFrame:
    """Cria usuarios_x_filiais, combinação de duas variáveis existentes."""
    X = X.copy()
    X["usuarios_x_filiais"] = X["numero_usuarios"] * X["numero_filiais"]
    return X


# 4. Pré-processamento ---------------------------------------------------------

def _preprocessador(com_interacao: bool) -> ColumnTransformer:
    numericas = NUMERICAS + (["usuarios_x_filiais"] if com_interacao else [])
    return ColumnTransformer([
        ("numericas", StandardScaler(), numericas),
        ("categoricas", OneHotEncoder(drop="if_binary", handle_unknown="ignore"), CATEGORICAS),
    ])


def _pipeline(estimador, com_interacao: bool = True) -> Pipeline:
    etapas = []
    if com_interacao:
        etapas.append(("interacao", FunctionTransformer(adicionar_interacao)))
    etapas += [("preprocessamento", _preprocessador(com_interacao)), ("modelo", estimador)]
    return Pipeline(etapas)


def modelos_candidatos() -> dict[str, Pipeline]:
    kfold = KFold(n_splits=5, shuffle=True, random_state=SEMENTE)
    return {
        "Regressão Linear (sem interação)": _pipeline(LinearRegression(), com_interacao=False),
        "Regressão Linear": _pipeline(LinearRegression()),
        "Ridge (L2)": _pipeline(RidgeCV(alphas=np.logspace(-3, 3, 25))),
        "Lasso (L1)": _pipeline(LassoCV(alphas=np.logspace(-3, 2, 25), cv=kfold, max_iter=50_000)),
        "Random Forest": _pipeline(RandomForestRegressor(
            n_estimators=300, max_depth=8, min_samples_leaf=3, random_state=SEMENTE)),
    }


# 5 e 6. Treino, validação e avaliação ------------------------------------------

def _metricas(y_real, y_prev) -> dict:
    mse = mean_squared_error(y_real, y_prev)
    return {
        "MAE": round(float(mean_absolute_error(y_real, y_prev)), 2),
        "MSE": round(float(mse), 2),
        "RMSE": round(float(np.sqrt(mse)), 2),
        "R2": round(float(r2_score(y_real, y_prev)), 4),
    }


def treinar_e_avaliar(df: pd.DataFrame) -> dict:
    """Compara os modelos e devolve o melhor, já retreinado com toda a base."""
    X, y = df[ENTRADAS], df[ALVO]
    X_treino, X_teste, y_treino, y_teste = train_test_split(
        X, y, test_size=0.2, random_state=SEMENTE)
    kfold = KFold(n_splits=5, shuffle=True, random_state=SEMENTE)

    linhas, ajustados = [], {}
    for nome, pipe in modelos_candidatos().items():
        cv = cross_validate(pipe, X_treino, y_treino, cv=kfold,
                            scoring=("neg_mean_absolute_error", "neg_root_mean_squared_error", "r2"))
        pipe.fit(X_treino, y_treino)
        ajustados[nome] = pipe
        treino = _metricas(y_treino, pipe.predict(X_treino))
        teste = _metricas(y_teste, pipe.predict(X_teste))
        linhas.append({
            "modelo": nome,
            "cv_MAE": round(-cv["test_neg_mean_absolute_error"].mean(), 2),
            "cv_RMSE": round(-cv["test_neg_root_mean_squared_error"].mean(), 2),
            "cv_RMSE_desvio": round(cv["test_neg_root_mean_squared_error"].std(), 2),
            "cv_R2": round(cv["test_r2"].mean(), 4),
            "treino_RMSE": treino["RMSE"],
            "teste_MAE": teste["MAE"],
            "teste_MSE": teste["MSE"],
            "teste_RMSE": teste["RMSE"],
            "teste_R2": teste["R2"],
        })

    comparacao = pd.DataFrame(linhas)
    # A escolha usa a validação cruzada, e não o teste, para não enviesar a avaliação final
    nome_melhor = comparacao.sort_values("cv_RMSE").iloc[0]["modelo"]
    melhor = ajustados[nome_melhor]

    previsoes_teste = pd.DataFrame({
        "id_projeto": df.loc[X_teste.index, "id_projeto"],
        "horas_reais": y_teste,
        "horas_previstas": melhor.predict(X_teste).round(1),
    })
    previsoes_teste["erro"] = (previsoes_teste["horas_previstas"] - previsoes_teste["horas_reais"]).round(1)

    # 7. Importância por permutação no conjunto de teste
    imp = permutation_importance(melhor, X_teste, y_teste, n_repeats=30,
                                 random_state=SEMENTE, scoring="neg_root_mean_squared_error")
    importancia = pd.DataFrame({
        "variavel": ENTRADAS,
        "aumento_RMSE": imp.importances_mean.round(2),
        "desvio": imp.importances_std.round(2),
    }).sort_values("aumento_RMSE", ascending=False)

    # Faixa de incerteza a partir dos resíduos da validação cruzada (P10 a P90)
    residuos = y_treino - cross_val_predict(melhor, X_treino, y_treino, cv=kfold)
    faixa = (round(float(np.percentile(residuos, 10)), 1), round(float(np.percentile(residuos, 90)), 1))

    # Coeficientes do Lasso, para mostrar quais variáveis ele manteve
    lasso = ajustados["Lasso (L1)"]
    nomes_saida = lasso.named_steps["preprocessamento"].get_feature_names_out()
    coef_lasso = pd.DataFrame({
        "variavel": [n.split("__", 1)[1] for n in nomes_saida],
        "coeficiente": lasso.named_steps["modelo"].coef_.round(3),
    })

    # Modelo final retreinado com toda a base, usado pela calculadora
    modelo_final = modelos_candidatos()[nome_melhor].fit(X, y)

    return {
        "nome_melhor": nome_melhor,
        "modelo_final": modelo_final,
        "comparacao": comparacao,
        "previsoes_teste": previsoes_teste,
        "importancia": importancia,
        "coeficientes_lasso": coef_lasso,
        "alpha_lasso": float(lasso.named_steps["modelo"].alpha_),
        "alpha_ridge": float(ajustados["Ridge (L2)"].named_steps["modelo"].alpha_),
        "faixa_residuos_p10_p90": faixa,
        "tamanho_treino": int(len(X_treino)),
        "tamanho_teste": int(len(X_teste)),
    }


# Uso pela calculadora ------------------------------------------------------------

def estimar(modelo: Pipeline, entrada: dict, faixa=(0.0, 0.0)) -> dict:
    """Estima as horas de um novo projeto e faz o rateio pelas fases da SAP AIP."""
    horas = float(modelo.predict(pd.DataFrame([entrada])[ENTRADAS])[0])
    horas = max(horas, 60.0)
    return {
        "horas": round(horas, 0),
        "faixa_min": round(max(horas + faixa[0], 60.0), 0),
        "faixa_max": round(horas + faixa[1], 0),
        "fases": [(fase, round(horas * pct, 0)) for fase, pct in FASES_AIP],
    }


def main() -> None:
    resultado = treinar_e_avaliar(carregar_dados())
    PASTA_MODELOS.mkdir(exist_ok=True)

    resultado["comparacao"].to_csv(PASTA_MODELOS / "comparacao_modelos.csv", index=False)
    resultado["previsoes_teste"].to_csv(PASTA_MODELOS / "previsoes_teste.csv", index=False)
    resultado["importancia"].to_csv(PASTA_MODELOS / "importancia_variaveis.csv", index=False)
    resultado["coeficientes_lasso"].to_csv(PASTA_MODELOS / "coeficientes_lasso.csv", index=False)

    melhor = resultado["comparacao"].set_index("modelo").loc[resultado["nome_melhor"]]
    resumo = {
        "modelo_escolhido": resultado["nome_melhor"],
        "criterio_escolha": "menor RMSE médio na validação cruzada 5-fold (base de treino)",
        "divisao": {"treino": resultado["tamanho_treino"], "teste": resultado["tamanho_teste"]},
        "metricas_teste": {k.replace("teste_", ""): float(melhor[k])
                           for k in ["teste_MAE", "teste_MSE", "teste_RMSE", "teste_R2"]},
        "alpha_ridge": resultado["alpha_ridge"],
        "alpha_lasso": resultado["alpha_lasso"],
        "faixa_residuos_p10_p90": resultado["faixa_residuos_p10_p90"],
        "variaveis_entrada": ENTRADAS + ["usuarios_x_filiais (criada)"],
        "variaveis_excluidas": EXCLUIDAS,
    }
    (PASTA_MODELOS / "metricas.json").write_text(
        json.dumps(resumo, ensure_ascii=False, indent=2), encoding="utf-8")

    pd.set_option("display.width", 200)
    print(resultado["comparacao"].to_string(index=False))
    print(json.dumps(resumo, ensure_ascii=False, indent=2))
    print(resultado["importancia"].to_string(index=False))


if __name__ == "__main__":
    main()
