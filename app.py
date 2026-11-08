"""
Calculadora de Estimativa de Horas de Implantação de ERP
Aplicação Streamlit da 2ª etapa do Projeto Integrador

Abas
  Calculadora   estimativa de horas de um novo cliente com rateio pela SAP AIP
  Dashboard     análise exploratória interativa sobre o Data Warehouse
  Modelo        desempenho e interpretação do modelo de aprendizado de máquina
  Sobre         contexto do projeto, arquitetura e integrantes

Execução local:  streamlit run app.py
"""

import sqlite3
import sys
from contextlib import closing
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ / "src"))
import modelo as m  # noqa: E402

BANCO = RAIZ / "data" / "calculadora.db"
URL_REPOSITORIO = "https://github.com/walmarina/calculadora_implantacao_sap_v3"

# Paleta categórica validada (ordem fixa) e cores de texto
AZUL, LARANJA, VERDE_AGUA = "#2a78d6", "#eb6834", "#1baf7a"
CINZA = "#9a9893"
ORDEM_FASES = [f for f, _ in m.FASES_AIP]
ORDEM_PORTE = ["Pequeno (até 20 usuários)", "Médio (21 a 50 usuários)", "Grande (acima de 50 usuários)"]

MODULOS = ["Financeiro", "Fiscal", "Compras", "Vendas", "Estoque", "CRM"]
TIPOS_IMPORTACAO = [
    "Cadastro de itens", "Parceiros de negócio", "Saldos de estoque", "Saldos contábeis",
    "Ativo fixo", "Plano de contas", "Títulos em aberto", "Pedidos em aberto",
    "Centros de custo", "Listas de preço",
]

st.set_page_config(page_title="Calculadora de Implantação ERP", page_icon="🧮", layout="wide")


# Dados e modelo (carregados uma única vez e mantidos em cache) -----------------

@st.cache_data
def carregar_projetos() -> pd.DataFrame:
    return m.carregar_dados(BANCO)


@st.cache_data
def carregar_fases() -> pd.DataFrame:
    with closing(sqlite3.connect(BANCO)) as con:
        return pd.read_sql("SELECT * FROM vw_horas_por_fase", con)


@st.cache_resource(show_spinner="Treinando o modelo com os projetos do Data Warehouse...")
def treinar() -> dict:
    return m.treinar_e_avaliar(carregar_projetos())


def br(valor: float, casas: int = 1) -> str:
    """Formata número no padrão brasileiro (vírgula decimal, ponto de milhar)."""
    return f"{valor:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def grafico(chart: alt.Chart, altura: int = 320) -> None:
    st.altair_chart(chart.properties(height=altura), width="stretch")


projetos = carregar_projetos()
fases = carregar_fases()
resultado = treinar()
comparacao = resultado["comparacao"].set_index("modelo")
melhor = comparacao.loc[resultado["nome_melhor"]]

st.title("Calculadora de Estimativa de Horas de Implantação de ERP")
st.caption("Prova de conceito de ciência de dados aplicada ao SAP Business One · Projeto Integrador · Senac EAD")

aba_calc, aba_dash, aba_modelo, aba_sobre = st.tabs(["Calculadora", "Dashboard", "Modelo", "Sobre o projeto"])


