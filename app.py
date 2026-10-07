import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import io

# ==========================================
# CONFIGURAÇÃO DE PÁGINA E DESIGN MODERNO
# ==========================================
st.set_page_config(page_title="Painel de Cadastro SAP", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    .block-container {padding-top: 1rem; padding-bottom: 2rem;}
    h1 {color: #1E293B; font-weight: 700; font-size: 2.2rem !important; margin-bottom: 0px;}
    p {color: #64748B; font-size: 1rem; margin-top: 0px;}
    
    /* Estilização padrão para botões NÃO selecionados (Brancos com borda cinza) */
    div.stButton > button {
        height: 52px;
        font-size: 14px !important;
        font-weight: 600;
        border-radius: 8px;
        border: 1px solid #CBD5E1 !important;
        background-color: #FFFFFF !important;
        color: #475569 !important;
        transition: all 0.2s ease-in-out;
    }
    div.stButton > button:hover {
        border-color: #EF4444 !important;
        color: #1E293B !important;
        background-color: #F8FAFC !important;
    }

    /* Estilização para o botão SELECIONADO (Vermelho corporativo com letras brancas e negrito) */
    div.stButton > button[kind="primary"] {
        background-color: #EF4444 !important;
        border-color: #EF4444 !important;
        color: #FFFFFF !important;
        font-weight: 700 !important;
    }
    div.stButton > button[kind="primary"] p {
        color: #FFFFFF !important;
    }
    div.stButton > button[kind="primary"]:hover {
        background-color: #DC2626 !important;
        border-color: #DC2626 !important;
        color: #FFFFFF !important;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# CABEÇALHO EXECUTIVO (LIMPO E SEM CORTE)
# ==========================================
st.markdown("<h1>Painel de Cadastro SAP</h1>", unsafe_allow_html=True)
st.markdown("<p>Governança de Master Data & Indicadores Executivos</p>", unsafe_allow_html=True)

st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
arquivo_upload = st.file_uploader("📥 Anexe o relatório (Excel/CSV)", type=["xlsx", "csv"])

st.markdown("<hr style='margin-top: 10px; margin-bottom: 15px;'>", unsafe_allow_html=True)

if arquivo_upload is not None:
    try:
        # 1. Leitura e Preparação
        df = pd.read_csv(arquivo_upload) if arquivo_upload.name.endswith('.csv') else pd.read_excel(arquivo_upload, sheet_name=0)
        df['Criado em'] = pd.to_datetime(df['Criado em'], errors='coerce')
        df['Mes_Ano'] = df['Criado em'].dt.strftime('%Y-%m')
        
        # BUSCA DINÂMICA DA COLUNA DE HIERARQUIA
        coluna_hierarquia = None
        for col in df.columns:
            if 'hierarquia' in str(col).lower():
                coluna_hierarquia = col
                break
        
        if not coluna_hierarquia and len(df.columns) >= 8:
            coluna_hierarquia = df.columns[7]
            
        if coluna_hierarquia:
            df['Hierarquia_Status'] = df[coluna_hierarquia].astype(str).str.strip()
        else:
            df['Hierarquia_Status'] = 'HIERARQUIA OK'
        
        # 2. Regras de Negócio (Classificações)
        def classificar_hawa(texto):
            texto = str(texto).upper()
            if 'PNEU' in texto or 'PN ' in texto: return 'Pneus'
            elif 'OLEO' in texto or 'LUB' in texto: return 'Lubrificantes'
            elif 'COMBO' in texto or 'PED' in texto: return 'Acessórios'
            else: return 'Peças de Reposição'
            
        def nomear_outros(tipo):
            if tipo in ['NLAG', 'HIBE']: return f"{tipo} (Uso e Consumo)"
            elif tipo == 'ROH': return f"{tipo} (Matéria Prima/Recapagem)"
            else: return f"{tipo} (Outros)"

        df['Categoria_HAWA'] = df.apply(lambda x: classificar_hawa(x['Texto breve material']) if x['Tipo de material'] == 'HAWA' else None, axis=1)
        df['Categoria_Outros'] = df.apply(lambda x: nomear_outros(x['Tipo de material']) if x['Tipo de material'] != 'HAWA' else None, axis=1)
        df['Fornecedor regular'] = df['Fornecedor regular'].astype(str).str.strip().str.title()
        df['Fornecedor'] = df['Fornecedor'].astype(str).str.strip()
        df['Descrição Fornecedor'] = df['Descrição Fornecedor'].astype(str).str.strip()
        df['SKU'] = df['SKU'].astype(str).str.strip()

        # ==========================================
        # FILTROS GLOBAIS (Nível 0)
        # ==========================================
        with st.expander("🔍 Filtros Avançados Globais (SKU / Fornecedor)", expanded=False):
            col_f1, col_f2, col_f3 = st.columns(3)
            with col_f1:
                lista_skus = sorted(df['SKU'].unique())
                skus_selecionados = st.multiselect("📦 Filtrar por SKU:", options=lista_skus)
            with col_f2:
                lista_codigos = sorted([f for f in df['Fornecedor'].unique() if f != 'NI'])
                codigos_selecionados = st.multiselect("🔢 Código Fornecedor:", options=lista_codigos)
            with col_f3:
                lista_descricoes = sorted([f for f in df['Descrição Fornecedor'].unique() if f != 'NI'])
                descricoes_selecionadas = st.multiselect("🏢 Nome Fornecedor:", options=lista_descricoes)
        
        df_n1 = df.copy()
        if skus_selecionados: df_n1 = df_n1[df_n1['SKU'].isin(skus_selecionados)]
        if codigos_selecionados: df_n1 = df_n1[df_n1['Fornecedor'].isin(codigos_selecionados)]
        if descricoes_selecionadas: df_n1 = df_n1[df_n1['Descrição Fornecedor'].isin(descricoes_selecionadas)]

        # ==========================================
        # MOTOR DE MEMÓRIA DE CLIQUES
        # ==========================================
        if 'kpi_filter' not in st.session_state: st.session_state.kpi_filter = 'Todos'
        if 'kpi_hierarquia' not in st.session_state: st.session_state.kpi_hierarquia = 'Todos'

        mes_clicado = None
        if "chart_linha" in st.session_state:
            pts_linha = st.session_state.chart_linha.get("selection", {}).get("points", [])
            if pts_linha: mes_clicado = str(pts_linha[0].get("x"))[:7]

        cat_selecionada = None
        tipo_cat = None
        pts_hawa = st.session_state.chart_hawa.get("selection", {}).get("points", []) if "chart_hawa" in st.session_state else []
        pts_outros = st.session_state.chart_outros.get("selection", {}).get("points", []) if "chart_outros" in st.session_state else []
        
        if pts_hawa:
            cat_selecionada = pts_hawa[0].get("y")
            tipo_cat = "HAWA"
        elif pts_outros:
            cat_selecionada = pts_outros[0].get("y")
            tipo_cat = "OUTROS"

        # ==========================================
        # FUNÇÃO DE FILTRAGEM DE HIERARQUIA
        # ==========================================
        def filtrar_hierarquia(df_temp, status):
            if status == 'Dentro': 
                return df_temp[df_temp['Hierarquia_Status'].str.contains('OK', case=False, na=False)]
            elif status == 'Fora': 
                return df_temp[df_temp['Hierarquia_Status'].str.contains('Fora', case=False, na=False)]
            elif status == 'NA': 
                return df_temp[df_temp['Hierarquia_Status'].str.contains('Não|Nao|Aplica', case=False, na=False)]
            return df_temp

        # ==========================================
        # CÁLCULO DOS BOTÕES KPI
        # ==========================================
        df_kpi = df_n1.copy()
        if mes_clicado: df_kpi = df_kpi[df_kpi['Mes_Ano'].astype(str).str.contains(mes_clicado)]
        if cat_selecionada:
            if tipo_cat == "HAWA": df_kpi = df_kpi[df_kpi['Categoria_HAWA'] == cat_selecionada]
            else: df_kpi = df_kpi[df_kpi['Categoria_Outros'] == cat_selecionada]

        total_sku = len(df_kpi)
        qtd_ni = len(df_kpi[df_kpi['Fornecedor'] == 'NI'])
        qtd_regular = len(df_kpi[df_kpi['Fornecedor regular'] == 'Regular'])
        qtd_irregular = len(df_kpi[df_kpi['Fornecedor regular'] == 'Não Regular'])
        
        qtd_dentro = len(df_kpi[df_kpi['Hierarquia_Status'].str.contains('OK', case=False, na=False)])
        qtd_fora = len(df_kpi[df_kpi['Hierarquia_Status'].str.contains('Fora', case=False, na=False)])
        qtd_na = len(df_kpi[df_kpi['Hierarquia_Status'].str.contains('Não|Nao|Aplica', case=False, na=False)])

        # ==========================================
        # CONTROLES REMOTOS (BOTÕES KPI DINÂMICOS)
        # ==========================================
        st.markdown("##### 🎛️ Painel de Controle Executivo")
        
        st.caption("Acompanhamento de Fornecedores:")
        kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)
        kpi_ativo = st.session_state.kpi_filter
        
        if kpi_col1.button(f"Total Geral: {total_sku:,.0f}".replace(',','.'), type="primary" if kpi_ativo == 'Todos' else "secondary", use_container_width=True, key='btn_t'): 
            st.session_state.kpi_filter = 'Todos'; st.rerun()
        if kpi_col2.button(f"Gargalo (NI): {qtd_ni}", type="primary" if kpi_ativo == 'Gargalo' else "secondary", use_container_width=True, key='btn_g'): 
            st.session_state.kpi_filter = 'Gargalo'; st.rerun()
        if kpi_col3.button(f"Regular: {qtd_regular}", type="primary" if kpi_ativo == 'Regular' else "secondary", use_container_width=True, key='btn_r'): 
            st.session_state.kpi_filter = 'Regular'; st.rerun()
        if kpi_col4.button(f"Irregular: {qtd_irregular}", type="primary" if kpi_ativo == 'Irregular' else "secondary", use_container_width=True, key='btn_i'): 
            st.session_state.kpi_filter = 'Irregular'; st.rerun()

        st.caption("Governança de Hierarquia:")
        h_col1, h_col2, h_col3, h_col4 = st.columns(4)
        h_ativo = st.session_state.kpi_hierarquia
        
        if h_col1.button(f"Todas Hierarquias", type="primary" if h_ativo == 'Todos' else "secondary", use_container_width=True, key='btn_h_t'): 
            st.session_state.kpi_hierarquia = 'Todos'; st.rerun()
        if h_col2.button(f"Dentro (OK): {qtd_dentro}", type="primary" if h_ativo == 'Dentro' else "secondary", use_container_width=True, key='btn_h_d'): 
            st.session_state.kpi_hierarquia = 'Dentro'; st.rerun()
        if h_col3.button(f"Fora da Hierarquia: {qtd_fora}", type="primary" if h_ativo == 'Fora' else "secondary", use_container_width=True, key='btn_h_f'): 
            st.session_state.kpi_hierarquia = 'Fora'; st.rerun()
        if h_col4.button(f"Não Se Aplica: {qtd_na}", type="primary" if h_ativo == 'NA' else "secondary", use_container_width=True, key='btn_h_n'): 
            st.session_state.kpi_hierarquia = 'NA'; st.rerun()

        # ==========================================
        # ALERTAS VISUAIS DE FILTROS
        # ==========================================
        filtros_ativos = []
        if skus_selecionados or codigos_selecionados or descricoes_selecionadas: filtros_ativos.append("Filtros Manuais")
        if kpi_ativo != 'Todos': filtros_ativos.append(f"Fornecedor: {kpi_ativo}")
        if h_ativo != 'Todos': filtros_ativos.append(f"Hierarquia: {h_ativo}")
        if cat_selecionada: filtros_ativos.append(f"Categoria: {cat_selecionada}")
        if mes_clicado: filtros_ativos.append(f"Mês: {mes_clicado}")

        if filtros_ativos:
            st.success(f"🎯 **Filtros Ativos no Momento:** {' | '.join(filtros_ativos)}")
        else:
            st.info("💡 Exibindo Visão Consolidada Geral.")

        # ==========================================
        # PREPARAÇÃO DAS BASES FINAIS
        # ==========================================
        df_barras = df_n1.copy()
        if mes_clicado: df_barras = df_barras[df_barras['Mes_Ano'].astype(str).str.contains(mes_clicado)]
        if kpi_ativo == 'Gargalo': df_barras = df_barras[df_barras['Fornecedor'] == 'NI']
        elif kpi_ativo == 'Regular': df_barras = df_barras[df_barras['Fornecedor regular'] == 'Regular']
        elif kpi_ativo == 'Irregular': df_barras = df_barras[df_barras['Fornecedor regular'] == 'Não Regular']
        df_barras = filtrar_hierarquia(df_barras, h_ativo)

        df_linha = df_n1.copy()
        if cat_selecionada:
            if tipo_cat == "HAWA": df_linha = df_linha[df_linha['Categoria_HAWA'] == cat_selecionada]
            else: df_linha = df_linha[df_linha['Categoria_Outros'] == cat_selecionada]
        if kpi_ativo == 'Gargalo': df_linha = df_linha[df_linha['Fornecedor'] == 'NI']
        elif kpi_ativo == 'Regular': df_linha = df_linha[df_linha['Fornecedor regular'] == 'Regular']
        elif kpi_ativo == 'Irregular': df_linha = df_linha[df_linha['Fornecedor regular'] == 'Não Regular']
        df_linha = filtrar_hierarquia(df_linha, h_ativo)

        df_final = df_linha.copy()
        if mes_clicado: df_final = df_final[df_final['Mes_Ano'].astype(str).str.contains(mes_clicado)]

        # ==========================================
        # GRÁFICOS COM MÉTRICAS DE TOTAIS EM DESTAQUE
        # ==========================================
        c_hawa, c_outros = st.columns(2)
        
        with c_hawa:
            df_hawa = df_barras[df_barras['Tipo de material'] == 'HAWA']
            total_hawa = len(df_hawa)
            
            st.metric("🛒 Total SKUs - Revenda (HAWA)", f"{total_hawa:,.0f}".replace(',','.'))
            df_cat_hawa = df_hawa.groupby('Categoria_HAWA').size().reset_index(name='Quantidade').sort_values('Quantidade')
            
            fig_hawa = px.bar(df_cat_hawa, x='Quantidade', y='Categoria_HAWA', orientation='h', text='Quantidade',
                             title=f"Distribuição Revenda (HAWA) [Total: {total_hawa}]", color_discrete_sequence=['#2563EB'])
            fig_hawa.update_layout(height=240, margin=dict(l=10, r=10, t=35, b=10),
                                   xaxis=dict(range=[0, (df_cat_hawa['Quantidade'].max() if not df_cat_hawa.empty else 10) * 1.25]), 
                                   paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", xaxis_title="", yaxis_title="",
                                   font=dict(family="sans-serif", size=12, color="#334155"))
            fig_hawa.update_traces(textposition="outside")
            st.plotly_chart(fig_hawa, use_container_width=True, on_select="rerun", key="chart_hawa")
            
        with c_outros:
            df_outros = df_barras[df_barras['Tipo de material'] != 'HAWA']
            total_outros = len(df_outros)
            
            st.metric("⚙️ Total SKUs - Operação Interna", f"{total_outros:,.0f}".replace(',','.'))
            df_cat_outros = df_outros.groupby('Categoria_Outros').size().reset_index(name='Quantidade').sort_values('Quantidade')
            
            fig_outros = px.bar(df_cat_outros, x='Quantidade', y='Categoria_Outros', orientation='h', text='Quantidade',
                             title=f"Distribuição Operação Interna [Total: {total_outros}]", color_discrete_sequence=['#D97706'])
            fig_outros.update_layout(height=240, margin=dict(l=10, r=10, t=35, b=10),
                                     xaxis=dict(range=[0, (df_cat_outros['Quantidade'].max() if not df_cat_outros.empty else 10) * 1.25]), 
                                     paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", xaxis_title="", yaxis_title="",
                                     font=dict(family="sans-serif", size=12, color="#334155"))
            fig_outros.update_traces(textposition="outside")
            st.plotly_chart(fig_outros, use_container_width=True, on_select="rerun", key="chart_outros")

        # Gráfico de Evolução Moderno
        df_mes = df_linha.groupby('Mes_Ano').size().reset_index(name='Quantidade').sort_values('Mes_Ano')
        media_mensal = df_mes['Quantidade'].mean() if not df_mes.empty else 0
        
        fig_mes = px.line(df_mes, x='Mes_Ano', y='Quantidade', text='Quantidade', markers=True,
                          title="📉 Evolução de Criação Mês a Mês", color_discrete_sequence=['#0D9488'])
        fig_mes.update_traces(textposition="bottom right", marker=dict(size=10, line=dict(width=2, color='#0F766E')), line=dict(width=3))
        fig_mes.add_hline(y=media_mensal, line_dash="dot", line_color="#EF4444", annotation_text=f"Média: {media_mensal:.0f}", annotation_position="top left")
        fig_mes.update_xaxes(type='category')
        fig_mes.update_layout(height=280, margin=dict(l=10, r=10, t=35, b=10),
                              paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", xaxis_title="", hovermode="closest",
                              font=dict(family="sans-serif", size=12, color="#334155"))
        st.plotly_chart(fig_mes, use_container_width=True, on_select="rerun", key="chart_linha")

        # ==========================================
        # TABELA DETALHADA E BOTÃO DE EXPORTAÇÃO
        # ==========================================
        st.markdown("---")
        
        col_t1, col_t2 = st.columns([3, 1])
        with col_t1:
            st.subheader("📋 Detalhamento na Raiz (Dados Filtrados)")
        with col_t2:
            # Conversão para Excel utilizando o motor nativo openpyxl
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_export = df_final.sort_values(by='Criado em', ascending=False).drop(columns=['Categoria_HAWA', 'Categoria_Outros', 'Hierarquia_Status'], errors='ignore')
                df_export['Criado em'] = df_export['Criado em'].dt.strftime('%d/%m/%Y')
                df_export.to_excel(writer, index=False, sheet_name='Dados_Filtrados')
            processed_data = output.getvalue()
            
            st.download_button(
                label="📥 Exportar para Excel (.xlsx)",
                data=processed_data,
                file_name=f"detalhamento_sap_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

        df_exibicao = df_final.sort_values(by='Criado em', ascending=False).drop(columns=['Categoria_HAWA', 'Categoria_Outros', 'Hierarquia_Status'], errors='ignore')
        df_exibicao['Criado em'] = df_exibicao['Criado em'].dt.strftime('%d/%m/%Y')
        st.dataframe(df_exibicao, use_container_width=True, hide_index=True, height=350)

    except Exception as e:
        st.error(f"Erro técnico ao processar o ficheiro: {e}")
else:
    st.info("👆 Anexe o seu ficheiro XLSX no topo da página para iniciar a análise corporativa.")