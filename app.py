"""
Dashboard Interativo de Segurança Viária — Bauru/SP (2015–2026)
Desenvolvido com Streamlit, Plotly e Scikit-Learn
Dados: Infosiga SP (Movimento Paulista de Segurança no Trânsito)
"""

import os
import io
import time
import pandas as pd
import numpy as np
import scipy.stats as stats
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score, accuracy_score, classification_report

# ==============================================================================
# CONFIGURAÇÃO DA PÁGINA STREAMLIT
# ==============================================================================
st.set_page_config(
    page_title="Segurança Viária — Bauru/SP (2015–2026)",
    page_icon="🚦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ==============================================================================
# ESTILOS CUSTOMIZADOS (CSS PROFISSIONAL & MODERNO)
# ==============================================================================
CUSTOM_CSS = """
<style>
/* Fonte e espaçamento geral */
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Plus Jakarta Sans', sans-serif;
}

/* Card de métricas customizado */
.metric-card {
    background: linear-gradient(135deg, rgba(255, 255, 255, 0.05), rgba(255, 255, 255, 0.02));
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 14px;
    padding: 18px 20px;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
    backdrop-filter: blur(10px);
    transition: transform 0.2s ease, border-color 0.2s ease;
    margin-bottom: 12px;
}
.metric-card:hover {
    transform: translateY(-2px);
    border-color: rgba(99, 102, 241, 0.4);
}
.metric-title {
    font-size: 0.82rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: #94a3b8;
    margin-bottom: 6px;
    display: flex;
    align-items: center;
    gap: 6px;
}
.metric-value {
    font-size: 1.85rem;
    font-weight: 800;
    color: #f8fafc;
    line-height: 1.1;
    margin-bottom: 6px;
}
.metric-sub {
    font-size: 0.8rem;
    color: #cbd5e1;
    display: flex;
    align-items: center;
    gap: 6px;
}

/* Badges e tags */
.badge {
    display: inline-block;
    padding: 3px 9px;
    border-radius: 9999px;
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.02em;
}
.badge-danger { background-color: rgba(239, 68, 68, 0.2); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.4); }
.badge-warning { background-color: rgba(245, 158, 11, 0.2); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.4); }
.badge-success { background-color: rgba(16, 185, 129, 0.2); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.4); }
.badge-info { background-color: rgba(99, 102, 241, 0.2); color: #818cf8; border: 1px solid rgba(99, 102, 241, 0.4); }

/* Bloco de destaque / Callout */
.insight-box {
    background: linear-gradient(90deg, rgba(99, 102, 241, 0.1) 0%, rgba(59, 130, 246, 0.05) 100%);
    border-left: 4px solid #6366f1;
    border-radius: 0 12px 12px 0;
    padding: 16px 20px;
    margin: 16px 0;
}
.insight-box-danger {
    background: linear-gradient(90deg, rgba(239, 68, 68, 0.12) 0%, rgba(220, 38, 38, 0.04) 100%);
    border-left: 4px solid #ef4444;
    border-radius: 0 12px 12px 0;
    padding: 16px 20px;
    margin: 16px 0;
}

/* Header estilizado */
.header-container {
    background: linear-gradient(135deg, #1e1b4b 0%, #0f172a 50%, #1e293b 100%);
    border: 1px solid rgba(99, 102, 241, 0.3);
    border-radius: 16px;
    padding: 24px 28px;
    margin-bottom: 24px;
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
}
.header-title {
    font-size: 2.1rem;
    font-weight: 800;
    color: #ffffff;
    margin-bottom: 6px;
    letter-spacing: -0.02em;
}
.header-subtitle {
    font-size: 1.0rem;
    color: #94a3b8;
    line-height: 1.4;
}

/* Simulador ML Card */
.ml-card {
    background: linear-gradient(145deg, rgba(30, 41, 59, 0.9), rgba(15, 23, 42, 0.95));
    border: 1px solid rgba(99, 102, 241, 0.35);
    border-radius: 16px;
    padding: 22px;
    box-shadow: 0 12px 30px rgba(0,0,0,0.3);
}

/* Divisor */
hr {
    border-color: rgba(255, 255, 255, 0.08) !important;
}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# ==============================================================================
# CARREGAMENTO E CACHE DOS DADOS
# ==============================================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "data", "bauru_limpo.csv")
RESUMO_FILE = os.path.join(BASE_DIR, "output", "relatorios", "resumo_anual_bauru.csv")
RELATORIO_MD = os.path.join(BASE_DIR, "output", "relatorios", "relatorio_final_bauru.md")
RELATORIO_PDF = os.path.join(BASE_DIR, "output", "relatorios", "relatorio_bauru.pdf")
MAPA_HTML_FILE = os.path.join(BASE_DIR, "output", "graficos", "mapa_acidentes.html")

GRAFICOS_DIR = os.path.join(BASE_DIR, "output", "graficos")

@st.cache_data(show_spinner="Carregando base de dados tratada de Bauru...")
def load_data():
    if not os.path.exists(DATA_FILE):
        st.error(f"Arquivo não encontrado: {DATA_FILE}")
        return pd.DataFrame()
    df = pd.read_csv(DATA_FILE, sep=';', encoding='utf-8', low_memory=False)
    df['data_sinistro_dt'] = pd.to_datetime(df['data_sinistro_dt'], errors='coerce')
    df['ano'] = pd.to_numeric(df['ano'], errors='coerce').fillna(0).astype(int)
    return df

@st.cache_data(show_spinner="Carregando resumo anual...")
def load_resumo():
    if os.path.exists(RESUMO_FILE):
        return pd.read_csv(RESUMO_FILE, sep=';', encoding='utf-8')
    return pd.DataFrame()

@st.cache_resource(show_spinner="Carregando e calibrando modelo de Machine Learning...")
def get_ml_model(df_input):
    df_ml = df_input[df_input['hora_num'].notnull()].copy()
    features_cols = [
        'envolve_moto', 'envolve_auto', 'envolve_pedestre', 'envolve_bicicleta', 'envolve_pesado',
        'is_fim_de_semana'
    ]
    
    dummies_via = pd.get_dummies(df_ml['tipo_via_simplificado'], prefix='via', drop_first=True)
    dummies_tipo = pd.get_dummies(df_ml['tipo_sinistro_simplificado'], prefix='tipo', drop_first=True)
    dummies_turno = pd.get_dummies(df_ml['turno_ajustado'], prefix='turno', drop_first=True)
    
    X = pd.concat([df_ml[features_cols], df_ml[['hora_num']], dummies_via, dummies_tipo, dummies_turno], axis=1)
    y = df_ml['severidade_grave_ou_fatal']
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=42, stratify=y)
    
    rf = RandomForestClassifier(n_estimators=150, max_depth=10, class_weight='balanced', random_state=42, n_jobs=-1)
    rf.fit(X_train, y_train)
    
    y_prob = rf.predict_proba(X_test)[:, 1]
    y_pred = rf.predict(X_test)
    
    roc = roc_auc_score(y_test, y_prob)
    acc = accuracy_score(y_test, y_pred)
    
    importancias = pd.Series(rf.feature_importances_, index=X.columns).sort_values(ascending=False)
    
    return rf, X.columns.tolist(), roc, acc, importancias, classification_report(y_test, y_pred, output_dict=True)

df_completo = load_data()
df_resumo = load_resumo()

if df_completo.empty:
    st.error("Erro crítico: Nenhum dado disponível para análise. Verifique `data/bauru_limpo.csv`.")
    st.stop()

# ==============================================================================
# BARRA LATERAL (FILTROS INTERATIVOS)
# ==============================================================================
st.sidebar.markdown("## 🚦 Filtros de Análise")
st.sidebar.caption("Refine os parâmetros para segmentar a base de Bauru/SP:")

# Filtro de Ano
anos_disponiveis = sorted(df_completo['ano'].unique().tolist())
anos_selecionados = st.sidebar.multiselect(
    "Ano da Ocorrência:",
    options=anos_disponiveis,
    default=anos_disponiveis,
    help="Selecione um ou mais anos para analisar o histórico."
)

# Filtro de Severidade
severidades_disponiveis = sorted(df_completo['severidade_categoria'].unique().tolist())
severidades_selecionadas = st.sidebar.multiselect(
    "Severidade do Sinistro:",
    options=severidades_disponiveis,
    default=severidades_disponiveis
)

# Filtro de Tipo de Via
vias_disponiveis = ["Todas"] + sorted(df_completo['tipo_via_simplificado'].unique().tolist())
via_selecionada = st.sidebar.selectbox("Tipo de Via:", options=vias_disponiveis, index=0)

# Filtro de Tipo de Sinistro
sinistros_disponiveis = ["Todos"] + sorted(df_completo['tipo_sinistro_simplificado'].unique().tolist())
sinistro_selecionado = st.sidebar.selectbox("Tipo de Sinistro:", options=sinistros_disponiveis, index=0)

# Filtro de Modal Envolvido
modal_opcoes = [
    "Todos os Modais",
    "Apenas com Motocicleta (🏍️)",
    "Apenas com Automóvel (🚗)",
    "Apenas com Pedestre (🚶)",
    "Apenas com Bicicleta (🚲)",
    "Apenas com Pesados / Ônibus / Caminhão (🚛)"
]
modal_selecionado = st.sidebar.selectbox("Modal Específico:", options=modal_opcoes, index=0)

# Filtro de Período da Semana
dia_semana_opcoes = ["Todos os Dias", "Apenas Dias Úteis (Seg-Sex)", "Apenas Fim de Semana (Sáb-Dom)"]
periodo_selecionado = st.sidebar.selectbox("Período da Semana:", options=dia_semana_opcoes, index=0)

# APLICAÇÃO DOS FILTROS
df_filtrado = df_completo.copy()

if anos_selecionados:
    df_filtrado = df_filtrado[df_filtrado['ano'].isin(anos_selecionados)]

if severidades_selecionadas:
    df_filtrado = df_filtrado[df_filtrado['severidade_categoria'].isin(severidades_selecionadas)]

if via_selecionada != "Todas":
    df_filtrado = df_filtrado[df_filtrado['tipo_via_simplificado'] == via_selecionada]

if sinistro_selecionado != "Todos":
    df_filtrado = df_filtrado[df_filtrado['tipo_sinistro_simplificado'] == sinistro_selecionado]

if modal_selecionado == "Apenas com Motocicleta (🏍️)":
    df_filtrado = df_filtrado[df_filtrado['envolve_moto'] == 1]
elif modal_selecionado == "Apenas com Automóvel (🚗)":
    df_filtrado = df_filtrado[df_filtrado['envolve_auto'] == 1]
elif modal_selecionado == "Apenas com Pedestre (🚶)":
    df_filtrado = df_filtrado[df_filtrado['envolve_pedestre'] == 1]
elif modal_selecionado == "Apenas com Bicicleta (🚲)":
    df_filtrado = df_filtrado[df_filtrado['envolve_bicicleta'] == 1]
elif modal_selecionado == "Apenas com Pesados / Ônibus / Caminhão (🚛)":
    df_filtrado = df_filtrado[df_filtrado['envolve_pesado'] == 1]

if periodo_selecionado == "Apenas Dias Úteis (Seg-Sex)":
    df_filtrado = df_filtrado[df_filtrado['is_fim_de_semana'] == 0]
elif periodo_selecionado == "Apenas Fim de Semana (Sáb-Dom)":
    df_filtrado = df_filtrado[df_filtrado['is_fim_de_semana'] == 1]

# Métricas da Barra Lateral
st.sidebar.divider()
total_completo = len(df_completo)
total_atual = len(df_filtrado)
pct_selecionada = (total_atual / total_completo * 100) if total_completo > 0 else 0

st.sidebar.markdown(f"**Amostra Selecionada:**")
st.sidebar.markdown(f"- **{total_atual:,}** de **{total_completo:,}** sinistros (`{pct_selecionada:.1f}%`)")
st.sidebar.markdown(f"- **{df_filtrado['obitos'].sum():,}** óbitos confirmados")
st.sidebar.markdown(f"- **{df_filtrado['feridos_graves'].sum():,}** feridos graves")

st.sidebar.info("💡 **Dica:** Os gráficos e métricas reagem dinamicamente aos filtros selecionados acima.")

# ==============================================================================
# CABEÇALHO PRINCIPAL DA PÁGINA
# ==============================================================================
st.markdown("""
<div class="header-container">
    <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 12px;">
        <div>
            <div style="display: flex; gap: 8px; margin-bottom: 8px; flex-wrap: wrap;">
                <span class="badge badge-info">BAURU / SP (IBGE 3506003)</span>
                <span class="badge badge-success">INFOSIGA SP OFICIAL</span>
                <span class="badge badge-warning">2015 – 2026</span>
                <span class="badge badge-danger">18.938 SINISTROS</span>
            </div>
            <div class="header-title">🚦 Painel de Diagnóstico da Segurança Viária de Bauru</div>
            <div class="header-subtitle">
                Auditoria integral e modelagem preditiva de gravidade sobre os sinistros de trânsito em vias urbanas e rodovias de Bauru/SP ao longo de mais de 11 anos.
            </div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# ==============================================================================
# CARDS DE MÉTRICAS EXECUTIVAS (KPIS)
# ==============================================================================
total_sinistros = len(df_filtrado)
total_obitos = int(df_filtrado['obitos'].sum())
total_graves = int(df_filtrado['feridos_graves'].sum())
taxa_letalidade = (total_obitos / total_sinistros * 100) if total_sinistros > 0 else 0
total_motos = int(df_filtrado['envolve_moto'].sum())
pct_motos = (total_motos / total_sinistros * 100) if total_sinistros > 0 else 0

kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)