# =============================================================================
# CALCULADORA
# =============================================================================
with aba_calc:
    st.subheader("Estimativa de esforço para um novo cliente")
    st.write("Preencha as informações do handover técnico-comercial. A estimativa é recalculada a cada alteração.")

    col_entrada, col_saida = st.columns([1, 1.15], gap="large")

    with col_entrada:
        c1, c2 = st.columns(2)
        usuarios = c1.number_input("Número de usuários (licenças)", min_value=1, max_value=500, value=25, step=1)
        filiais = c2.number_input("Número de filiais", min_value=1, max_value=100, value=3, step=1)

        c3, c4 = st.columns(2)
        addons = c3.number_input("Quantidade de add-ons", min_value=0, max_value=20, value=2, step=1,
                                 help="Soluções complementares instaladas, como TaxPlus, BankPlus e ContractPlus.")
        notas = c4.number_input("Notas fiscais emitidas por mês", min_value=0, max_value=100_000,
                                value=3000, step=100)

        modulos = st.pills("Módulos a implantar", MODULOS, selection_mode="multi",
                           default=["Financeiro", "Fiscal", "Compras", "Vendas", "Estoque"]) or []
        importacoes = st.pills("Tipos de dados a importar", TIPOS_IMPORTACAO, selection_mode="multi",
                               default=["Cadastro de itens", "Parceiros de negócio", "Saldos de estoque",
                                        "Saldos contábeis", "Plano de contas", "Títulos em aberto"]) or []

        c5, c6 = st.columns(2)
        ambiente = c5.segmented_control("Tipo de ambiente", ["Compartilhado", "Dedicado"], default="Compartilhado", required=True)
        modalidade = c6.segmented_control("Modalidade", ["Cloud", "On Premise"], default="Cloud", required=True)

        c7, c8 = st.columns(2)
        van = c7.toggle("Utiliza Van Bancária", value=True)
        plano = c8.toggle("Plano de contas customizado", value=False)

    with col_saida:
        if not modulos or not importacoes:
            st.warning("Selecione pelo menos um módulo e um tipo de dado a importar.")
        else:
            entrada = {
                "numero_usuarios": usuarios, "numero_filiais": filiais, "qtd_addons": addons,
                "qtd_modulos": len(modulos), "complexidade_importacao": len(importacoes),
                "notas_mensal": notas, "tipo_ambiente": ambiente, "modalidade": modalidade,
                "usa_van_bancaria": "Sim" if van else "Não",
                "plano_contas_customizado": "Sim" if plano else "Não",
            }
            est = m.estimar(resultado["modelo_final"], entrada, resultado["faixa_residuos_p10_p90"])

            with st.container(border=True):
                k1, k2, k3 = st.columns(3)
                k1.metric("Horas estimadas", f"{br(est['horas'], 0)} h")
                k2.metric("Faixa provável", f"{br(est['faixa_min'], 0)} a {br(est['faixa_max'], 0)} h",
                          help="Intervalo que concentrou 80% dos erros do modelo na validação cruzada (percentis 10 e 90).")
                k3.metric("Semanas de consultoria", br(est['horas'] / 40),
                          help="Equivalente para um consultor em dedicação integral (40 horas por semana).")

            df_fases = pd.DataFrame(est["fases"], columns=["Fase", "Horas"])
            df_fases["Percentual"] = [f"{p:.0%}" for _, p in m.FASES_AIP]
            barras = alt.Chart(df_fases).mark_bar(color=AZUL, cornerRadiusEnd=4, size=26).encode(
                x=alt.X("Horas:Q", title="Horas"),
                y=alt.Y("Fase:N", sort=ORDEM_FASES, title=None, axis=alt.Axis(labelLimit=200)),
                tooltip=["Fase", alt.Tooltip("Horas:Q", format=".0f"), "Percentual"],
            )
            rotulos = barras.mark_text(align="left", dx=6, color="#52514e").encode(text=alt.Text("Horas:Q", format=".0f"))
            st.markdown("**Distribuição pelas fases da metodologia SAP AIP**")
            grafico(barras + rotulos, altura=230)

            # Alerta de extrapolação (entrada fora da faixa usada no treino)
            fora = []
            for col, rotulo in [("numero_usuarios", "usuários"), ("numero_filiais", "filiais"),
                                ("qtd_addons", "add-ons"), ("notas_mensal", "notas por mês")]:
                mn, mx = projetos[col].min(), projetos[col].max()
                if not mn <= entrada[col] <= mx:
                    fora.append(f"{rotulo} (base de {mn} a {mx})")
            if fora:
                st.warning("Atenção, valor fora da faixa dos projetos usados no treino, a estimativa é menos confiável para "
                           + ", ".join(fora) + ".")

            st.caption(f"Modelo {resultado['nome_melhor']} · erro médio absoluto de {melhor.teste_MAE:.0f} horas "
                       f"no conjunto de teste · base sintética de {len(projetos)} projetos.")


