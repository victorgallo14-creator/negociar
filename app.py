import streamlit as st
import pandas as pd
import plotly.express as px
from fpdf import FPDF

# -----------------------------------------
# CONFIGURAÇÃO DA PÁGINA
# -----------------------------------------

st.set_page_config(
    page_title="Sistema Analítico de Folha Municipal",
    page_icon="🏛️",
    layout="wide"
)

# -----------------------------------------
# CSS
# -----------------------------------------

st.markdown("""
<style>

.block-container {
    padding-top: 2rem;
}

.stMetric {
    background-color:#f8f9fa;
    padding:10px;
    border-radius:10px;
}

[data-testid="stSidebar"] {
    background-color:#f3f3f3;
}

</style>
""", unsafe_allow_html=True)

# -----------------------------------------
# FUNÇÕES AUXILIARES
# -----------------------------------------

def moeda(valor):
    try:
        return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return "R$ 0,00"


def limpar_moeda(coluna):

    return (
        coluna.astype(str)
        .str.replace(".", "", regex=False)
        .str.replace(",", ".", regex=False)
        .astype(float)
    )


@st.cache_data
def carregar_dados(detalhe, holerite):

    df_detalhe = pd.read_csv(
        detalhe,
        sep="|",
        encoding="latin1",
        dtype={"Matrícula": str}
    )

    df_holerite = pd.read_csv(
        holerite,
        sep="|",
        encoding="latin1",
        dtype={"Matrícula": str}
    )

    if "Valor" in df_holerite.columns:
        df_holerite["Valor"] = limpar_moeda(df_holerite["Valor"])

    if "Salário Bruto" in df_detalhe.columns:
        df_detalhe["Salário Bruto"] = limpar_moeda(df_detalhe["Salário Bruto"])

    return df_detalhe, df_holerite


def gerar_pdf(texto):

    pdf = FPDF()
    pdf.add_page()

    pdf.set_font("Arial", size=12)

    for linha in texto.split("\n"):
        pdf.cell(0,8,linha,ln=True)

    return pdf.output(dest="S").encode("latin1")

# -----------------------------------------
# SIDEBAR
# -----------------------------------------

st.sidebar.title("🏛️ Sistema de Análise de Folha")

st.sidebar.header("Entrada de Dados")

file_detalhe = st.sidebar.file_uploader(
    "Arquivo Detalhe Funcionários",
    type="csv"
)

file_holerite = st.sidebar.file_uploader(
    "Arquivo Holerite",
    type="csv"
)

# -----------------------------------------
# CARREGAR DADOS
# -----------------------------------------

if file_detalhe and file_holerite:

    df_detalhe, df_holerite = carregar_dados(
        file_detalhe,
        file_holerite
    )

    st.sidebar.success("Arquivos carregados com sucesso")

    # -----------------------------------------
    # ABAS
    # -----------------------------------------

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Visão Geral",
        "Secretarias",
        "Consulta Holerite",
        "Simulador",
        "Auxílio Alimentação"
    ])

    # -----------------------------------------
    # VISÃO GERAL
    # -----------------------------------------

    with tab1:

        st.title("📊 Visão Geral da Folha")

        total_servidores = df_detalhe["Matrícula"].nunique()
        custo_total = df_detalhe["Salário Bruto"].sum()
        media = df_detalhe["Salário Bruto"].mean()

        col1, col2, col3 = st.columns(3)

        col1.metric(
            "Servidores",
            total_servidores
        )

        col2.metric(
            "Custo Mensal",
            moeda(custo_total)
        )

        col3.metric(
            "Média Salarial",
            moeda(media)
        )

        st.divider()

        if "Secretaria" in df_detalhe.columns:

            grupo = df_detalhe.groupby("Secretaria")[
                "Salário Bruto"
            ].sum().reset_index()

            fig = px.bar(
                grupo,
                x="Secretaria",
                y="Salário Bruto",
                title="Custo por Secretaria"
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )

    # -----------------------------------------
    # SECRETARIAS
    # -----------------------------------------

    with tab2:

        st.title("🏢 Análise por Secretaria")

        if "Secretaria" in df_detalhe.columns:

            secretarias = sorted(
                df_detalhe["Secretaria"].dropna().unique()
            )

            secretaria = st.selectbox(
                "Selecione a secretaria",
                secretarias
            )

            dados = df_detalhe[
                df_detalhe["Secretaria"] == secretaria
            ]

            st.metric(
                "Servidores",
                dados["Matrícula"].nunique()
            )

            st.metric(
                "Custo",
                moeda(dados["Salário Bruto"].sum())
            )

            st.dataframe(dados)

    # -----------------------------------------
    # CONSULTA HOLERITE
    # -----------------------------------------

    with tab3:

        st.title("🔎 Consulta de Holerite")

        matricula = st.text_input(
            "Digite a matrícula"
        )

        if matricula:

            dados = df_holerite[
                df_holerite["Matrícula"] == matricula
            ]

            if dados.empty:

                st.warning("Matrícula não encontrada")

            else:

                st.dataframe(dados)

                total = dados["Valor"].sum()

                st.metric(
                    "Total do Holerite",
                    moeda(total)
                )

    # -----------------------------------------
    # SIMULADOR
    # -----------------------------------------

    with tab4:

        st.title("📈 Simulador de Reajuste Salarial")

        reajuste = st.slider(
            "Percentual de reajuste (%)",
            0.0,
            30.0,
            5.0
        )

        fator = 1 + reajuste / 100

        df_simulado = df_detalhe.copy()

        df_simulado["Salário Simulado"] = (
            df_simulado["Salário Bruto"] * fator
        )

        custo_atual = df_detalhe["Salário Bruto"].sum()
        custo_novo = df_simulado["Salário Simulado"].sum()

        impacto = custo_novo - custo_atual

        col1, col2, col3 = st.columns(3)

        col1.metric(
            "Custo Atual",
            moeda(custo_atual)
        )

        col2.metric(
            "Custo Simulado",
            moeda(custo_novo)
        )

        col3.metric(
            "Impacto",
            moeda(impacto)
        )

    # -----------------------------------------
    # AUXÍLIO ALIMENTAÇÃO
    # -----------------------------------------

    with tab5:

        st.title("🍽️ Auxílio Alimentação")

        eventos = df_holerite[
            df_holerite["Evento"].str.contains(
                "ALIMENT",
                case=False,
                na=False
            )
        ]

        if eventos.empty:

            st.warning(
                "Nenhum evento de auxílio encontrado"
            )

        else:

            total = eventos["Valor"].sum()

            st.metric(
                "Custo Total",
                moeda(total)
            )

            fig = px.histogram(
                eventos,
                x="Valor",
                nbins=30,
                title="Distribuição do Auxílio"
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )

    # -----------------------------------------
    # RELATÓRIO
    # -----------------------------------------

    st.sidebar.divider()

    if st.sidebar.button("Gerar Relatório PDF"):

        texto = f"""
RELATÓRIO DA FOLHA

Servidores: {total_servidores}
Custo Mensal: {moeda(custo_total)}
Média Salarial: {moeda(media)}
"""

        pdf = gerar_pdf(texto)

        st.sidebar.download_button(
            "Baixar PDF",
            pdf,
            "relatorio_folha.pdf"
        )

else:

    st.title("🏛️ Sistema de Análise de Folha Municipal")

    st.info(
        "Envie os arquivos de Detalhe de Funcionários e Holerite para iniciar."
    )