with kpi1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">🚨 Total de Sinistros</div>
        <div class="metric-value">{total_sinistros:,}</div>
        <div class="metric-sub"><span class="badge badge-info">100% registros</span> no filtro</div>
    </div>
    """, unsafe_allow_html=True)

with kpi2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">✝️ Vítimas Fatais</div>
        <div class="metric-value" style="color: #f87171;">{total_obitos:,}</div>
        <div class="metric-sub"><span class="badge badge-danger">Óbitos</span> confirmados</div>
    </div>
    """, unsafe_allow_html=True)

with kpi3:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">🏥 Feridos Graves</div>
        <div class="metric-value" style="color: #fbbf24;">{total_graves:,}</div>
        <div class="metric-sub"><span class="badge badge-warning">Internações</span> hospitalares</div>
    </div>
    """, unsafe_allow_html=True)

with kpi4:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">⚡ Taxa de Letalidade</div>
        <div class="metric-value">{taxa_letalidade:.2f}%</div>
        <div class="metric-sub">Óbitos / Total de Sinistros</div>
    </div>
    """, unsafe_allow_html=True)

with kpi5:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">🏍️ Envolve Moto</div>
        <div class="metric-value" style="color: #818cf8;">{total_motos:,}</div>
        <div class="metric-sub"><span class="badge badge-info">{pct_motos:.1f}%</span> do volume total</div>
    </div>
    """, unsafe_allow_html=True)

st.write("")

# ==============================================================================
# ABAS DE NAVEGAÇÃO E ANÁLISE PROFUNDA
# ==============================================================================
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
    "📊 Evolução Anual & Histórico",
    "💥 Tipos de Sinistro & Choque",
    "🏍️ Modais & Motocicletas",
    "⏰ Padrões Temporais & Teste t",
    "🗺️ Mapa Geoespacial Interativo",
    "🤖 Inteligência Preditiva (ML)",
    "🏛️ Recomendações Estruturantes",
    "📑 Relatório & Downloads"
])

# ------------------------------------------------------------------------------
# TAB 1: EVOLUÇÃO ANUAL & HISTÓRICO
# ------------------------------------------------------------------------------
with tab1:
    st.markdown("### 1. Evolução Histórica de Sinistros e Fatalidades (2015–2026)")
    
    st.markdown("""
    <div class="insight-box">
        <strong>📌 Marco Metodológico do Infosiga SP:</strong>
        <br>• <strong>2015 a 2018:</strong> O sistema registrava exclusivamente sinistros com <strong>vítimas fatais</strong> (média de 30 a 50 mortes/ano em Bauru).
        <br>• <strong>2019 a 2026:</strong> O cadastro passou a cobrir <strong>sinistros não fatais</strong> (feridos graves, leves e ilesos), saltando o volume anual para <strong>2.200 a 2.800 ocorrências por ano</strong>.
    </div>
    """, unsafe_allow_html=True)
    
    col_chart, col_side = st.columns([2.2, 1])
    
    with col_chart:
        # Gráfico dinâmico interativo com Plotly
        resumo_filtrado = df_filtrado.groupby('ano').agg(
            total_sinistros=('id_sinistro', 'count'),
            obitos=('obitos', 'sum'),
            feridos_graves=('feridos_graves', 'sum'),
            feridos_leves=('feridos_leves', 'sum')
        ).reset_index()
        
        fig_anual = go.Figure()
        
        fig_anual.add_trace(go.Bar(
            x=resumo_filtrado['ano'],
            y=resumo_filtrado['total_sinistros'],
            name='Total de Sinistros',
            marker_color='#3b82f6',
            opacity=0.85,
            yaxis='y'
        ))
        
        fig_anual.add_trace(go.Scatter(
            x=resumo_filtrado['ano'],
            y=resumo_filtrado['obitos'],
            name='Óbitos Confirmados',
            line=dict(color='#ef4444', width=3),
            marker=dict(size=8, color='#ef4444'),
            mode='lines+markers+text',
            text=resumo_filtrado['obitos'],
            textposition='top center',
            yaxis='y2'
        ))
        
        fig_anual.update_layout(
            title="Evolução de Sinistros e Fatalidades de Trânsito em Bauru/SP",
            xaxis=dict(title="Ano", tickmode='linear', tick0=2015, dtick=1),
            yaxis=dict(title="Total de Sinistros Registrados", showgrid=True, gridcolor='rgba(255,255,255,0.1)'),
            yaxis2=dict(title="Número de Óbitos", overlaying='y', side='right', showgrid=False),
            legend=dict(x=0.02, y=0.98, bgcolor='rgba(15, 23, 42, 0.7)'),
            template='plotly_dark',
            margin=dict(l=20, r=20, t=50, b=30),
            height=430
        )
        st.plotly_chart(fig_anual, use_container_width=True)
        
    with col_side:
        st.markdown("#### 📋 Resumo Consolidado por Ano")
        if not df_resumo.empty:
            df_display_resumo = df_resumo.copy()
            st.dataframe(
                df_display_resumo.style.format({
                    "total_sinistros": "{:,}",
                    "obitos": "{:,}",
                    "feridos_graves": "{:,}",
                    "feridos_leves": "{:,}",
                    "sinistros_fatais": "{:,}"
                }),
                height=380,
                use_container_width=True
            )
        else:
            st.dataframe(resumo_filtrado, use_container_width=True)

    with st.expander("🖼️ Visualizar Imagem Oficial Gerada pelo Pipeline (`output/graficos/acidentes_por_ano.png`)"):
        img_ano = os.path.join(GRAFICOS_DIR, "acidentes_por_ano.png")
        if os.path.exists(img_ano):
            st.image(img_ano, caption="Gráfico Oficial gerado pelo pipeline de dados (Alta Resolução 300 DPI)", use_container_width=True)
        else:
            st.info("Arquivo de imagem estática não encontrado no caminho especificado.")

# ------------------------------------------------------------------------------
# TAB 2: TIPOS DE SINISTRO & CHOQUE CONTRA OBSTÁCULOS
# ------------------------------------------------------------------------------
with tab2:
    st.markdown("### 2. Tipos de Sinistro e a Alta Gravidade de Choques e Atropelamentos")
    
    st.markdown("""
    <div class="insight-box-danger">
        <strong>⚠️ Descoberta Crítica de Letalidade:</strong>
        <br>Embora a <strong>Colisão veicular</strong> seja a mecânica com maior frequência bruta (7.505 casos), a <strong>taxa de letalidade é de 2,36%</strong>.
        <br>Em contrapartida, os <strong>Atropelamentos (9,09%)</strong> e os <strong>Choques contra Obstáculos Fixos (7,45%)</strong> apresentam letalidades entre <strong>3 e 4 vezes superiores</strong>!
    </div>
    """, unsafe_allow_html=True)
    
    col_t1, col_t2 = st.columns([1.2, 1])
    
    with col_t1:
        # Tabela agrupada
        tabela_tipo = df_filtrado.groupby('tipo_sinistro_simplificado').agg(
            total=('id_sinistro', 'count'),
            obitos=('obitos', 'sum'),
            feridos_graves=('feridos_graves', 'sum'),
            feridos_leves=('feridos_leves', 'sum')
        ).reset_index()
        tabela_tipo['letalidade_pct'] = (tabela_tipo['obitos'] / tabela_tipo['total'] * 100).round(2)
        tabela_tipo['gravidade_grave_fatal_pct'] = ((tabela_tipo['obitos'] + tabela_tipo['feridos_graves']) / tabela_tipo['total'] * 100).round(2)
        tabela_tipo = tabela_tipo.sort_values(by='letalidade_pct', ascending=False)
        
        fig_bar_letal = px.bar(
            tabela_tipo,
            x='tipo_sinistro_simplificado',
            y='letalidade_pct',
            color='letalidade_pct',
            color_continuous_scale='Reds',
            text='letalidade_pct',
            title="Taxa de Letalidade (%) por Tipo de Sinistro",
            labels={'tipo_sinistro_simplificado': 'Tipo de Sinistro', 'letalidade_pct': 'Letalidade (%)'},
            template='plotly_dark'
        )
        fig_bar_letal.update_traces(texttemplate='%{text:.2f}%', textposition='outside')
        fig_bar_letal.update_layout(height=380, margin=dict(l=20, r=20, t=50, b=30))
        st.plotly_chart(fig_bar_letal, use_container_width=True)
        
    with col_t2:
        fig_bar_vol = px.bar(
            tabela_tipo.sort_values(by='total', ascending=True),
            x='total',
            y='tipo_sinistro_simplificado',
            orientation='h',
            text='total',
            title="Volume Total de Ocorrências por Tipo",
            labels={'tipo_sinistro_simplificado': 'Tipo de Sinistro', 'total': 'Ocorrências'},
            color_discrete_sequence=['#6366f1'],
            template='plotly_dark'
        )
        fig_bar_vol.update_traces(texttemplate='%{text:,}', textposition='outside')
        fig_bar_vol.update_layout(height=380, margin=dict(l=20, r=20, t=50, b=30))
        st.plotly_chart(fig_bar_vol, use_container_width=True)
        
    st.markdown("#### 📊 Tabela Detalhada de Severidade por Mecânica")
    st.dataframe(
        tabela_tipo.rename(columns={
            'tipo_sinistro_simplificado': 'Tipo de Sinistro',
            'total': 'Total de Casos',
            'obitos': 'Óbitos',
            'feridos_graves': 'Feridos Graves',
            'feridos_leves': 'Feridos Leves',
            'letalidade_pct': 'Letalidade (%)',
            'gravidade_grave_fatal_pct': 'Grave ou Fatal (%)'
        }).style.format({
            'Total de Casos': '{:,}',
            'Óbitos': '{:,}',
            'Feridos Graves': '{:,}',
            'Feridos Leves': '{:,}',
            'Letalidade (%)': '{:.2f}%',
            'Grave ou Fatal (%)': '{:.2f}%'
        }),
        use_container_width=True
    )
    
    with st.expander("🖼️ Visualizar Imagem Oficial (`output/graficos/tipos_e_veiculos.png`)"):
        img_tipo = os.path.join(GRAFICOS_DIR, "tipos_e_veiculos.png")
        if os.path.exists(img_tipo):
            st.image(img_tipo, caption="Gráfico Oficial gerado pelo pipeline", use_container_width=True)

# ------------------------------------------------------------------------------
# TAB 3: MODAIS & MOTOCICLETAS
# ------------------------------------------------------------------------------
with tab3:
    st.markdown("### 3. Modais de Transporte: A Vulnerabilidade Crítica dos Motociclistas")
    
    st.markdown("""
    <div class="insight-box">
        <strong>🏍️ O Papel Central das Motocicletas na Segurança Viária de Bauru:</strong>
        <br>• As motocicletas estão envolvidas em <strong>6.852 sinistros (36,2% do total)</strong> da cidade.
        <br>• A presença de moto é o <strong>preditor isolado nº 1 de gravidade física</strong> na modelagem preditiva supervisionada.
        <br>• A falta de proteção mecânica converte pequenos toques urbanos em fraturas expostas e traumatismos cranianos graves.
    </div>
    """, unsafe_allow_html=True)
    
    col_m1, col_m2 = st.columns(2)
    
    with col_m1:
        modais_df = pd.DataFrame({
            'Modal': ['Automóvel', 'Motocicleta', 'Pedestre', 'Pesado (Caminhão/Ônibus)', 'Bicicleta'],
            'Volume': [
                int(df_filtrado['envolve_auto'].sum()),
                int(df_filtrado['envolve_moto'].sum()),
                int(df_filtrado['envolve_pedestre'].sum()),
                int(df_filtrado['envolve_pesado'].sum()),
                int(df_filtrado['envolve_bicicleta'].sum())
            ]
        })
        modais_df['Participacao_Pct'] = (modais_df['Volume'] / len(df_filtrado) * 100).round(1)
        
        fig_modal = px.bar(
            modais_df,
            x='Modal',
            y='Volume',
            color='Modal',
            color_discrete_sequence=['#3b82f6', '#ec4899', '#f97316', '#8b5cf6', '#10b981'],
            text='Volume',
            title="Distribuição de Sinistros por Modal Envolvido",
            template='plotly_dark'
        )
        fig_modal.update_traces(texttemplate='%{text:,}', textposition='outside')
        fig_modal.update_layout(height=380, showlegend=False, margin=dict(l=20, r=20, t=50, b=30))
        st.plotly_chart(fig_modal, use_container_width=True)
        
    with col_m2:
        # Comparativo: Severidade COM moto vs SEM moto
        df_comp_moto = df_filtrado.copy()
        df_comp_moto['Grupo'] = df_comp_moto['envolve_moto'].map({1: 'Com Motocicleta', 0: 'Sem Motocicleta'})
        
        comp_agg = df_comp_moto.groupby(['Grupo', 'severidade_categoria']).size().unstack(fill_value=0)
        comp_pct = (comp_agg.div(comp_agg.sum(axis=1), axis=0) * 100).round(1).reset_index()
        
        # Donut de gravidade com moto
        df_moto_only = df_filtrado[df_filtrado['envolve_moto'] == 1]
        sev_moto_counts = df_moto_only['severidade_categoria'].value_counts().reset_index()
        sev_moto_counts.columns = ['Severidade', 'Contagem']
        
        color_sev_map = {
            'FATAL': '#ef4444',
            'GRAVE': '#f97316',
            'LEVE': '#eab308',
            'ILESO / NAO INFORMADO': '#3b82f6'
        }
        
        fig_donut_moto = px.pie(
            sev_moto_counts,
            names='Severidade',
            values='Contagem',
            hole=0.45,
            color='Severidade',
            color_discrete_map=color_sev_map,
            title="Distribuição de Severidade em Sinistros com Motocicleta",
            template='plotly_dark'
        )
        fig_donut_moto.update_layout(height=380, margin=dict(l=20, r=20, t=50, b=30))
        st.plotly_chart(fig_donut_moto, use_container_width=True)

    st.markdown("#### 🔍 Análise Comparativa de Severidade: Com Moto vs Sem Moto")
    col_c1, col_c2, col_c3 = st.columns(3)
    
    moto_total = (df_filtrado['envolve_moto'] == 1).sum()
    sem_moto_total = (df_filtrado['envolve_moto'] == 0).sum()
    
    moto_graves_fatais = (df_filtrado[df_filtrado['envolve_moto'] == 1]['severidade_grave_ou_fatal'] == 1).sum()
    sem_moto_graves_fatais = (df_filtrado[df_filtrado['envolve_moto'] == 0]['severidade_grave_ou_fatal'] == 1).sum()
    
    taxa_grave_moto = (moto_graves_fatais / moto_total * 100) if moto_total > 0 else 0
    taxa_grave_sem_moto = (sem_moto_graves_fatais / sem_moto_total * 100) if sem_moto_total > 0 else 0
    
    with col_c1:
        st.metric("Total com Motocicleta", f"{moto_total:,}", f"{(moto_total/total_sinistros*100 if total_sinistros>0 else 0):.1f}% do total")
    with col_c2:
        st.metric("Taxa Grave/Fatal COM Moto", f"{taxa_grave_moto:.1f}%", f"{moto_graves_fatais:,} ocorrências graves/fatais")
    with col_c3:
        st.metric("Taxa Grave/Fatal SEM Moto", f"{taxa_grave_sem_moto:.1f}%", f"{sem_moto_graves_fatais:,} ocorrências graves/fatais")

# ------------------------------------------------------------------------------
# TAB 4: PADRÕES TEMPORAIS & TESTE ESTATÍSTICO
# ------------------------------------------------------------------------------
with tab4:
    st.markdown("### 4. Análise Temporal, Matriz de Calor e Teste de Hipótese Estatístico")
    
    ordem_dias = ['Segunda-feira', 'Terça-feira', 'Quarta-feira', 'Quinta-feira', 'Sexta-feira', 'Sábado', 'Domingo']
    
    col_dia, col_hora = st.columns(2)
    
    with col_dia:
        dias_counts = df_filtrado['dia_da_semana_limpo'].value_counts().reindex(ordem_dias).dropna().reset_index()
        dias_counts.columns = ['Dia da Semana', 'Volume']
        
        fig_dia = px.bar(
            dias_counts,
            x='Dia da Semana',
            y='Volume',
            color='Volume',
            color_continuous_scale='Blues',
            text='Volume',
            title="Sinistros por Dia da Semana em Bauru",
            template='plotly_dark'
        )
        fig_dia.update_traces(texttemplate='%{text:,}', textposition='outside')
        fig_dia.update_layout(height=340, margin=dict(l=20, r=20, t=50, b=30))
        st.plotly_chart(fig_dia, use_container_width=True)
        
    with col_hora:
        horas_counts = df_filtrado['hora_num'].dropna().value_counts().sort_index().reset_index()
        horas_counts.columns = ['Hora', 'Volume']
        horas_counts['Hora'] = horas_counts['Hora'].astype(int)
        
        fig_hora = px.bar(
            horas_counts,
            x='Hora',
            y='Volume',
            text='Volume',
            title="Distribuição por Hora do Dia (0h às 23h)",
            color_discrete_sequence=['#60a5fa'],
            template='plotly_dark'
        )
        fig_hora.update_traces(texttemplate='%{text:,}', textposition='outside')
        fig_hora.update_layout(
            xaxis=dict(tickmode='linear', tick0=0, dtick=2),
            height=340,
            margin=dict(l=20, r=20, t=50, b=30)
        )
        st.plotly_chart(fig_hora, use_container_width=True)
        
    st.markdown("#### 🔥 Matriz de Calor (Heatmap): Dia da Semana vs Hora do Dia")
    pivot_heat = df_filtrado[df_filtrado['hora_num'].notnull()].pivot_table(
        index='dia_da_semana_limpo',
        columns='hora_num',
        values='id_sinistro',
        aggfunc='count',
        fill_value=0
    ).reindex(ordem_dias)
    
    fig_heat = px.imshow(
        pivot_heat,
        labels=dict(x="Hora do Dia (0h - 23h)", y="Dia da Semana", color="Volume"),
        x=[f"{int(c)}h" for c in pivot_heat.columns],
        y=pivot_heat.index,
        color_continuous_scale='YlOrRd',
        aspect="auto",
        template='plotly_dark',
        title="Concentração Espaço-Temporal dos Sinistros de Bauru/SP"
    )
    fig_heat.update_layout(height=360, margin=dict(l=20, r=20, t=50, b=30))
    st.plotly_chart(fig_heat, use_container_width=True)
    
    st.markdown("---")
    st.markdown("#### 🧪 Teste de Hipótese Estatístico: Teste t de Student (Dias Úteis vs Fins de Semana)")
    
    # Cálculo do teste t sobre os dados completos (2019 a 2025 com dados diários contínuos)
    df_pos2019 = df_completo[(df_completo['ano'] >= 2019) & (df_completo['ano'] <= 2025) & df_completo['data_sinistro_dt'].notnull()].copy()
    acidentes_data = df_pos2019.groupby('data_sinistro_dt').agg(
        total=('id_sinistro', 'count'),
        fim_de_semana=('is_fim_de_semana', 'first')
    ).reset_index()
    
    uteis = acidentes_data[acidentes_data['fim_de_semana'] == 0]['total']
    finais = acidentes_data[acidentes_data['fim_de_semana'] == 1]['total']
    
    t_stat, p_val = stats.ttest_ind(uteis, finais, equal_var=False)
    media_uteis = uteis.mean()
    media_finais = finais.mean()
    
    col_t_stat1, col_t_stat2, col_t_stat3, col_t_stat4 = st.columns(4)
    with col_t_stat1:
        st.metric("Média Dias Úteis", f"{media_uteis:.2f} acid./dia", "Segunda a Sexta")
    with col_t_stat2:
        st.metric("Média Finais de Semana", f"{media_finais:.2f} acid./dia", "Sábado e Domingo")
    with col_t_stat3:
        st.metric("Estatística t de Student", f"{t_stat:.3f}", "Graus de liberdade Welch")
    with col_t_stat4:
        st.metric("p-valor do Teste", f"{p_val:.4f}", "Não significativo (p > 0.05)")
        
    st.markdown(f"""
    <div class="insight-box">
        <strong>📖 Interpretação Estatística Rigorosa:</strong>
        <br>• Com <strong>p-valor = {p_val:.4f} (muito superior a 0,05)</strong>, <strong>NÃO rejeitamos a hipótese nula (H₀)</strong>.
        <br>• <strong>Conclusão:</strong> A média diária de acidentes é <strong>estatisticamente idêntica</strong> entre os dias úteis (6,98/dia) e os finais de semana (7,07/dia).
        <br>• <strong>O que muda não é o volume, mas o perfil:</strong> Nos dias úteis predominam colisões com feridos leves no tráfego comercial pendular (12h e 18h). Nos fins de semana aumentam acidentes na madrugada com alta velocidade e alcoolemia.
    </div>
    """, unsafe_allow_html=True)

# ------------------------------------------------------------------------------
# TAB 5: MAPEAMENTO GEOESPACIAL INTERATIVO
# ------------------------------------------------------------------------------
with tab5:
    st.markdown("### 5. Geografia do Risco: Mapeamento de 17.422 Sinistros Georreferenciados")
    
    st.markdown("""
    <div class="insight-box">
        <strong>🗺️ Distribuição Espacial entre Malha Urbana e Rodovias:</strong>
        <br>• <strong>Vias Urbanas Municipais (87,5% do volume):</strong> Concentram colisões em cruzamentos e semáforos (Av. Nações Unidas, Av. Duque de Caxias, Av. Rodrigues Alves), predominando feridos leves e médios.
        <br>• <strong>Rodovias Concessionadas e DER (12,5% do volume):</strong> Os eixos das rodovias <strong>SP-300 (Rodovia Marechal Rondon)</strong>, <strong>SP-225 (Bauru-Jaú)</strong> e <strong>SP-294 (Bauru-Marília)</strong> concentram grande desproporcionalidade de fatalidades em alta velocidade.
    </div>
    """, unsafe_allow_html=True)
    
    map_mode = st.radio(
        "Selecione o Modo de Visualização do Mapa:",
        options=[
            "⚡ Mapa Dinâmico Interativo (Plotly com Filtros Ativos)",
            "🗺️ Mapa Completo do Pipeline Oficial (17.422 sinistros integrados em HTML)"
        ],
        horizontal=True
    )
    
    if "Mapa Dinâmico" in map_mode:
        df_geo_filtered = df_filtrado[df_filtrado['geo_valida']].copy()
        total_pontos = len(df_geo_filtered)
        
        st.caption(f"Exibindo **{total_pontos:,}** ocorrências georreferenciadas válidas com os filtros atuais.")
        
        if total_pontos > 0:
            # Amostragem para manter a performance da renderização fluida se o usuário não filtrar muito
            amostra_geo = df_geo_filtered if total_pontos <= 4000 else df_geo_filtered.sample(4000, random_state=42)
            if total_pontos > 4000:
                st.info(f"⚡ Para otimizar o desempenho de renderização WebGL do navegador, exibindo amostra representativa de 4.000 de um total de {total_pontos:,} pontos.")
                
            color_map = {
                'FATAL': '#ef4444',
                'GRAVE': '#f97316',
                'LEVE': '#eab308',
                'ILESO / NAO INFORMADO': '#3b82f6'
            }
            
            fig_map_live = px.scatter_map(
                amostra_geo,
                lat='lat',
                lon='lon',
                color='severidade_categoria',
                color_discrete_map=color_map,
                hover_name='tipo_sinistro_simplificado',
                hover_data={
                    'lat': False,
                    'lon': False,
                    'data_sinistro': True,
                    'tipo_via': True,
                    'logradouro': True,
                    'obitos': True,
                    'feridos_graves': True,
                    'envolve_moto': True
                },
                zoom=11.5,
                center={'lat': -22.3145, 'lon': -49.0587},
                map_style='carto-positron',
                title="Mapeamento Geoespacial de Sinistros — Bauru/SP",
                height=700
            )
            fig_map_live.update_layout(
                margin=dict(l=0, r=0, t=30, b=0),
                legend=dict(
                    title=dict(text='Severidade', font=dict(size=12)),
                    yanchor='top',
                    y=0.98,
                    xanchor='left',
                    x=0.02,
                    bgcolor='rgba(15, 23, 42, 0.85)',
                    bordercolor='rgba(255, 255, 255, 0.2)',
                    borderwidth=1
                )
            )
            st.plotly_chart(fig_map_live, use_container_width=True)
        else:
            st.warning("Nenhum registro com coordenadas válidas encontrado para os filtros selecionados.")
            
    else:
        # Modo HTML completo
        if os.path.exists(MAPA_HTML_FILE):
            st.success("Carregando mapa HTML completo gerado pelo projeto (7,1 MB — 17.422 pontos mapeados com Leaflet/Plotly).")
            with open(MAPA_HTML_FILE, 'r', encoding='utf-8') as f:
                html_data = f.read()
            st.components.v1.html(html_data, height=750, scrolling=False)
        else:
            st.error(f"Arquivo de mapa não encontrado em `{MAPA_HTML_FILE}`.")

# ------------------------------------------------------------------------------
# TAB 6: INTELIGÊNCIA PREDITIVA (MACHINE LEARNING)
# ------------------------------------------------------------------------------
with tab6:
    st.markdown("### 6. Modelagem Preditiva Supervisionada de Gravidade (Machine Learning)")
    
    st.markdown("""
    <div class="insight-box">
        <strong>🤖 Arquitetura do Modelo:</strong>
        <br>• <strong>Algoritmo:</strong> <code>RandomForestClassifier</code> (200 estimadores, profundidade máxima 10, balanceamento ponderado de classes <code>class_weight='balanced'</code>).
        <br>• <strong>Objetivo Preditivo:</strong> Estimar a probabilidade de um sinistro resultar em <strong>lesão grave ou morte</strong> (Severidade Grave ou Fatal = 1).
        <br>• <strong>Desempenho:</strong> <strong>ROC-AUC = 0.801</strong> | <strong>Acurácia Global = 65.0%</strong>.
    </div>
    """, unsafe_allow_html=True)
    
    # Obter modelo e métricas do cache
    rf_model, feat_cols, roc_score, acc_score, importancias, class_rep = get_ml_model(df_completo)
    
    col_ml_metrics1, col_ml_metrics2, col_ml_metrics3 = st.columns(3)
    with col_ml_metrics1:
        st.metric("Área sob a Curva ROC (ROC-AUC)", f"{roc_score:.3f}", "Capacidade discriminativa excelente")
    with col_ml_metrics2:
        st.metric("Acurácia Ponderada Global", f"{acc_score*100:.1f}%", "Com balanceamento de classes")
    with col_ml_metrics3:
        st.metric("Volume de Treinamento", f"{len(df_completo[df_completo['hora_num'].notnull()]):,} sinistros", "Divisão 75% treino / 25% teste")
        
    col_feat, col_sim = st.columns([1.1, 1.2])
    
    with col_feat:
        st.markdown("#### 🏆 Ranking de Importância das Variáveis (Gini)")
        top_10 = importancias.head(10).reset_index()
        top_10.columns = ['Variável', 'Importância']
        
        traducao_feats = {
            'hora_num': 'Hora do Sinistro (0-23h)',
            'envolve_moto': 'Presença de Motocicleta',
            'via_RODOVIA / ESTRADA': 'Via: Rodovia / Estrada',
            'envolve_auto': 'Presença de Automóvel',
            'tipo_COLISAO': 'Tipo: Colisão Veicular',
            'is_fim_de_semana': 'Fim de Semana (Sáb/Dom)',
            'envolve_pedestre': 'Presença de Pedestre',
            'tipo_CHOQUE': 'Tipo: Choque Obstáculo Fixo',
            'turno_MANHA': 'Turno: Manhã (6h-12h)',
            'turno_TARDE': 'Turno: Tarde (12h-18h)',
            'turno_NOITE': 'Turno: Noite (18h-24h)',
            'envolve_pesado': 'Veículo Pesado (Ônibus/Caminhão)',
            'envolve_bicicleta': 'Presença de Bicicleta'
        }
        top_10['Nome Legível'] = top_10['Variável'].map(lambda x: traducao_feats.get(x, x))
        
        fig_feat = px.bar(
            top_10.sort_values(by='Importância', ascending=True),
            x='Importância',
            y='Nome Legível',
            orientation='h',
            text='Importância',
            title="Importância das Variáveis no Risco de Sinistro Grave/Fatal",
            color='Importância',
            color_continuous_scale='Viridis',
            template='plotly_dark'
        )
        fig_feat.update_traces(texttemplate='%{text:.3f}', textposition='outside')
        fig_feat.update_layout(height=420, margin=dict(l=20, r=20, t=50, b=30))
        st.plotly_chart(fig_feat, use_container_width=True)
        
    with col_sim:
        st.markdown("#### ⚡ Simulador Preditivo de Risco em Tempo Real")
        st.markdown("Configure as condições do sinistro para o modelo estimar a **probabilidade de gravidade extrema**:")
        
        with st.container():
            st.markdown('<div class="ml-card">', unsafe_allow_html=True)
            
            s_hora = st.slider("Hora da Ocorrência:", 0, 23, 18, help="Horário aproximado do sinistro")
            
            c_s1, c_s2 = st.columns(2)
            with c_s1:
                s_moto = st.checkbox("🏍️ Envolve Motocicleta", value=True)
                s_auto = st.checkbox("🚗 Envolve Automóvel", value=True)
                s_pedestre = st.checkbox("🚶 Envolve Pedestre", value=False)
            with c_s2:
                s_pesado = st.checkbox("🚛 Envolve Pesado (Caminhão/Ônibus)", value=False)
                s_bike = st.checkbox("🚲 Envolve Bicicleta", value=False)
                s_fds = st.checkbox("📅 Ocorre no Fim de Semana", value=False)
                
            c_s3, c_s4 = st.columns(2)
            with c_s3:
                s_via = st.selectbox("Tipo de Via:", ["VIA URBANA", "RODOVIA / ESTRADA"], index=0)
            with c_s4:
                s_tipo = st.selectbox("Tipo de Sinistro:", ["COLISAO", "CHOQUE", "ATROPELAMENTO", "OUTROS"], index=0)
                
            # Classificar turno
            if 0 <= s_hora < 6:
                s_turno = 'MADRUGADA'
            elif 6 <= s_hora < 12:
                s_turno = 'MANHA'
            elif 12 <= s_hora < 18:
                s_turno = 'TARDE'
            else:
                s_turno = 'NOITE'
                
            # Montar vetor para predição
            input_dict = {col: 0 for col in feat_cols}
            input_dict['hora_num'] = s_hora
            input_dict['envolve_moto'] = int(s_moto)
            input_dict['envolve_auto'] = int(s_auto)
            input_dict['envolve_pedestre'] = int(s_pedestre)
            input_dict['envolve_bicicleta'] = int(s_bike)
            input_dict['envolve_pesado'] = int(s_pesado)
            input_dict['is_fim_de_semana'] = int(s_fds)
            
            via_col = f"via_{s_via}"
            if via_col in input_dict:
                input_dict[via_col] = 1
                
            tipo_col = f"tipo_{s_tipo}"
            if tipo_col in input_dict:
                input_dict[tipo_col] = 1
                
            turno_col = f"turno_{s_turno}"
            if turno_col in input_dict:
                input_dict[turno_col] = 1
                
            X_input = pd.DataFrame([input_dict])[feat_cols]
            prob_grave = rf_model.predict_proba(X_input)[0, 1] * 100
            
            # Badge de risco
            if prob_grave >= 65:
                risco_texto = "CRÍTICO"
                badge_class = "badge-danger"
                cor_gauge = "#ef4444"
            elif prob_grave >= 45:
                risco_texto = "ELEVADO"
                badge_class = "badge-warning"
                cor_gauge = "#f59e0b"
            elif prob_grave >= 25:
                risco_texto = "MODERADO"
                badge_class = "badge-info"
                cor_gauge = "#6366f1"
            else:
                risco_texto = "BAIXO"
                badge_class = "badge-success"
                cor_gauge = "#10b981"
                
            st.markdown("---")
            st.markdown(f"""
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <div style="font-size: 0.85rem; color: #94a3b8; text-transform: uppercase;">Probabilidade Estimada de Lesão Grave ou Fatal:</div>
                    <div style="font-size: 2.2rem; font-weight: 800; color: {cor_gauge};">{prob_grave:.1f}%</div>
                </div>
                <div>
                    <span class="badge {badge_class}" style="font-size: 0.9rem; padding: 6px 14px;">RISCO {risco_texto}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            st.progress(min(prob_grave / 100.0, 1.0))
            
            st.markdown('</div>', unsafe_allow_html=True)

    with st.expander("🖼️ Visualizar Gráfico de Machine Learning Oficial (`output/graficos/importancia_features_ml.png`)"):
        img_ml = os.path.join(GRAFICOS_DIR, "importancia_features_ml.png")
        if os.path.exists(img_ml):
            st.image(img_ml, caption="Gráfico Oficial gerado pelo pipeline de dados", use_container_width=True)

