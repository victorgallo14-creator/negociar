import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import io

# Tentar importar fpdf para geração do PDF
try:
    from fpdf import FPDF
    HAS_FPDF = True
except ImportError:
    HAS_FPDF = False

# Configuração inicial da página
st.set_page_config(
    page_title="Simulador Folha de Pagamento - Prefeitura",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilização básica via CSS
st.markdown("""
    <style>
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #f8f9fa;
        border-radius: 4px 4px 0px 0px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #e6f2ff;
        border-bottom: 2px solid #1f77b4;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

# --- FUNÇÕES DE SUPORTE ---

def clean_currency_series(series):
    def clean_val(x):
        x = str(x).strip()
        if pd.isna(x) or x == 'nan' or x == '': return 0.0
        if ',' in x and '.' in x:
            if x.rfind(',') > x.rfind('.'): return x.replace('.', '').replace(',', '.')
            else: return x.replace(',', '')
        elif ',' in x: return x.replace(',', '.')
        return x
    return pd.to_numeric(series.apply(clean_val), errors='coerce').fillna(0)

def limpar_eventos_holerite(df):
    df_limpo = df.copy()
    df_limpo = df_limpo[~df_limpo['Evento'].str.contains('Salario Bruto|Salario Líquido|Salario Liquido', case=False, na=False)]
    mask_lixo = (df_limpo['Evento'].str.contains('Outros Descontos', case=False, na=False)) & (df_limpo['Valor'] > 0)
    df_limpo = df_limpo[~mask_lixo]
    return df_limpo

def formata_moeda(val):
    return f"R$ {val:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

@st.cache_data
def load_data(file_detalhe, file_holerite, file_holerite_2=None):
    try:
        df_detalhe = pd.read_csv(file_detalhe, sep='|', dtype={'Matrícula': str}, encoding='latin1')
        df_holerite = pd.read_csv(file_holerite, sep='|', dtype={'Matrícula': str}, encoding='latin1')

        if 'Salário Bruto' in df_detalhe.columns:
            df_detalhe['Salário Bruto'] = clean_currency_series(df_detalhe['Salário Bruto'])
        if 'Valor' in df_holerite.columns:
            df_holerite['Valor'] = clean_currency_series(df_holerite['Valor'])

        cruzamento_ativo = False

        if file_holerite_2 is not None:
            df_holerite_2 = pd.read_csv(file_holerite_2, sep='|', dtype={'Matrícula': str}, encoding='latin1')
            if 'Valor' in df_holerite_2.columns:
                df_holerite_2['Valor'] = clean_currency_series(df_holerite_2['Valor'])
            
            matriculas_mes2 = df_holerite_2['Matrícula'].unique()
            df_holerite_comuns = df_holerite[df_holerite['Matrícula'].isin(matriculas_mes2)]
            df_holerite_novos = df_holerite[~df_holerite['Matrícula'].isin(matriculas_mes2)]
            
            eventos_mes2 = df_holerite_2[['Matrícula', 'Evento']].drop_duplicates()
            df_holerite = pd.concat([df_holerite_comuns.merge(eventos_mes2, on=['Matrícula', 'Evento'], how='inner'), df_holerite_novos], ignore_index=True)
            cruzamento_ativo = True

            holerite_limpo = limpar_eventos_holerite(df_holerite)
            bruto_padrao = holerite_limpo[holerite_limpo['Valor'] > 0].groupby('Matrícula')['Valor'].sum().reset_index(name='Novo_Bruto')
            df_detalhe = df_detalhe.merge(bruto_padrao, on='Matrícula', how='left')
            df_detalhe['Salário Bruto'] = df_detalhe['Novo_Bruto'].fillna(df_detalhe['Salário Bruto'])

        df_detalhe_mensal = df_detalhe[df_detalhe['Tipo Folha'].astype(str).str.contains('Mensal', case=False, na=False)]
        df_holerite_mensal = df_holerite[df_holerite['Tipo de Folha'].astype(str).str.contains('Mensal', case=False, na=False)]

        return df_detalhe_mensal, df_holerite_mensal, df_detalhe, df_holerite, cruzamento_ativo
    except Exception as e:
        st.error(f"Erro no processamento: {e}")
        return None, None, None, None, False

# --- LOGICA PRINCIPAL ---

st.title("🏛️ Sistema Estratégico de Folha de Pagamento")

st.sidebar.header("📥 Entrada de Dados")
f_det = st.sidebar.file_uploader("1. Detalhe Funcionários (CSV)", type=['csv'])
f_hol = st.sidebar.file_uploader("2. Holerite Referência (CSV)", type=['csv'])
f_comp = st.sidebar.file_uploader("3. Comparação (Opcional)", type=['csv'])

if f_det and f_hol:
    dados = load_data(f_det, f_hol, f_comp)
    
    if dados[0] is not None:
        df_detalhe, df_holerite, df_detalhe_full, df_holerite_full, cruzamento_ativo = dados
        
        # Correção do Unpacking das Abas (5 variáveis para 5 títulos)
        tab_geral, tab_sec, tab_holerite, tab_simulador, tab_auxilio = st.tabs([
            "📊 Visão Geral", "🏢 Análise por Secretaria", "📄 Consulta de Holerite", 
            "📈 Simulador de Negociação", "🍎 Negociação de Auxílio"
        ])

        # Extração de proventos únicos para uso em várias abas
        df_hol_limpo_global = limpar_eventos_holerite(df_holerite)
        proventos_unicos = sorted(df_hol_limpo_global[df_hol_limpo_global['Valor'] > 0]['Evento'].unique().tolist())

        with tab_geral:
            st.header("Visão Global do Município")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Servidores Ativos", f"{df_detalhe['Matrícula'].nunique():,}".replace(',', '.'))
            c2.metric("Custo Total Mensal", formata_moeda(df_detalhe['Salário Bruto'].sum()))
            c3.metric("Média Salarial", formata_moeda(df_detalhe['Salário Bruto'].mean()))
            c4.metric("Maior Salário", formata_moeda(df_detalhe['Salário Bruto'].max()))
            
            # Gráficos Simples
            col_g1, col_g2 = st.columns(2)
            with col_g1:
                if 'Escolaridade' in df_detalhe.columns:
                    fig_esc = px.pie(df_detalhe, names='Escolaridade', hole=0.4, title="Escolaridade")
                    st.plotly_chart(fig_esc, use_container_width=True)
            with col_g2:
                if 'Cargo' in df_detalhe.columns:
                    top_cargos = df_detalhe['Cargo'].value_counts().head(10).reset_index()
                    fig_car = px.bar(top_cargos, x='count', y='Cargo', orientation='h', title="Top 10 Cargos")
                    st.plotly_chart(fig_car, use_container_width=True)

        with tab_sec:
            st.header("Análise por Secretaria")
            if 'Secretaria' in df_detalhe.columns:
                sec_res = df_detalhe.groupby('Secretaria')['Salário Bruto'].sum().reset_index().sort_values('Salário Bruto', ascending=False)
                fig_sec = px.bar(sec_res, x='Secretaria', y='Salário Bruto', color='Salário Bruto', title="Custo por Secretaria")
                st.plotly_chart(fig_sec, use_container_width=True)

        with tab_holerite:
            st.header("Consulta de Holerite")
            busca = st.selectbox("Selecione o servidor:", sorted(df_detalhe_full['Nome'].dropna().unique()))
            if busca:
                serv = df_detalhe_full[df_detalhe_full['Nome'] == busca].iloc[0]
                st.subheader(f"👤 {serv['Nome']} ({serv['Matrícula']})")
                st.info(f"**Cargo:** {serv['Cargo']} | **Secretaria:** {serv.get('Secretaria', 'N/A')}")
                
                evs = df_holerite_full[df_holerite_full['Matrícula'] == serv['Matrícula']]
                st.dataframe(limpar_eventos_holerite(evs)[['Evento', 'Valor']], use_container_width=True)

        with tab_simulador:
            st.header("📈 Simulador de Impacto Global")
            perc = st.slider("Aumento Salarial (%)", 0.0, 20.0, 0.0, 0.5)
            custo_atual = df_detalhe['Salário Bruto'].sum()
            impacto = custo_atual * (perc / 100)
            
            st.metric("Impacto Mensal", formata_moeda(impacto))
            st.error(f"Impacto Anual Projetado (13.3 meses): {formata_moeda(impacto * 13.3)}")

        with tab_auxilio:
            st.header("🍎 Negociação Específica de Auxílio")
            st.markdown("Análise de impacto por cargo exclusivamente para benefícios de alimentação.")

            # Filtro inteligente de rubricas de auxílio
            opcoes_va = [r for r in proventos_unicos if any(k in r.upper() for k in ['ALIMENTA', 'REFEICAO', 'VALE'])]
            rubrica_sel = st.selectbox("Escolha a rubrica do Auxílio:", proventos_unicos, index=proventos_unicos.index(opcoes_va[0]) if opcoes_va else 0)

            # Cruzamento Holerite + Cadastro
            df_va = df_holerite[df_holerite['Evento'].str.upper() == rubrica_sel.upper()]
            df_va_cargo = df_va.merge(df_detalhe[['Matrícula', 'Cargo']], on='Matrícula', how='inner')

            if df_va_cargo.empty:
                st.warning("Nenhum dado encontrado para esta rubrica.")
            else:
                with st.container(border=True):
                    c_sim1, c_sim2 = st.columns(2)
                    with c_sim1:
                        modo = st.radio("Ajuste por:", ["Valor Fixo (Soma)", "Percentual (%)"], horizontal=True)
                    with c_sim2:
                        val_adj = st.number_input("Quanto aumentar?", min_value=0.0, value=50.0)

                # Agrupamento e Cálculo
                resumo = df_va_cargo.groupby(['Cargo', 'Valor']).agg(Qtd=('Matrícula', 'count')).reset_index()
                if modo == "Valor Fixo (Soma)":
                    resumo['Novo Valor'] = resumo['Valor'] + val_adj
                else:
                    resumo['Novo Valor'] = resumo['Valor'] * (1 + (val_adj / 100))

                resumo['Impacto Mensal'] = (resumo['Novo Valor'] - resumo['Valor']) * resumo['Qtd']
                
                st.subheader("Tabela de Negociação por Cargo")
                view_res = resumo.copy().sort_values('Impacto Mensal', ascending=False)
                for col in ['Valor', 'Novo Valor', 'Impacto Mensal']:
                    view_res[col] = view_res[col].apply(formata_moeda)
                
                st.dataframe(view_res, use_container_width=True, hide_index=True)
                
                total_va = resumo['Impacto Mensal'].sum()
                st.metric("Impacto Mensal Total da Proposta", formata_moeda(total_va))

else:
    st.info("👈 Por favor, carregue os arquivos CSV para começar.")
