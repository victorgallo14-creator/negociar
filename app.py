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

# Estilização básica via CSS
st.markdown("""
    <style>
    .metric-card {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 10px;
        text-align: center;
    }
    .metric-value {
        font-size: 24px;
        font-weight: bold;
        color: #1f77b4;
    }
    </style>
""", unsafe_allow_html=True)

# Função para carregar e tratar os dados
@st.cache_data
def load_data(file_detalhe, file_holerite):
    try:
        # Lendo os arquivos CSV (tratando o delimitador '|')
        df_detalhe = pd.read_csv(file_detalhe, sep='|', dtype={'Matrícula': str}, encoding='latin1')
        df_holerite = pd.read_csv(file_holerite, sep='|', dtype={'Matrícula': str}, encoding='latin1')

        # Limpeza e conversão de dados do Detalhe
        if 'Salário Bruto' in df_detalhe.columns:
            df_detalhe['Salário Bruto'] = pd.to_numeric(df_detalhe['Salário Bruto'].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
        if 'Salário Líquido' in df_detalhe.columns:
            df_detalhe['Salário Líquido'] = pd.to_numeric(df_detalhe['Salário Líquido'].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)

        # Limpeza e conversão de dados do Holerite
        if 'Valor' in df_holerite.columns:
            df_holerite['Valor'] = pd.to_numeric(df_holerite['Valor'].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)

        # Filtrando apenas 'Pagamento Mensal' para não duplicar com 13º e férias nas análises globais
        df_detalhe_mensal = df_detalhe[df_detalhe['Tipo Folha'].astype(str).str.contains('Mensal', case=False, na=False)]
        df_holerite_mensal = df_holerite[df_holerite['Tipo de Folha'].astype(str).str.contains('Mensal', case=False, na=False)]

        return df_detalhe_mensal, df_holerite_mensal, df_detalhe, df_holerite # Retorna também o completo para consultas específicas
    except Exception as e:
        st.error(f"Erro ao processar os arquivos. Verifique se o formato está correto. Detalhe: {e}")
        return None, None, None, None

# Título da Aplicação
st.title("🏛️ Sistema Estratégico de Folha de Pagamento")
st.markdown("Plataforma de análise e simulação de impactos financeiros da folha de pagamento municipal.")

# Sidebar - Upload de Arquivos e Navegação
st.sidebar.header("📥 Entrada de Dados")
file_detalhe = st.sidebar.file_uploader("Upload: Detalhe Funcionários (CSV)", type=['csv'])
file_holerite = st.sidebar.file_uploader("Upload: Holerite Eventos (CSV)", type=['csv'])

if file_detalhe is not None and file_holerite is not None:
    df_detalhe, df_holerite, df_detalhe_full, df_holerite_full = load_data(file_detalhe, file_holerite)
    
    if df_detalhe is not None:
        st.sidebar.markdown("---")
        st.sidebar.header("🧭 Navegação")
        menu = st.sidebar.radio("Selecione o Módulo:", [
            "📊 Visão Geral (Dashboard)",
            "🏢 Análise por Secretaria",
            "📄 Consulta de Holerite",
            "📈 Simulador de Impacto (Negociação)"
        ])

        # -----------------------------------------------------------------------------
        # MÓDULO 1: VISÃO GERAL
        # -----------------------------------------------------------------------------
        if menu == "📊 Visão Geral (Dashboard)":
            st.header("Visão Geral do Município (Folha Mensal)")
            
            # Métricas principais
            col1, col2, col3, col4 = st.columns(4)
            total_servidores = df_detalhe['Matrícula'].nunique()
            custo_bruto = df_detalhe['Salário Bruto'].sum()
            media_salarial = df_detalhe['Salário Bruto'].mean()
            maior_salario = df_detalhe['Salário Bruto'].max()

            col1.metric("Total de Servidores (Ativos)", f"{total_servidores:,}".replace(',', '.'))
            col2.metric("Custo Total Bruto (Mensal)", f"R$ {custo_bruto:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
            col3.metric("Média Salarial Bruta", f"R$ {media_salarial:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
            col4.metric("Maior Salário", f"R$ {maior_salario:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))

            st.markdown("---")

            # Gráficos
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

        # -----------------------------------------------------------------------------
        # MÓDULO 2: ANÁLISE POR SECRETARIA
        # -----------------------------------------------------------------------------
        elif menu == "🏢 Análise por Secretaria":
            st.header("Análise e Custo por Secretaria")
            
            if 'Secretaria' in df_detalhe.columns:
                # Agrupamento
                sec_group = df_detalhe.groupby('Secretaria').agg(
                    Total_Servidores=('Matrícula', 'count'),
                    Custo_Mensal=('Salário Bruto', 'sum'),
                    Media_Salarial=('Salário Bruto', 'mean')
                ).reset_index().sort_values('Custo_Mensal', ascending=False)

                # Formatação para exibição
                sec_group_display = sec_group.copy()
                sec_group_display['Custo_Mensal'] = sec_group_display['Custo_Mensal'].apply(lambda x: f"R$ {x:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
                sec_group_display['Media_Salarial'] = sec_group_display['Media_Salarial'].apply(lambda x: f"R$ {x:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
                
                # Gráfico
                fig_sec = px.bar(sec_group, x='Secretaria', y='Custo_Mensal', 
                                 title="Custo Total Bruto por Secretaria",
                                 text=sec_group['Custo_Mensal'].apply(lambda x: f"R$ {x/1000000:,.1f}M"),
                                 color='Custo_Mensal', color_continuous_scale='Blues')
                st.plotly_chart(fig_sec, use_container_width=True)

                st.subheader("Tabela Detalhada")
                st.dataframe(sec_group_display, use_container_width=True, hide_index=True)
                
                # Filtro interativo de cargos dentro da secretaria
                st.markdown("---")
                st.subheader("Explorar Secretaria Especifica")
                sec_selecionada = st.selectbox("Selecione uma Secretaria para ver os cargos:", sec_group['Secretaria'])
                df_sec_filtrada = df_detalhe[df_detalhe['Secretaria'] == sec_selecionada]
                
                cargos_sec = df_sec_filtrada.groupby('Cargo').agg(
                    Servidores=('Matrícula', 'count'),
                    Custo_Total=('Salário Bruto', 'sum')
                ).reset_index().sort_values('Custo_Total', ascending=False)
                
                fig_cargos_sec = px.bar(cargos_sec.head(15), x='Custo_Total', y='Cargo', orientation='h', 
                                        title=f"Top 15 Cargos de Maior Custo na {sec_selecionada}")
                fig_cargos_sec.update_layout(yaxis={'categoryorder':'total ascending'})
                st.plotly_chart(fig_cargos_sec, use_container_width=True)

        # -----------------------------------------------------------------------------
        # MÓDULO 3: CONSULTA DE HOLERITE
        # -----------------------------------------------------------------------------
        elif menu == "📄 Consulta de Holerite":
            st.header("Consulta Individual de Holerite")
            st.info("Busque por nome ou matrícula para verificar os detalhamentos da folha de pagamento de um servidor específico.")

            col_busca1, col_busca2 = st.columns(2)
            with col_busca1:
                tipo_busca = st.radio("Buscar por:", ["Nome", "Matrícula"])
            
            with col_busca2:
                if tipo_busca == "Nome":
                    nomes = sorted(df_detalhe_full['Nome'].dropna().unique())
                    selecao = st.selectbox("Digite ou selecione o nome:", nomes)
                    filtro_dict = {'Nome': selecao}
                else:
                    matriculas = sorted(df_detalhe_full['Matrícula'].dropna().unique())
                    selecao = st.selectbox("Digite ou selecione a matrícula:", matriculas)
                    filtro_dict = {'Matrícula': selecao}

            # Filtrar dados do servidor
            if selecao:
                if tipo_busca == "Nome":
                    servidor_info = df_detalhe_full[df_detalhe_full['Nome'] == selecao].iloc[0]
                    mat_servidor = servidor_info['Matrícula']
                else:
                    servidor_info = df_detalhe_full[df_detalhe_full['Matrícula'] == selecao].iloc[0]
                    mat_servidor = selecao

                st.markdown("---")
                st.subheader(f"Servidor(a): {servidor_info['Nome']} (Matrícula: {mat_servidor})")
                
                # Card de informações
                col_info1, col_info2, col_info3 = st.columns(3)
                col_info1.write(f"**Secretaria:** {servidor_info.get('Secretaria', 'N/A')}")
                col_info1.write(f"**Local de Trabalho:** {servidor_info.get('Local de Trabalho', 'N/A')}")
                col_info2.write(f"**Cargo:** {servidor_info.get('Cargo', 'N/A')}")
                col_info2.write(f"**Tempo de Casa:** {servidor_info.get('Tempo de Casa', 'N/A')}")
                col_info3.write(f"**Data Admissão:** {servidor_info.get('Data Admissão', 'N/A')}")
                col_info3.write(f"**Condição:** {servidor_info.get('Condição', 'N/A')}")

                st.markdown("#### Eventos da Folha (Proventos e Descontos)")
                
                # Selecionar tipo de folha (Mensal, 13o, etc)
                holerite_servidor = df_holerite_full[df_holerite_full['Matrícula'] == mat_servidor]
                tipos_folha_disp = holerite_servidor['Tipo de Folha'].unique()
                tipo_folha_selecionada = st.selectbox("Selecione a Folha de Referência:", tipos_folha_disp)
                
                holerite_view = holerite_servidor[holerite_servidor['Tipo de Folha'] == tipo_folha_selecionada]
                
                # 1. Extrair os totais oficiais do contracheque (Bruto e Líquido)
                bruto_oficial = holerite_view[holerite_view['Evento'].str.contains('Bruto', case=False, na=False)]['Valor'].sum()
                liquido_oficial = holerite_view[holerite_view['Evento'].str.contains('Líquido', case=False, na=False)]['Valor'].sum()

                # 2. Separar eventos de proventos e descontos para as tabelas
                # Removemos Bruto, Líquido e Base das tabelas de detalhes
                filtro_tabelas = 'Bruto|Líquido|Base'
                eventos = holerite_view[~holerite_view['Evento'].str.contains(filtro_tabelas, case=False, na=False)]
                
                # Proventos: Valores positivos (exclui os falsos proventos se estiverem chamados de 'Outros Descontos')
                proventos = eventos[(eventos['Valor'] > 0) & ~(eventos['Evento'].str.contains('Outros Descontos', case=False, na=False))][['Evento', 'Valor']]
                
                # Descontos: Valores negativos (inclui os 'Outros Descontos' reais)
                descontos = eventos[eventos['Valor'] < 0][['Evento', 'Valor']]
                
                col_prov, col_desc = st.columns(2)
                
                with col_prov:
                    st.success("🟢 PROVENTOS")
                    proventos_fmt = proventos.copy()
                    proventos_fmt['Valor'] = proventos_fmt['Valor'].apply(lambda x: f"R$ {x:,.2f}".replace('.', ','))
                    st.dataframe(proventos_fmt, hide_index=True, use_container_width=True)
                    st.write(f"**Soma (Proventos):** R$ {proventos['Valor'].sum():,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))

                with col_desc:
                    st.error("🔴 DESCONTOS")
                    descontos_fmt = descontos.copy()
                    descontos_fmt['Valor'] = descontos_fmt['Valor'].apply(lambda x: f"R$ {x:,.2f}".replace('.', ','))
                    st.dataframe(descontos_fmt, hide_index=True, use_container_width=True)
                    st.write(f"**Soma (Descontos):** R$ {descontos['Valor'].sum():,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))

                # 3. Painel de Resumo Final
                st.markdown("---")
                st.markdown("#### 💰 Resumo do Holerite")
                res_col1, res_col2, res_col3 = st.columns(3)
                res_col1.metric("Salário Bruto", f"R$ {bruto_oficial:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
                res_col2.metric("Total de Descontos", f"R$ {descontos['Valor'].sum():,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
                res_col3.metric("Salário Líquido", f"R$ {liquido_oficial:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))

        # -----------------------------------------------------------------------------
        # MÓDULO 4: SIMULADOR DE IMPACTO (MESA DE NEGOCIAÇÃO)
        # -----------------------------------------------------------------------------
        elif menu == "📈 Simulador de Impacto (Negociação)":
            st.header("Simulador de Impacto Financeiro")
            st.markdown("Utilize esta ferramenta para simular o impacto de propostas sindicais ou da prefeitura na folha de pagamento.")

            # Identificar rubricas principais (Salário e Vale Alimentação baseado na amostra)
            # Vamos assumir que "SALARIO" ou "VENCIMENTO" é o base. 
            nome_rubrica_salario = st.selectbox("Qual rubrica representa o Salário Base no arquivo de Holerite?", 
                                                options=['SALARIO', 'VENCIMENTO', 'VENCIMENTOS'], index=0)
            
            nome_rubrica_va = st.selectbox("Qual rubrica representa o Vale/Auxílio Alimentação?", 
                                                options=['AUXILIO ALIMENTACAO', 'VALE ALIMENTACAO'], index=0)

            # Custos Atuais
            custo_total_atual = df_detalhe['Salário Bruto'].sum()
            base_salarial_atual_df = df_holerite[df_holerite['Evento'].str.upper() == nome_rubrica_salario.upper()]
            custo_base_atual = base_salarial_atual_df['Valor'].sum()
            
            va_atual_df = df_holerite[df_holerite['Evento'].str.upper() == nome_rubrica_va.upper()]
            custo_va_atual = va_atual_df['Valor'].sum()
            qtd_servidores_va = va_atual_df['Matrícula'].nunique()

            st.markdown("---")
            st.subheader("Configuração da Proposta")
            
            col_sim1, col_sim2 = st.columns(2)
            
            with col_sim1:
                st.markdown("**1. Reajuste Salarial Linear**")
                reajuste_perc = st.slider("Percentual de Reajuste no Salário Base (%):", min_value=0.0, max_value=25.0, value=0.0, step=0.1)
            
            with col_sim2:
                st.markdown("**2. Política de Benefícios**")
                # Se não todos têm VA, precisamos saber o valor unitário. Vamos pegar a média/moda para o slider.
                valor_va_medio_atual = va_atual_df['Valor'].mean() if not va_atual_df.empty else 0
                st.write(f"*(Valor médio atual praticado: R$ {valor_va_medio_atual:.2f})*")
                aumento_va_fixo = st.number_input("Aumento FIXO no Vale Alimentação por Servidor (R$):", min_value=0.0, value=0.0, step=10.0)

            # Cálculos da Simulação
            # Impacto 1: Reajuste sobre o base (Gera reflexos em anuênios, horas extras, etc, mas aqui simulamos o impacto direto sobre a rubrica)
            impacto_mensal_salario = custo_base_atual * (reajuste_perc / 100)
            
            # Impacto 2: Aumento no VA para quem já recebe (ou pode considerar todos os ativos)
            # Para segurança orçamentária, prefeituras costumam multiplicar pelo total de ativos.
            aplicar_va_todos = st.checkbox("Aplicar aumento de VA para TODOS os servidores ativos (mesmo os que hoje não recebem)?")
            if aplicar_va_todos:
                impacto_mensal_va = df_detalhe['Matrícula'].nunique() * aumento_va_fixo
            else:
                impacto_mensal_va = qtd_servidores_va * aumento_va_fixo

            impacto_mensal_total = impacto_mensal_salario + impacto_mensal_va
            impacto_anual_total = impacto_mensal_total * 13.3 # Aproximadamente 12 meses + 13º + 1/3 Férias

            # Exibição de Resultados
            st.markdown("---")
            st.subheader("💸 Resultados Globais da Simulação")
            
            res_col1, res_col2, res_col3 = st.columns(3)
            
            res_col1.metric("Custo Folha Atual (Mensal)", f"R$ {custo_total_atual:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
            res_col2.metric("Acréscimo MENSAL Estimado", f"+ R$ {impacto_mensal_total:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'), f"{(impacto_mensal_total/custo_total_atual)*100:.2f}% de impacto", delta_color="inverse")
            res_col3.metric("Novo Custo Folha (Mensal)", f"R$ {(custo_total_atual + impacto_mensal_total):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))

            st.warning(f"⚠️ **IMPACTO ANUAL ESTIMADO NO ORÇAMENTO:** O acréscimo provisionado para o ano (incluindo 13º e Férias proporcionais) é de **R$ {impacto_anual_total:,.2f}**".replace(',', 'X').replace('.', ',').replace('X', '.'))

            # Gráfico de cascata (Waterfall) para mostrar a transição
            with st.expander("Ver Gráfico de Composição do Aumento"):
                dados_waterfall = pd.DataFrame({
                    'Etapa': ['Custo Atual', 'Reajuste Salarial', 'Aumento VA', 'Custo Projetado'],
                    'Valor': [custo_total_atual, impacto_mensal_salario, impacto_mensal_va, custo_total_atual + impacto_mensal_total],
                    'Measure': ['absolute', 'relative', 'relative', 'total']
                })

                fig_wf = go.Figure(go.Waterfall(
                    name = "20", orientation = "v",
                    measure = dados_waterfall['Measure'],
                    x = dados_waterfall['Etapa'],
                    textposition = "outside",
                    text = dados_waterfall['Valor'].apply(lambda x: f"R$ {x/1000000:.2f}M"),
                    y = dados_waterfall['Valor'],
                    connector = {"line":{"color":"rgb(63, 63, 63)"}},
                ))
                fig_wf.update_layout(title="Transição do Custo da Folha Mensal (em Milhões)")
                st.plotly_chart(fig_wf, use_container_width=True)

            st.caption("*Nota: Esta simulação calcula o impacto financeiro direto bruto sobre as rubricas selecionadas. Impactos indiretos em encargos patronais (INSS/Regime Próprio) dependem da legislação local e devem ser acrescidos à margem.*")

            # ---------------------------------------------------------
            # NOVA SEÇÃO: HOLERITE SIMULADO INDIVIDUAL
            # ---------------------------------------------------------
            st.markdown("---")
            st.subheader("👤 Simulação Individual (Holerite Simulado)")
            st.markdown("Pesquise um servidor para ver como o salário dele ficará com a proposta que você acabou de configurar acima.")

            col_busca_sim1, col_busca_sim2 = st.columns(2)
            with col_busca_sim1:
                tipo_busca_sim = st.radio("Buscar servidor por:", ["Nome", "Matrícula"], key="radio_busca_sim")
            
            with col_busca_sim2:
                if tipo_busca_sim == "Nome":
                    nomes_sim = sorted(df_detalhe_full['Nome'].dropna().unique())
                    selecao_sim = st.selectbox("Selecione o nome:", nomes_sim, key="select_nome_sim")
                else:
                    matriculas_sim = sorted(df_detalhe_full['Matrícula'].dropna().unique())
                    selecao_sim = st.selectbox("Selecione a matrícula:", matriculas_sim, key="select_mat_sim")

            if selecao_sim:
                # Obter dados do servidor
                if tipo_busca_sim == "Nome":
                    servidor_info_sim = df_detalhe_full[df_detalhe_full['Nome'] == selecao_sim].iloc[0]
                    mat_servidor_sim = servidor_info_sim['Matrícula']
                else:
                    servidor_info_sim = df_detalhe_full[df_detalhe_full['Matrícula'] == selecao_sim].iloc[0]
                    mat_servidor_sim = selecao_sim

                st.markdown(f"**Holerite Simulado para:** {servidor_info_sim['Nome']} (Matrícula: {mat_servidor_sim})")
                
                # Resgatar folha mensal deste servidor
                holerite_sim = df_holerite_full[(df_holerite_full['Matrícula'] == mat_servidor_sim) & 
                                                (df_holerite_full['Tipo de Folha'].astype(str).str.contains('Mensal', case=False, na=False))]
                
                if holerite_sim.empty:
                    st.warning("Este servidor não possui registro de 'Pagamento Mensal' no arquivo de holerites para realizar a simulação.")
                else:
                    # Filtra apenas eventos reais (tira os totais e informações de base da prefeitura)
                    filtro_exclusao = 'Bruto|Líquido|Base'
                    eventos_sim = holerite_sim[~holerite_sim['Evento'].str.contains(filtro_exclusao, case=False, na=False)].copy()
                    eventos_sim = eventos_sim[~((eventos_sim['Valor'] > 0) & (eventos_sim['Evento'].str.contains('Outros Descontos', case=False, na=False)))]
                    
                    # Prepara a coluna de simulação
                    eventos_sim['Valor Simulado'] = eventos_sim['Valor'].copy()
                    
                    # 1. Aplica o reajuste no Salário Base
                    mask_salario = eventos_sim['Evento'].str.upper() == nome_rubrica_salario.upper()
                    eventos_sim.loc[mask_salario, 'Valor Simulado'] = eventos_sim.loc[mask_salario, 'Valor'] * (1 + (reajuste_perc / 100))
                    
                    # 2. Aplica o aumento do Vale Alimentação
                    mask_va = eventos_sim['Evento'].str.upper() == nome_rubrica_va.upper()
                    if mask_va.any():
                        # Já recebe VA, apenas soma o aumento
                        eventos_sim.loc[mask_va, 'Valor Simulado'] = eventos_sim.loc[mask_va, 'Valor'] + aumento_va_fixo
                    elif aplicar_va_todos and aumento_va_fixo > 0:
                        # Não recebe VA, mas o aumento foi parametrizado para todos os ativos. Adicionamos a rubrica!
                        nova_rubrica = pd.DataFrame([{
                            'Matrícula': mat_servidor_sim,
                            'Nome': servidor_info_sim['Nome'],
                            'Tipo de Folha': 'Pagamento Mensal',
                            'Evento': nome_rubrica_va,
                            'Valor': 0.0,
                            'Valor Simulado': aumento_va_fixo
                        }])
                        eventos_sim = pd.concat([eventos_sim, nova_rubrica], ignore_index=True)

                    # Separar Proventos para exibição (Simulação afeta mais os proventos)
                    prov_sim = eventos_sim[eventos_sim['Valor Simulado'] > 0].copy()
                    desc_sim = eventos_sim[eventos_sim['Valor Simulado'] < 0].copy()
                    
                    total_prov_atual = prov_sim['Valor'].sum()
                    total_prov_simulado = prov_sim['Valor Simulado'].sum()
                    
                    total_desc_atual = desc_sim['Valor'].sum()
                    # Mantemos o desconto simulado igual ao atual por padrão. (Para atualizar imposto demandaria as faixas do IR/INSS)
                    total_desc_simulado = desc_sim['Valor Simulado'].sum() 
                    
                    liquido_atual = total_prov_atual + total_desc_atual
                    liquido_simulado = total_prov_simulado + total_desc_simulado
                    diferenca_liquida = liquido_simulado - liquido_atual

                    # Painel de Resultados do Servidor
                    col_res1, col_res2, col_res3 = st.columns(3)
                    col_res1.metric("Líquido ATUAL", f"R$ {liquido_atual:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
                    col_res2.metric("Líquido SIMULADO", f"R$ {liquido_simulado:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'), f"+ R$ {diferenca_liquida:,.2f}".replace('.', ','))
                    
                    perc_ganho = ((liquido_simulado / liquido_atual) - 1) * 100 if liquido_atual > 0 else 0
                    col_res3.metric("Aumento Real no Bolso", f"{perc_ganho:.2f}%")

                    # Tabela Comparativa de Proventos
                    st.markdown("**Comparativo Detalhado (Proventos)**")
                    
                    tabela_comparativa = prov_sim[['Evento', 'Valor', 'Valor Simulado']].copy()
                    tabela_comparativa.columns = ['Rubrica', 'Valor Atual (R$)', 'Valor Simulado (R$)']
                    
                    # Função para formatar moeda na tabela
                    def formata_moeda(val):
                        return f"R$ {val:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                    
                    tabela_comparativa['Valor Atual (R$)'] = tabela_comparativa['Valor Atual (R$)'].apply(formata_moeda)
                    tabela_comparativa['Valor Simulado (R$)'] = tabela_comparativa['Valor Simulado (R$)'].apply(formata_moeda)
                    
                    st.dataframe(tabela_comparativa, hide_index=True, use_container_width=True)
                    
                    st.caption("ℹ️ *Aviso: Esta simulação individual reflete o aumento bruto das rubricas selecionadas. Os descontos de impostos (IRRF e Previdência) foram mantidos com os valores atuais. Na vida real, o aumento do salário base pode gerar mudança de alíquota no imposto de renda, alterando ligeiramente o valor líquido final.*")


else:
    # Tela Inicial antes do Upload
    st.info("👈 Por favor, faça o upload dos arquivos 'Detalhe Funcionários' e 'Holerite' no menu lateral para iniciar o sistema.")
    st.markdown("""
    ### Bem-vindo ao Sistema Estratégico de Folha de Pagamento!
    Para utilizar esta ferramenta:
    1. Acesse o Portal da Transparência da Prefeitura.
    2. Baixe os arquivos CSV de Extração de Dados (Detalhe dos Funcionários e Holerites).
    3. Arraste-os para o painel lateral esquerdo.
    
    **O que você poderá fazer:**
    * Analisar gastos por secretaria e cargos.
    * Pesquisar o holerite aberto de qualquer servidor.
    * **Mesa de Negociação:** Simular online qual o custo em Reais que um reajuste de X% ou um aumento no vale-alimentação causará no orçamento da prefeitura.
    """)