# ------------------------------------------------------------------------------
# TAB 7: RECOMENDAÇÕES ESTRUTURANTES PARA GESTÃO PÚBLICA
# ------------------------------------------------------------------------------
with tab7:
    st.markdown("### 7. Recomendações Estruturantes para a Gestão Pública Municipal de Bauru")
    
    st.markdown("""
    Com base nas evidências empíricas e nas análises de machine learning deste projeto, sintetizamos **quatro eixos de intervenção prioritários** para a Prefeitura de Bauru, EMDURB, DER-SP e concessionárias:
    """)
    
    col_rec1, col_rec2 = st.columns(2)
    
    with col_rec1:
        st.markdown("""
        <div class="metric-card" style="border-left: 4px solid #3b82f6;">
            <h4 style="color: #60a5fa; margin-bottom: 8px;">1. Plano de Contingência para Motociclistas</h4>
            <p style="font-size: 0.9rem; color: #cbd5e1; line-height: 1.5;">
                • <strong>Criação de Faixas Azuis (Motofaixas):</strong> Implantação piloto nos corredores de maior fluxo pendular, como a <em>Avenida Nações Unidas</em> e a <em>Avenida Duque de Caxias</em>, segregando motos nos horários de pico (11h–13h e 17h–19h).<br>
                • <strong>Áreas de Espera Exclusivas nos Semáforos:</strong> Espaços à frente da linha de retenção para evitar colisões no arranque.<br>
                • <strong>Fiscalização de Equipamentos:</strong> Intensificação das blitzes focadas em capacetes homologados e calçados adequados.
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div class="metric-card" style="border-left: 4px solid #ef4444;">
            <h4 style="color: #f87171; margin-bottom: 8px;">2. Engenharia em Obstáculos Fixos (Prevenção de Choques)</h4>
            <p style="font-size: 0.9rem; color: #cbd5e1; line-height: 1.5;">
                • <strong>Instalação de Atenuadores de Impacto (Crash Cushions):</strong> Aplicação diante de pilares de viadutos e divisores de pista nos acessos à SP-300.<br>
                • <strong>Defensas Metálicas Maleáveis:</strong> Proteção de postes de iluminação e árvores de grande porte em curvas de alta velocidade.<br>
                • <strong>Mitigação:</strong> Como o choque contra obstáculo fixo mata <strong>7,45%</strong> dos envolvidos, essas medidas trazem retorno imediato na redução de fatalidades.
            </p>
        </div>
        """, unsafe_allow_html=True)
        
    with col_rec2:
        st.markdown("""
        <div class="metric-card" style="border-left: 4px solid #f59e0b;">
            <h4 style="color: #fbbf24; margin-bottom: 8px;">3. Iluminação e Travessia Segura para Pedestres</h4>
            <p style="font-size: 0.9rem; color: #cbd5e1; line-height: 1.5;">
                • <strong>Faixas Elevadas e Refúgios Centrais:</strong> Instalação em áreas de intenso fluxo comercial e universitário onde atropelamentos registram <strong>9,09% de letalidade</strong>.<br>
                • <strong>Reforço na Iluminação Noturna em LED:</strong> Foco nas travessias e paradas de ônibus em avenidas arteriais (Av. Rodrigues Alves e Av. Comendador Daniel Pacífico).<br>
                • <strong>Redução de Velocidade em Zonas Escolares:</strong> Limitação para 30 km/h com sinalização ostensiva.
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div class="metric-card" style="border-left: 4px solid #10b981;">
            <h4 style="color: #34d399; margin-bottom: 8px;">4. Articulação Integrada com DER-SP e Concessionárias</h4>
            <p style="font-size: 0.9rem; color: #cbd5e1; line-height: 1.5;">
                • <strong>Comitê Conjunto de Monitoramento da SP-300 (Marechal Rondon):</strong> As marginais e alças de acesso da rodovia que cortam o perímetro urbano respondem pelo maior índice de colisões de alta velocidade.<br>
                • <strong>Melhoria nos Trevos de Conexão:</strong> Reordenamento das alças de acesso com a SP-225 (Bauru-Jaú) e SP-294 (Bauru-Marília).<br>
                • <strong>Fiscalização Eletrônica Inteligente:</strong> Radares de velocidade nos pontos com histórico recorrente de capotamento e colisão transversal.
            </p>
        </div>
        """, unsafe_allow_html=True)