# =============================================================================
# DASHBOARD
# =============================================================================
with aba_dash:
    st.subheader("Análise dos projetos de implantação")

    f1, f2, f3 = st.columns([1, 1, 1.3])
    sel_mod = f1.pills("Modalidade", ["Cloud", "On Premise"], selection_mode="multi", default=["Cloud", "On Premise"])
    sel_amb = f2.pills("Tipo de ambiente", ["Compartilhado", "Dedicado"], selection_mode="multi", default=["Compartilhado", "Dedicado"])
    sel_porte = f3.pills("Porte do cliente", ORDEM_PORTE, selection_mode="multi", default=ORDEM_PORTE,
                         format_func=lambda p: p.split(" (")[0],
                         help="Pequeno até 20 usuários, Médio de 21 a 50 e Grande acima de 50.")

    filtro = (projetos["modalidade"].isin(sel_mod) & projetos["tipo_ambiente"].isin(sel_amb)
              & projetos["porte"].isin(sel_porte))
    dados = projetos[filtro]
    dados_fases = fases[fases["id_projeto"].isin(dados["id_projeto"])]

    if dados.empty:
        st.info("Nenhum projeto atende aos filtros selecionados.")
    else:
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Projetos", f"{len(dados)}")
        k2.metric("Média de horas", f"{br(dados.horas_totais_implantacao.mean(), 0)} h")
        k3.metric("Mediana de horas", f"{br(dados.horas_totais_implantacao.median(), 0)} h")
        k4.metric("Usuários por projeto (média)", f"{dados.numero_usuarios.mean():.0f}")

        g1, g2 = st.columns(2, gap="large")
        with g1:
            st.markdown("**Usuários e horas de implantação por modalidade**")
            grafico(alt.Chart(dados).mark_circle(size=70, opacity=0.75, stroke="white", strokeWidth=1).encode(
                x=alt.X("numero_usuarios:Q", title="Número de usuários (licenças)"),
                y=alt.Y("horas_totais_implantacao:Q", title="Horas totais", scale=alt.Scale(zero=False)),
                color=alt.Color("modalidade:N", title="Modalidade",
                                scale=alt.Scale(domain=["Cloud", "On Premise"], range=[AZUL, LARANJA])),
                tooltip=[alt.Tooltip("id_projeto", title="Projeto"), alt.Tooltip("numero_usuarios", title="Usuários"),
                         alt.Tooltip("numero_filiais", title="Filiais"),
                         alt.Tooltip("horas_totais_implantacao", title="Horas"), alt.Tooltip("modalidade", title="Modalidade")],
            ))
        with g2:
            st.markdown("**Distribuição de horas por tipo de ambiente**")
            grafico(alt.Chart(dados).mark_boxplot(size=60, color=AZUL, median={"color": "white"}).encode(
                x=alt.X("tipo_ambiente:N", title=None, sort=["Dedicado", "Compartilhado"], axis=alt.Axis(labelAngle=0)),
                y=alt.Y("horas_totais_implantacao:Q", title="Horas totais", scale=alt.Scale(zero=False)),
            ))

        g3, g4 = st.columns(2, gap="large")
        with g3:
            st.markdown("**Média de horas por quantidade de add-ons**")
            media_addon = dados.groupby("qtd_addons", as_index=False).agg(
                horas=("horas_totais_implantacao", "mean"), projetos=("id_projeto", "count"))
            grafico(alt.Chart(media_addon).mark_bar(color=AZUL, cornerRadiusEnd=4, size=28).encode(
                x=alt.X("qtd_addons:O", title="Quantidade de add-ons", axis=alt.Axis(labelAngle=0)),
                y=alt.Y("horas:Q", title="Média de horas"),
                tooltip=[alt.Tooltip("qtd_addons", title="Add-ons"), alt.Tooltip("horas:Q", title="Média de horas", format=".0f"),
                         alt.Tooltip("projetos", title="Projetos")],
            ))
        with g4:
            st.markdown("**Média de horas por porte do cliente**")
            media_porte = dados.groupby("porte", as_index=False).agg(
                horas=("horas_totais_implantacao", "mean"), projetos=("id_projeto", "count"))
            grafico(alt.Chart(media_porte).mark_bar(color=AZUL, cornerRadiusEnd=4, size=40).encode(
                x=alt.X("porte:N", title=None, sort=ORDEM_PORTE, axis=alt.Axis(labelAngle=0, labelLimit=200)),
                y=alt.Y("horas:Q", title="Média de horas"),
                tooltip=[alt.Tooltip("porte", title="Porte"), alt.Tooltip("horas:Q", title="Média de horas", format=".0f"),
                         alt.Tooltip("projetos", title="Projetos")],
            ))

        g5, g6 = st.columns(2, gap="large")
        with g5:
            st.markdown("**Média de horas por fase da metodologia SAP AIP**")
            media_fase = dados_fases.groupby("fase", as_index=False)["horas_fase"].mean()
            grafico(alt.Chart(media_fase).mark_bar(color=AZUL, cornerRadiusEnd=4, size=26).encode(
                x=alt.X("horas_fase:Q", title="Média de horas"),
                y=alt.Y("fase:N", sort=ORDEM_FASES, title=None, axis=alt.Axis(labelLimit=200)),
                tooltip=[alt.Tooltip("fase", title="Fase"), alt.Tooltip("horas_fase:Q", title="Média de horas", format=".1f")],
            ))
        with g6:
            st.markdown("**Correlação entre as variáveis e as horas totais**")
            rotulos_corr = {"numero_usuarios": "Usuários", "numero_filiais": "Filiais", "qtd_addons": "Add-ons",
                            "qtd_modulos": "Módulos", "complexidade_importacao": "Complex. importação",
                            "notas_mensal": "Notas/mês", "horas_totais_implantacao": "Horas totais"}
            corr = dados[list(rotulos_corr)].rename(columns=rotulos_corr).corr().round(2)
            corr_longo = corr.reset_index(names="linha").melt(id_vars="linha", var_name="coluna", value_name="r")
            ordem = list(rotulos_corr.values())
            base = alt.Chart(corr_longo).encode(
                x=alt.X("coluna:N", sort=ordem, title=None, axis=alt.Axis(labelAngle=-40, labelOverlap=False, labelLimit=140)),
                y=alt.Y("linha:N", sort=ordem, title=None, axis=alt.Axis(labelLimit=160)))
            grafico(base.mark_rect(stroke="white", strokeWidth=2).encode(
                color=alt.Color("r:Q", title="r", scale=alt.Scale(domain=[-1, 0, 1], range=[LARANJA, "#f2f1ee", AZUL], interpolate="rgb")),
                tooltip=[alt.Tooltip("linha", title="Variável"), alt.Tooltip("coluna", title="Variável"),
                         alt.Tooltip("r:Q", title="Correlação")],
            ) + base.mark_text(fontSize=11, color="#0b0b0b").encode(text=alt.Text("r:Q", format=".2f")), altura=360)

        st.markdown("**Propostas por trimestre**")
        dados_tempo = dados.assign(periodo=dados["ano"].astype(str) + " T" + dados["trimestre"].astype(str))
        por_tri = dados_tempo.groupby("periodo", as_index=False).agg(
            projetos=("id_projeto", "count"), horas=("horas_totais_implantacao", "sum"))
        grafico(alt.Chart(por_tri).mark_line(color=AZUL, strokeWidth=2, point=alt.OverlayMarkDef(size=60, color=AZUL)).encode(
            x=alt.X("periodo:N", title=None, axis=alt.Axis(labelAngle=0)),
            y=alt.Y("projetos:Q", title="Quantidade de propostas"),
            tooltip=[alt.Tooltip("periodo", title="Trimestre"), alt.Tooltip("projetos", title="Propostas"),
                     alt.Tooltip("horas:Q", title="Horas vendidas", format=",.0f")],
        ), altura=260)

        with st.expander("Ver os dados filtrados"):
            st.dataframe(dados, hide_index=True)


