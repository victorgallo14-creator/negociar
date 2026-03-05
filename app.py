import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Configuração inicial da página
st.set_page_config(
    page_title="Simulador Folha de Pagamento - Prefeitura",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilização básica via CSS para melhorar o visual
st.markdown("""
    <style>
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #f8f9fa;
        border-radius: 4px 4px 0px 0px;
        padding-top: 10px;
        padding-bottom: 10px;
        box-shadow: 0px -1px 2px rgba(0,0,0,0.05);
    }
    .stTabs [aria-selected="true"] {
        background-color: #e6f2ff;
        border-bottom: 2px solid #1f77b4;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

# Função robusta para limpar e converter texto em valores monetários
def clean_currency_series(series):
    def clean_val(x):
        x = str(x).strip()
        if pd.isna(x) or x == 'nan' or x == '':
            return 0.0
        if ',' in x and '.' in x:
            if x.rfind(',') > x.rfind('.'):  # Formato BR: 1.234,56
                return x.replace('.', '').replace(',', '.')
            else:  # Formato US: 1,234.56
                return x.replace(',', '')
        elif ',' in x:
            return x.replace(',', '.')
        return x
    return pd.to_numeric(series.apply(clean_val), errors='coerce').fillna(0)

# NOVA FUNÇÃO CENTRAL: Limpeza Inteligente baseada nos padrões exatos da Prefeitura
def limpar_eventos_holerite(df):
    df_limpo = df.copy()
    
    # 1. Remove apenas os totalizadores reais do arquivo
    df_limpo = df_limpo[~df_limpo['Evento'].str.contains('Salario Bruto|Salario Líquido|Salario Liquido', case=False, na=False)]
    
    # 2. Remove "Outros Descontos" APENAS se o valor for POSITIVO (pois é usado como lixo/base de cálculo pela prefeitura).
    # Descontos negativos (reais) são mantidos!
    mask_lixo = (df_limpo['Evento'].str.contains('Outros Descontos', case=False, na=False)) & (df_limpo['Valor'] > 0)
    df_limpo = df_limpo[~mask_lixo]
    
    return df_limpo

# Função para carregar e tratar os dados
@st.cache_data
def load_data(file_detalhe, file_holerite, file_holerite_2=None):
    try:
        df_detalhe = pd.read_csv(file_detalhe, sep='|', dtype={'Matrícula': str}, encoding='latin1')
        df_holerite = pd.read_csv(file_holerite, sep='|', dtype={'Matrícula': str}, encoding='latin1')

        if 'Salário Bruto' in df_detalhe.columns:
            df_detalhe['Salário Bruto'] = clean_currency_series(df_detalhe['Salário Bruto'])
        if 'Salário Líquido' in df_detalhe.columns:
            df_detalhe['Salário Líquido'] = clean_currency_series(df_detalhe['Salário Líquido'])
        if 'Valor' in df_holerite.columns:
            df_holerite['Valor'] = clean_currency_series(df_holerite['Valor'])

        cruzamento_ativo = False

        if file_holerite_2 is not None:
            df_holerite_2 = pd.read_csv(file_holerite_2, sep='|', dtype={'Matrícula': str}, encoding='latin1')
            matriculas_mes2 = df_holerite_2['Matrícula'].unique()
            df_holerite_comuns = df_holerite[df_holerite['Matrícula'].isin(matriculas_mes2)]
            df_holerite_novos = df_holerite[~df_holerite['Matrícula'].isin(matriculas_mes2)]
            
            eventos_mes2 = df_holerite_2[['Matrícula', 'Evento']].drop_duplicates()
            df_holerite_comuns_filtrado = df_holerite_comuns.merge(eventos_mes2, on=['Matrícula', 'Evento'], how='inner')
            df_holerite = pd.concat([df_holerite_comuns_filtrado, df_holerite_novos], ignore_index=True)
            cruzamento_ativo = True

            # Aplica a limpeza centralizada
            holerite_limpo = limpar_eventos_holerite(df_holerite)
            
            holerite_prov = holerite_limpo[holerite_limpo['Valor'] > 0]
            bruto_padrao = holerite_prov.groupby('Matrícula')['Valor'].sum().reset_index()
            bruto_padrao.rename(columns={'Valor': 'Novo_Bruto'}, inplace=True)
            
            df_detalhe = df_detalhe.merge(bruto_padrao, on='Matrícula', how='left')
            df_detalhe['Salário Bruto'] = df_detalhe['Novo_Bruto'].fillna(df_detalhe['Salário Bruto'])

        df_detalhe_mensal = df_detalhe[df_detalhe['Tipo Folha'].astype(str).str.contains('Mensal', case=False, na=False)]
        df_holerite_mensal = df_holerite[df_holerite['Tipo de Folha'].astype(str).str.contains('Mensal', case=False, na=False)]

        return df_detalhe_mensal, df_holerite_mensal, df_detalhe, df_holerite, cruzamento_ativo
    except Exception as e:
        st.error(f"Erro ao processar os arquivos. Verifique se o formato está correto. Detalhe: {e}")
        return None, None, None, None, False

def formata_moeda(val):
    return f"R$ {val:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

# Título da Aplicação
st.title("🏛️ Sistema Estratégico de Folha de Pagamento")
st.markdown("Plataforma de análise e simulação de impactos financeiros da folha municipal.")

# Sidebar - Upload de Arquivos
st.sidebar.header("📥 Entrada de Dados")
file_detalhe = st.sidebar.file_uploader("1. Detalhe Funcionários (CSV)", type=['csv'])
file_holerite = st.sidebar.file_uploader("2. Holerite Mês de Referência (CSV)", type=['csv'], help="Este será o mês usado como base para os valores.")

st.sidebar.markdown("---")
st.sidebar.markdown("**Filtro de Rubricas Constantes (Opcional)**")
st.sidebar.info("Faça upload de um mês diferente para cruzar dados e remover rubricas variáveis (férias, extras, faltas). O sistema simulará um 'mês padrão'.")
file_holerite_2 = st.sidebar.file_uploader("3. Holerite Mês de Comparação (CSV)", type=['csv'])

if file_detalhe is not None and file_holerite is not None:
    dados_carregados = load_data(file_detalhe, file_holerite, file_holerite_2)
    
    if dados_carregados[0] is not None:
        df_detalhe, df_holerite, df_detalhe_full, df_holerite_full, cruzamento_ativo = dados_carregados
        
        st.sidebar.success("✅ Dados carregados com sucesso!")
        if cruzamento_ativo:
            st.sidebar.success("✨ **Cruzamento Ativo:** O sistema filtrou o contracheque e está utilizando apenas as rubricas fixas/constantes de cada servidor!")

        st.sidebar.markdown("---")
        st.sidebar.info("💡 **Dica:** Utilize as abas no painel principal para navegar entre as diferentes ferramentas do sistema sem precisar recarregar a página.")
        
        # Criação das Abas Principais de Navegação
        tab_geral, tab_sec, tab_holerite, tab_simulador = st.tabs([
            "📊 Visão Geral", 
            "🏢 Análise por Secretaria", 
            "📄 Consulta de Holerite", 
            "📈 Simulador de Negociação"
        ])

        # =========================================================================
        # ABA 1: VISÃO GERAL
        # =========================================================================
        with tab_geral:
            if cruzamento_ativo:
                st.info("ℹ️ Os valores de 'Custo Bruto' e 'Média Salarial' abaixo representam o cenário padrão (sem rubricas variáveis), gerado pelo cruzamento dos arquivos.")

            st.header("Visão Global do Município (Folha Mensal)")
            
            col1, col2, col3, col4 = st.columns(4)
            total_servidores = df_detalhe['Matrícula'].nunique()
            custo_bruto = df_detalhe['Salário Bruto'].sum()
            media_salarial = df_detalhe['Salário Bruto'].mean()
            maior_salario = df_detalhe['Salário Bruto'].max()

            col1.metric("Total de Servidores (Ativos)", f"{total_servidores:,}".replace(',', '.'))
            col2.metric("Custo Total Bruto (Mensal)", formata_moeda(custo_bruto))
            col3.metric("Média Salarial Bruta", formata_moeda(media_salarial))
            col4.metric("Maior Salário", formata_moeda(maior_salario))

            st.markdown("---")
            col_chart1, col_chart2 = st.columns(2)
            
            with col_chart1:
                st.subheader("Distribuição por Escolaridade")
                if 'Escolaridade' in df_detalhe.columns:
                    escolaridade_count = df_detalhe['Escolaridade'].value_counts().reset_index()
                    escolaridade_count.columns = ['Escolaridade', 'Quantidade']
                    fig_esc = px.pie(escolaridade_count, values='Quantidade', names='Escolaridade', hole=0.4)
                    st.plotly_chart(fig_esc, use_container_width=True)

            with col_chart2:
                st.subheader("Top 10 Cargos mais Frequentes")
                if 'Cargo' in df_detalhe.columns:
                    cargo_count = df_detalhe['Cargo'].value_counts().head(10).reset_index()
                    cargo_count.columns = ['Cargo', 'Quantidade']
                    fig_cargo = px.bar(cargo_count, x='Quantidade', y='Cargo', orientation='h', text='Quantidade')
                    fig_cargo.update_layout(yaxis={'categoryorder':'total ascending'})
                    st.plotly_chart(fig_cargo, use_container_width=True)

        # =========================================================================
        # ABA 2: ANÁLISE POR SECRETARIA
        # =========================================================================
        with tab_sec:
            st.header("Análise de Custo por Secretaria")
            
            if 'Secretaria' in df_detalhe.columns:
                sec_group = df_detalhe.groupby('Secretaria').agg(
                    Total_Servidores=('Matrícula', 'count'),
                    Custo_Mensal=('Salário Bruto', 'sum'),
                    Media_Salarial=('Salário Bruto', 'mean')
                ).reset_index().sort_values('Custo_Mensal', ascending=False)
                
                fig_sec = px.bar(sec_group, x='Secretaria', y='Custo_Mensal', 
                                 title="Custo Total Bruto por Secretaria",
                                 text=sec_group['Custo_Mensal'].apply(lambda x: f"R$ {x/1000000:,.1f}M"),
                                 color='Custo_Mensal', color_continuous_scale='Blues')
                st.plotly_chart(fig_sec, use_container_width=True)

                with st.expander("📊 Ver Tabela Detalhada das Secretarias"):
                    sec_group_display = sec_group.copy()
                    sec_group_display['Custo_Mensal'] = sec_group_display['Custo_Mensal'].apply(formata_moeda)
                    sec_group_display['Media_Salarial'] = sec_group_display['Media_Salarial'].apply(formata_moeda)
                    st.dataframe(sec_group_display, use_container_width=True, hide_index=True)
                
                st.markdown("---")
                st.subheader("🔍 Explorar Cargos de uma Secretaria")
                sec_selecionada = st.selectbox("Selecione a Secretaria:", sec_group['Secretaria'])
                df_sec_filtrada = df_detalhe[df_detalhe['Secretaria'] == sec_selecionada]
                
                cargos_sec = df_sec_filtrada.groupby('Cargo').agg(
                    Servidores=('Matrícula', 'count'),
                    Custo_Total=('Salário Bruto', 'sum')
                ).reset_index().sort_values('Custo_Total', ascending=False)
                
                fig_cargos_sec = px.bar(cargos_sec.head(15), x='Custo_Total', y='Cargo', orientation='h', 
                                        title=f"Top 15 Cargos de Maior Custo na {sec_selecionada}")
                fig_cargos_sec.update_layout(yaxis={'categoryorder':'total ascending'})
                st.plotly_chart(fig_cargos_sec, use_container_width=True)

        # =========================================================================
        # ABA 3: CONSULTA DE HOLERITE
        # =========================================================================
        with tab_holerite:
            st.header("Consulta Individual de Holerite")
            st.markdown("Verifique os detalhamentos da folha de pagamento de um servidor específico.")

            if cruzamento_ativo:
                st.info("✨ **Modo Holerite Padrão Ativo:** Você está visualizando apenas os eventos fixos deste servidor. Rubricas variáveis (como férias) foram automaticamente removidas.")

            with st.container(border=True):
                col_busca1, col_busca2 = st.columns([1, 3])
                with col_busca1:
                    tipo_busca = st.radio("Buscar por:", ["Nome", "Matrícula"])
                with col_busca2:
                    if tipo_busca == "Nome":
                        nomes = sorted(df_detalhe_full['Nome'].dropna().unique())
                        selecao = st.selectbox("Selecione o servidor:", nomes)
                    else:
                        matriculas = sorted(df_detalhe_full['Matrícula'].dropna().unique())
                        selecao = st.selectbox("Selecione a matrícula:", matriculas)

            if selecao:
                if tipo_busca == "Nome":
                    servidor_info = df_detalhe_full[df_detalhe_full['Nome'] == selecao].iloc[0]
                    mat_servidor = servidor_info['Matrícula']
                else:
                    servidor_info = df_detalhe_full[df_detalhe_full['Matrícula'] == selecao].iloc[0]
                    mat_servidor = selecao

                st.subheader(f"👤 {servidor_info['Nome']} (Matrícula: {mat_servidor})")
                
                col_info1, col_info2, col_info3 = st.columns(3)
                col_info1.write(f"**Secretaria:** {servidor_info.get('Secretaria', 'N/A')}")
                col_info1.write(f"**Local de Trabalho:** {servidor_info.get('Local de Trabalho', 'N/A')}")
                col_info2.write(f"**Cargo:** {servidor_info.get('Cargo', 'N/A')}")
                col_info2.write(f"**Tempo de Casa:** {servidor_info.get('Tempo de Casa', 'N/A')}")
                col_info3.write(f"**Data Admissão:** {servidor_info.get('Data Admissão', 'N/A')}")
                col_info3.write(f"**Condição:** {servidor_info.get('Condição', 'N/A')}")

                st.markdown("---")
                holerite_servidor = df_holerite_full[df_holerite_full['Matrícula'] == mat_servidor]
                tipos_folha_disp = holerite_servidor['Tipo de Folha'].unique()
                tipo_folha_selecionada = st.selectbox("Selecione a Folha de Referência:", tipos_folha_disp)
                
                holerite_view = holerite_servidor[holerite_servidor['Tipo de Folha'] == tipo_folha_selecionada]

                # Aplica limpeza centralizada
                eventos = limpar_eventos_holerite(holerite_view)
                
                proventos = eventos[eventos['Valor'] > 0][['Evento', 'Valor']]
                descontos = eventos[eventos['Valor'] < 0][['Evento', 'Valor']]
                
                col_prov, col_desc = st.columns(2)
                with col_prov:
                    st.success("🟢 PROVENTOS")
                    proventos_fmt = proventos.copy()
                    proventos_fmt['Valor'] = proventos_fmt['Valor'].apply(formata_moeda)
                    st.dataframe(proventos_fmt, hide_index=True, use_container_width=True)
                with col_desc:
                    st.error("🔴 DESCONTOS")
                    descontos_fmt = descontos.copy()
                    descontos_fmt['Valor'] = descontos_fmt['Valor'].apply(formata_moeda)
                    st.dataframe(descontos_fmt, hide_index=True, use_container_width=True)

                st.markdown("#### 💰 Resumo Financeiro")
                
                bruto_calculado = proventos['Valor'].sum()
                descontos_calculado = descontos['Valor'].sum()
                liquido_calculado = bruto_calculado + descontos_calculado

                res_col1, res_col2, res_col3 = st.columns(3)
                label_sufixo = " (Constante)" if cruzamento_ativo else ""
                res_col1.metric(f"Salário Bruto{label_sufixo}", formata_moeda(bruto_calculado))
                res_col2.metric(f"Total de Descontos{label_sufixo}", formata_moeda(descontos_calculado))
                res_col3.metric(f"Salário Líquido{label_sufixo}", formata_moeda(liquido_calculado))

        # =========================================================================
        # ABA 4: SIMULADOR DE IMPACTO (COM ENCARGOS AVANÇADOS)
        # =========================================================================
        with tab_simulador:
            st.header("📈 Simulador de Negociação Salarial")
            st.markdown("Simule propostas considerando os reajustes em cascata nos encargos patronais e descontos (IPML/INSS / Assist. Médica).")

            # Aplica limpeza centralizada para gerar a lista de opções de configuração
            df_holerite_limpo = limpar_eventos_holerite(df_holerite)
            proventos_unicos = sorted(df_holerite_limpo[df_holerite_limpo['Valor'] > 0]['Evento'].dropna().unique().tolist())

            with st.container(border=True):
                st.subheader("⚙️ Configuração da Proposta")
                col_sim1, col_sim2 = st.columns(2)
                
                with col_sim1:
                    st.markdown("**1. Reajuste Salarial (Base e Adicionais)**")
                    reajuste_perc = st.slider("Percentual de Reajuste (%):", min_value=0.0, max_value=25.0, value=0.0, step=0.1)
                    palavras_chave_padrao = ['SALARIO', 'VENCIMENTO', 'TEMPO', 'ANUENIO', 'QUINQUENIO', 'COMBUSTIVEL', 'INSALUBRIDADE']
                    default_rubricas = [r for r in proventos_unicos if any(k in r.upper() for k in palavras_chave_padrao)]
                    rubricas_reajuste = st.multiselect(
                        "Rubricas que sofrerão reajuste (efeito cascata):",
                        options=proventos_unicos, default=default_rubricas
                    )
                
                with col_sim2:
                    st.markdown("**2. Política de Benefícios (Vale Alimentação)**")
                    opcoes_va = [r for r in proventos_unicos if 'ALIMENTA' in r.upper() or 'REFEICAO' in r.upper()]
                    indice_va = proventos_unicos.index(opcoes_va[0]) if opcoes_va else 0
                    nome_rubrica_va = st.selectbox("Rubrica do Vale/Auxílio Alimentação:", options=proventos_unicos, index=indice_va)
                    
                    va_atual_df = df_holerite[df_holerite['Evento'].str.upper() == nome_rubrica_va.upper()]
                    valor_va_medio_atual = va_atual_df['Valor'].mean() if not va_atual_df.empty else 0
                    st.caption(f"Valor médio praticado: {formata_moeda(valor_va_medio_atual)}. Variações por faltas/teto serão mantidas no ajuste percentual.")
                    
                    tipo_reajuste_va = st.radio("Tipo de Aumento no VA:", ["Percentual (%)", "Fixo (R$)"], horizontal=True)
                    if tipo_reajuste_va == "Percentual (%)":
                        aumento_va_val = st.number_input("Aumento no Vale Alimentação (%):", min_value=0.0, value=0.0, step=1.0)
                    else:
                        aumento_va_val = st.number_input("Aumento FIXO no Vale Alimentação (R$):", min_value=0.0, value=0.0, step=10.0)
                        
                    aplicar_va_todos = st.checkbox("Aplicar aumento de VA para TODOS os ativos (mesmo os que não recebem)?")

                # EXPANDER PARA ENCARGOS (IPML/INSS E MÉDICA)
                with st.expander("⚙️ Configurações Avançadas (Encargos, Previdência e Assistência Médica)"):
                    st.markdown("Configure os percentuais de desconto e custo patronal que incidem sobre a remuneração base.")
                    col_enc1, col_enc2 = st.columns(2)
                    with col_enc1:
                        aliquota_ipml_servidor = st.number_input("Previdência (IPML / INSS) - Desconto Servidor (%)", value=14.0, step=0.1)
                        aliquota_ipml_patronal = st.number_input("Previdência (IPML / INSS) - Custo Patronal Prefeitura (%)", value=14.0, step=0.1)
                    with col_enc2:
                        aliquota_medica = st.number_input("Assistência Médica - Desconto (%)", value=5.0, step=0.1)
                        
                    rubricas_base_encargos = st.multiselect(
                        "Selecione as rubricas que formam a BASE DE CÁLCULO para a Previdência e Assistência Médica:",
                        options=proventos_unicos, default=default_rubricas,
                        help="Geralmente a Previdência incide sobre o salário base e gratificações fixas."
                    )

            # CÁLCULOS GLOBAIS
            custo_total_atual = df_detalhe['Salário Bruto'].sum()
            
            # 1. Impacto Salarial
            if rubricas_reajuste:
                custo_base_atual = df_holerite[df_holerite['Evento'].isin(rubricas_reajuste)]['Valor'].sum()
                impacto_mensal_salario = custo_base_atual * (reajuste_perc / 100)
            else:
                impacto_mensal_salario = 0
            
            # 2. Impacto VA
            qtd_servidores_va = va_atual_df['Matrícula'].nunique()
            if tipo_reajuste_va == "Percentual (%)":
                # Aplica o % sobre a folha atual de VA
                impacto_mensal_va = va_atual_df['Valor'].sum() * (aumento_va_val / 100)
                if aplicar_va_todos: # Adiciona um VA médio para quem não tem
                    servidores_sem_va = df_detalhe['Matrícula'].nunique() - qtd_servidores_va
                    impacto_mensal_va += (servidores_sem_va * valor_va_medio_atual * (1 + aumento_va_val/100))
            else: # Fixo em R$
                if aplicar_va_todos:
                    impacto_mensal_va = df_detalhe['Matrícula'].nunique() * aumento_va_val
                else:
                    impacto_mensal_va = qtd_servidores_va * aumento_va_val

            # 3. Impacto Patronal (Prefeitura) sobre o aumento
            base_encargos_atual_prefeitura = df_holerite[df_holerite['Evento'].isin(rubricas_base_encargos)]['Valor'].sum()
            aumento_base_encargos_prefeitura = base_encargos_atual_prefeitura * (reajuste_perc / 100)
            impacto_patronal = aumento_base_encargos_prefeitura * (aliquota_ipml_patronal / 100)

            impacto_mensal_total = impacto_mensal_salario + impacto_mensal_va + impacto_patronal
            impacto_anual_total = impacto_mensal_total * 13.3

            # RESULTADOS
            st.markdown("---")
            st.subheader("🌎 Impacto Orçamentário Global (Prefeitura)")
            res_col1, res_col2, res_col3 = st.columns(3)
            res_col1.metric("Custo Folha Atual (Mensal)", formata_moeda(custo_total_atual))
            res_col2.metric("Acréscimo MENSAL Direto", f"+ {formata_moeda(impacto_mensal_total)}", f"{(impacto_mensal_total/custo_total_atual)*100:.2f}% impacto", delta_color="inverse")
            res_col3.metric("Novo Custo (Mensal c/ Patronal)", formata_moeda(custo_total_atual + impacto_mensal_total))

            st.error(f"⚠️ **IMPACTO ANUAL NO ORÇAMENTO:** Provisionamento de **{formata_moeda(impacto_anual_total)}** (Considerando reajuste salarial, benefícios e acréscimo de dívida Patronal).")

            with st.expander("📊 Ver Gráfico de Composição do Aumento (Waterfall)"):
                dados_waterfall = pd.DataFrame({
                    'Etapa': ['Custo Atual', 'Aumento Proventos', 'Aumento VA', 'Previdência Patronal (Custo Extra)', 'Novo Custo Total'],
                    'Valor': [custo_total_atual, impacto_mensal_salario, impacto_mensal_va, impacto_patronal, custo_total_atual + impacto_mensal_total],
                    'Measure': ['absolute', 'relative', 'relative', 'relative', 'total']
                })
                fig_wf = go.Figure(go.Waterfall(
                    name = "20", orientation = "v", measure = dados_waterfall['Measure'],
                    x = dados_waterfall['Etapa'], y = dados_waterfall['Valor'], textposition = "outside",
                    text = dados_waterfall['Valor'].apply(lambda x: f"R$ {x/1000000:.2f}M" if x > 1000000 else f"R$ {x/1000:.1f}K"),
                    connector = {"line":{"color":"rgb(63, 63, 63)"}},
                ))
                st.plotly_chart(fig_wf, use_container_width=True)

            # SIMULAÇÃO INDIVIDUAL COM DESCONTOS RECALCULADOS
            st.markdown("---")
            st.subheader("👤 Simulação de Holerite Individual (Aumento Real)")
            st.markdown("Veja o reflexo da proposta no contracheque. **Os descontos de Previdência e Assistência Médica serão recalculados** sobre a nova base salarial para mostrar o valor líquido exato.")

            col_busca_sim1, col_busca_sim2 = st.columns([1, 3])
            with col_busca_sim1:
                tipo_busca_sim = st.radio("Buscar servidor por:", ["Nome", "Matrícula"], key="radio_sim")
            with col_busca_sim2:
                if tipo_busca_sim == "Nome":
                    selecao_sim = st.selectbox("Selecione o nome:", sorted(df_detalhe_full['Nome'].dropna().unique()), key="sel_nome_sim")
                else:
                    selecao_sim = st.selectbox("Selecione a matrícula:", sorted(df_detalhe_full['Matrícula'].dropna().unique()), key="sel_mat_sim")

            if selecao_sim:
                if tipo_busca_sim == "Nome":
                    servidor_info_sim = df_detalhe_full[df_detalhe_full['Nome'] == selecao_sim].iloc[0]
                    mat_servidor_sim = servidor_info_sim['Matrícula']
                else:
                    servidor_info_sim = df_detalhe_full[df_detalhe_full['Matrícula'] == selecao_sim].iloc[0]
                    mat_servidor_sim = selecao_sim

                holerite_sim = df_holerite_full[(df_holerite_full['Matrícula'] == mat_servidor_sim) & 
                                                (df_holerite_full['Tipo de Folha'].astype(str).str.contains('Mensal', case=False, na=False))]
                
                if holerite_sim.empty:
                    st.warning("Sem registro de 'Pagamento Mensal' para este servidor.")
                else:
                    # Limpeza centralizada para a simulação
                    eventos_sim = limpar_eventos_holerite(holerite_sim)
                    eventos_sim['Valor Simulado'] = eventos_sim['Valor'].copy()
                    
                    # 1. Aplica Reajuste nos Proventos
                    mask_proporcionais = eventos_sim['Evento'].isin(rubricas_reajuste)
                    if mask_proporcionais.any():
                        eventos_sim.loc[mask_proporcionais, 'Valor Simulado'] = eventos_sim.loc[mask_proporcionais, 'Valor'] * (1 + (reajuste_perc / 100))
                    
                    # 2. Aplica VA
                    mask_va = eventos_sim['Evento'].str.upper() == nome_rubrica_va.upper()
                    if mask_va.any():
                        if tipo_reajuste_va == "Percentual (%)":
                            eventos_sim.loc[mask_va, 'Valor Simulado'] = eventos_sim.loc[mask_va, 'Valor'] * (1 + (aumento_va_val / 100))
                        else:
                            eventos_sim.loc[mask_va, 'Valor Simulado'] = eventos_sim.loc[mask_va, 'Valor'] + aumento_va_val
                    elif aplicar_va_todos and aumento_va_val > 0:
                        valor_injetar = (valor_va_medio_atual * (1 + aumento_va_val/100)) if tipo_reajuste_va == "Percentual (%)" else aumento_va_val
                        nova_rubrica = pd.DataFrame([{'Matrícula': mat_servidor_sim, 'Nome': servidor_info_sim['Nome'], 'Tipo de Folha': 'Pagamento Mensal', 'Evento': nome_rubrica_va, 'Valor': 0.0, 'Valor Simulado': valor_injetar}])
                        eventos_sim = pd.concat([eventos_sim, nova_rubrica], ignore_index=True)

                    # 3. Recalcula Descontos (Previdência e Médica)
                    base_encargos_sim_ind = eventos_sim[eventos_sim['Evento'].isin(rubricas_base_encargos)]['Valor Simulado'].sum()
                    
                    # Cobre IPML, PREVIDENCIARIO ou I.N.S.S (Celetistas)
                    mask_prev = eventos_sim['Evento'].str.contains('IPML|PREVID|I\.N\.S\.S', case=False, regex=True)
                    if mask_prev.any():
                        eventos_sim.loc[mask_prev, 'Valor Simulado'] = -(base_encargos_sim_ind * (aliquota_ipml_servidor / 100))
                        
                    # Cobre ASSISTENCIA MEDICA ESTATUTO ou ASSISTENCIA MEDICA - COMISS.
                    mask_medica = eventos_sim['Evento'].str.contains('MEDICA', case=False)
                    if mask_medica.any():
                        eventos_sim.loc[mask_medica, 'Valor Simulado'] = -(base_encargos_sim_ind * (aliquota_medica / 100))

                    # 4. Finaliza Totais
                    prov_sim = eventos_sim[eventos_sim['Valor Simulado'] > 0].copy()
                    desc_sim = eventos_sim[eventos_sim['Valor Simulado'] < 0].copy()
                    
                    liquido_atual = prov_sim['Valor'].sum() + desc_sim['Valor'].sum()
                    liquido_simulado = prov_sim['Valor Simulado'].sum() + desc_sim['Valor Simulado'].sum()

                    st.markdown(f"**Resultado para {servidor_info_sim['Nome']}**")
                    col_res1, col_res2, col_res3 = st.columns(3)
                    col_res1.metric("Líquido ATUAL", formata_moeda(liquido_atual))
                    col_res2.metric("Líquido SIMULADO", formata_moeda(liquido_simulado), f"+ {formata_moeda(liquido_simulado - liquido_atual)}")
                    col_res3.metric("Aumento REAL no Bolso", f"{((liquido_simulado / liquido_atual) - 1) * 100 if liquido_atual > 0 else 0:.2f}%")

                    with st.expander("📄 Ver Detalhamento do Holerite Simulado (Atenção às alterações em Previdência/Médica)", expanded=True):
                        col_prov_sim, col_desc_sim = st.columns(2)
                        with col_prov_sim:
                            st.success("🟢 PROVENTOS")
                            tab_prov = prov_sim[['Evento', 'Valor', 'Valor Simulado']].copy()
                            tab_prov.columns = ['Rubrica', 'Atual', 'Simulado']
                            tab_prov['Atual'] = tab_prov['Atual'].apply(formata_moeda)
                            tab_prov['Simulado'] = tab_prov['Simulado'].apply(formata_moeda)
                            st.dataframe(tab_prov, hide_index=True, use_container_width=True)
                        with col_desc_sim:
                            st.error("🔴 DESCONTOS")
                            tab_desc = desc_sim[['Evento', 'Valor', 'Valor Simulado']].copy()
                            tab_desc.columns = ['Rubrica', 'Atual', 'Simulado']
                            tab_desc['Atual'] = tab_desc['Atual'].apply(formata_moeda)
                            tab_desc['Simulado'] = tab_desc['Simulado'].apply(formata_moeda)
                            st.dataframe(tab_desc, hide_index=True, use_container_width=True)
                            
                    st.caption("ℹ️ *Nota: O recálculo de Imposto de Renda (IRRF) requer análise de faixas progressivas e dedução por dependentes (que não estão no holerite), por isso o IRRF foi mantido constante.*")

else:
    # Tela Inicial
    st.info("👈 Por favor, faça o upload dos arquivos CSV no menu lateral para iniciar.")
    st.markdown("""
    ### Bem-vindo ao Sistema Estratégico de Folha de Pagamento!
    Para iniciar, carregue os ficheiros de **Detalhe dos Funcionários** e **Holerites** na barra à esquerda.
    """)