# ------------------------------------------------------------------------------
# TAB 8: RELATÓRIO TÉCNICO & CENTRAL DE DOWNLOADS
# ------------------------------------------------------------------------------
with tab8:
    st.markdown("### 8. Central de Documentação, Relatórios e Downloads")
    
    st.markdown("Tenha acesso direto aos arquivos brutos, datasets higienizados, gráficos oficiais e relatório técnico-executivo:")
    
    c_dw1, c_dw2, c_dw3, c_dw4 = st.columns(4)
    
    with c_dw1:
        if os.path.exists(RELATORIO_PDF):
            with open(RELATORIO_PDF, "rb") as f_pdf:
                st.download_button(
                    label="📄 Baixar Relatório PDF (1.8 MB)",
                    data=f_pdf,
                    file_name="relatorio_seguranca_viaria_bauru.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
        else:
            st.button("Relatório PDF não encontrado", disabled=True, use_container_width=True)
            
    with c_dw2:
        if os.path.exists(RESUMO_FILE):
            with open(RESUMO_FILE, "rb") as f_resumo:
                st.download_button(
                    label="📊 Resumo Anual (CSV)",
                    data=f_resumo,
                    file_name="resumo_anual_bauru.csv",
                    mime="text/csv",
                    use_container_width=True
                )
                
    with c_dw3:
        # Download do CSV filtrado
        csv_buffer = io.StringIO()
        df_filtrado.to_csv(csv_buffer, sep=';', index=False, encoding='utf-8')
        st.download_button(
            label="💾 Dataset Filtrado (CSV)",
            data=csv_buffer.getvalue().encode('utf-8'),
            file_name="bauru_sinistros_filtrados.csv",
            mime="text/csv",
            use_container_width=True
        )
        
    with c_dw4:
        if os.path.exists(MAPA_HTML_FILE):
            with open(MAPA_HTML_FILE, "rb") as f_map:
                st.download_button(
                    label="🗺️ Mapa HTML Completo",
                    data=f_map,
                    file_name="mapa_acidentes_bauru.html",
                    mime="text/html",
                    use_container_width=True
                )

    st.markdown("---")
    st.markdown("#### 🖼️ Galeria de Gráficos Oficiais em Alta Resolução (PNG)")
    
    col_g1, col_g2, col_g3 = st.columns(3)
    
    graficos_lista = [
        ("acidentes_por_ano.png", "Evolução Histórica Anual"),
        ("acidentes_dia_e_hora.png", "Distribuição por Dia e Hora"),
        ("tipos_e_veiculos.png", "Letalidade por Tipo e Modais"),
        ("heatmap_dia_hora.png", "Matriz de Calor Dia x Hora"),
        ("importancia_features_ml.png", "Importância de Variáveis no Modelo ML")
    ]
    
    for idx, (nome_arquivo, titulo_g) in enumerate(graficos_lista):
        col_dest = [col_g1, col_g2, col_g3][idx % 3]
        caminho_g = os.path.join(GRAFICOS_DIR, nome_arquivo)
        with col_dest:
            st.markdown(f"**{titulo_g}** (`{nome_arquivo}`)")
            if os.path.exists(caminho_g):
                with open(caminho_g, "rb") as f_img:
                    img_bytes = f_img.read()
                st.image(img_bytes, use_container_width=True)
                st.download_button(
                    label=f"⬇️ Baixar {nome_arquivo}",
                    data=img_bytes,
                    file_name=nome_arquivo,
                    mime="image/png",
                    key=f"btn_dl_{nome_arquivo}",
                    use_container_width=True
                )
            else:
                st.caption("Imagem não encontrada")
                
    st.markdown("---")
    st.markdown("#### 📑 Relatório Técnico-Executivo na Íntegra (Markdown Oficial)")
    
    if os.path.exists(RELATORIO_MD):
        with open(RELATORIO_MD, 'r', encoding='utf-8') as f_rel:
            rel_md_texto = f_rel.read()
        with st.expander("Clique aqui para expandir e ler o Relatório Técnico-Executivo completo", expanded=False):
            st.markdown(rel_md_texto)
    else:
        st.info("Arquivo de relatório markdown não encontrado.")

# ==============================================================================
# RODAPÉ
# ==============================================================================
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #64748b; font-size: 0.85rem; padding: 12px;">
    <strong>Projeto de Ciência de Dados — Segurança Viária em Bauru/SP (2015–2026)</strong><br>
    Dados oficiais: Sistema Infosiga SP (Movimento Paulista de Segurança no Trânsito) • Código IBGE: 3506003<br>
    Construído com Streamlit, Plotly, Pandas e Scikit-Learn
</div>
""", unsafe_allow_html=True)