# =============================================================================
# MODELO
# =============================================================================
with aba_modelo:
    st.subheader("Modelo de aprendizado de máquina")
    st.write(
        "Aprendizado **supervisionado**, tarefa de **regressão**. O modelo aprende, a partir dos projetos "
        "do Data Warehouse, a relação entre as características do cliente e o total de horas de implantação. "
        "Foram comparados cinco modelos com validação cruzada 5-fold em 80% da base, e o escolhido foi "
        "avaliado nos 20% restantes, que ele não viu durante a escolha."
    )

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Modelo escolhido", resultado["nome_melhor"])
    k2.metric("MAE no teste", f"{br(melhor.teste_MAE)} h", help="Erro absoluto médio das previsões.")
    k3.metric("RMSE no teste", f"{br(melhor.teste_RMSE)} h", help="Raiz do erro quadrático médio, penaliza mais os erros grandes.")
    k4.metric("R² no teste", br(melhor.teste_R2, 2), help="Parcela da variação das horas explicada pelo modelo.")

    comp = resultado["comparacao"]
    m1, m2 = st.columns(2, gap="large")
    with m1:
        st.markdown("**Erro de cada modelo na validação cruzada**")
        barras = alt.Chart(comp).mark_bar(cornerRadiusEnd=4, size=24).encode(
            x=alt.X("cv_RMSE:Q", title="RMSE médio na validação cruzada (horas)"),
            y=alt.Y("modelo:N", sort="x", title=None, axis=alt.Axis(labelLimit=250)),
            color=alt.condition(alt.datum.modelo == resultado["nome_melhor"], alt.value(AZUL), alt.value(CINZA)),
            tooltip=[alt.Tooltip("modelo", title="Modelo"), alt.Tooltip("cv_RMSE", title="RMSE (CV)"),
                     alt.Tooltip("cv_R2", title="R² (CV)")],
        )
        grafico(barras + barras.mark_text(align="left", dx=6, color="#52514e").encode(
            text=alt.Text("cv_RMSE:Q", format=".1f"), color=alt.value("#52514e")), altura=260)
    with m2:
        st.markdown("**Erro no treino e no teste (overfitting)**")
        longo = comp.melt(id_vars="modelo", value_vars=["treino_RMSE", "teste_RMSE"], var_name="conjunto", value_name="rmse")
        longo["conjunto"] = longo["conjunto"].map({"treino_RMSE": "Treino", "teste_RMSE": "Teste"})
        grafico(alt.Chart(longo).mark_bar(cornerRadiusEnd=3, size=12).encode(
            y=alt.Y("modelo:N", title=None, sort=list(comp.sort_values("cv_RMSE")["modelo"]), axis=alt.Axis(labelLimit=250)),
            yOffset=alt.YOffset("conjunto:N", sort=["Treino", "Teste"]),
            x=alt.X("rmse:Q", title="RMSE (horas)"),
            color=alt.Color("conjunto:N", title=None, sort=["Treino", "Teste"],
                            scale=alt.Scale(domain=["Treino", "Teste"], range=[AZUL, LARANJA]),
                            legend=alt.Legend(orient="top")),
            tooltip=[alt.Tooltip("modelo", title="Modelo"), alt.Tooltip("conjunto", title="Conjunto"),
                     alt.Tooltip("rmse:Q", title="RMSE", format=".1f")],
        ), altura=260)
        st.caption("A Random Forest erra pouco no treino e muito no teste, sinal de que memorizou o ruído da base.")

    m3, m4 = st.columns(2, gap="large")
    with m3:
        st.markdown("**Horas reais e previstas no conjunto de teste**")
        prev = resultado["previsoes_teste"]
        lim = [float(prev[["horas_reais", "horas_previstas"]].min().min()) - 20,
               float(prev[["horas_reais", "horas_previstas"]].max().max()) + 20]
        diagonal = alt.Chart(pd.DataFrame({"x": lim, "y": lim})).mark_line(color=CINZA, strokeDash=[6, 4]).encode(
            x=alt.X("x:Q", scale=alt.Scale(domain=lim, zero=False, nice=False)),
            y=alt.Y("y:Q", scale=alt.Scale(domain=lim, zero=False, nice=False)))
        pontos = alt.Chart(prev).mark_circle(size=70, color=AZUL, opacity=0.85, stroke="white", strokeWidth=1).encode(
            x=alt.X("horas_reais:Q", title="Horas reais", scale=alt.Scale(domain=lim, zero=False, nice=False)),
            y=alt.Y("horas_previstas:Q", title="Horas previstas", scale=alt.Scale(domain=lim, zero=False, nice=False)),
            tooltip=[alt.Tooltip("id_projeto", title="Projeto"), alt.Tooltip("horas_reais", title="Reais"),
                     alt.Tooltip("horas_previstas", title="Previstas"), alt.Tooltip("erro", title="Erro")],
        )
        grafico(diagonal + pontos, altura=340)
        st.caption("Quanto mais próximos da linha tracejada, mais precisa a previsão.")
    with m4:
        st.markdown("**Importância das variáveis**")
        imp = resultado["importancia"]
        barras = alt.Chart(imp).mark_bar(color=AZUL, cornerRadiusEnd=4, size=20).encode(
            x=alt.X("aumento_RMSE:Q", title="Aumento do RMSE ao embaralhar a variável (horas)"),
            y=alt.Y("variavel:N", sort="-x", title=None, axis=alt.Axis(labelLimit=220)),
            tooltip=[alt.Tooltip("variavel", title="Variável"), alt.Tooltip("aumento_RMSE", title="Aumento do RMSE"),
                     alt.Tooltip("desvio", title="Desvio")],
        )
        grafico(barras + barras.mark_text(align="left", dx=6, color="#52514e").encode(
            text=alt.Text("aumento_RMSE:Q", format=".1f")), altura=340)
        st.caption("Importância por permutação, calculada no conjunto de teste.")

    with st.expander("Pré-processamento, seleção de variáveis e regularização"):
        st.markdown(
            f"""
* **Entradas do modelo** {", ".join(m.ENTRADAS)}, além da variável criada `usuarios_x_filiais`.
* **Pré-processamento** One-Hot Encoding nas variáveis categóricas e padronização (StandardScaler) nas numéricas.
* **Variáveis excluídas** {"; ".join(f"`{k}` ({v})" for k, v in m.EXCLUIDAS.items())}. As horas por fase da SAP AIP
  também ficaram de fora, pois são calculadas a partir do próprio rótulo (vazamento de dados).
* **Regularização** Ridge com alpha de {br(resultado['alpha_ridge'], 2)} e Lasso com alpha de {br(resultado['alpha_lasso'], 2)},
  escolhidos por validação cruzada. O Lasso zerou o coeficiente da modalidade, indicando que ela não ajuda a prever as horas.
"""
        )
        st.dataframe(comp, hide_index=True)


# =============================================================================
# SOBRE
# =============================================================================
with aba_sobre:
    st.subheader("Sobre o projeto")
    st.markdown(
        f"""
A estimativa de horas em propostas de implantação de ERP costuma ser feita de forma empírica, com base na
experiência individual do consultor. Esta prova de conceito propõe uma estimativa orientada por dados, usando
como referência o SAP Business One e a metodologia SAP Accelerated Implementation Program (SAP AIP).

**Arquitetura da solução**

1. **Fonte de dados** base sintética de {len(projetos)} projetos, estruturada a partir das variáveis de um handover técnico-comercial real.
2. **ETL** extração, limpeza, transformação e carga em Python (`src/etl.py`).
3. **Banco de dados** camada operacional normalizada e Data Warehouse em esquema estrela, em SQLite nesta prova de conceito e especificado em MySQL 8.0 para o cenário real.
4. **Modelo** regressão supervisionada com scikit-learn (`src/modelo.py`).
5. **Visualização** esta aplicação em Streamlit, publicada no Streamlit Community Cloud.

**Limitações** os dados são sintéticos e os padrões encontrados refletem os pesos definidos na geração da base.
A abordagem precisa ser validada com dados de projetos reais antes de uso comercial.

Código-fonte e documentação em [{URL_REPOSITORIO.replace("https://", "")}]({URL_REPOSITORIO}).

**Integrantes** Daniel Vieira Bueno, Danielly Mendes Moura, Everton Glad, Gabriel Polido, Giovanna Dainezi Franci,
Luan Cunha de Farias, Tainá Lima do Nascimento e Walquiria M. N. do Nascimento.

**Disciplina** Projeto Integrador, Ciência de Dados Aplicada a Situações de Mercado · Professor Engº Jean Carlo Wagner ·
Tecnologia em Banco de Dados · Senac EAD
"""
    )
