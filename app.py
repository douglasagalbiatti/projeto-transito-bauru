"""
Dashboard Interativo de Segurança Viária — Bauru/SP (2015–2026)
Desenvolvido com Streamlit, Plotly e Scikit-Learn
Dados: Infosiga SP (Movimento Paulista de Segurança no Trânsito)
"""

import os
import io
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

from src.metricas import (
    CORES_SEVERIDADE,
    ORDEM_SEVERIDADE,
    SEM_INFORMACAO,
    base_comparavel,
    br,
    com_modal_informado,
    comparar_dias,
    formatar_tabela,
    normalizar_via,
    ranking_vias,
    razao_letalidade,
    tabela_letalidade,
)
from src.modelo import treinar_modelo

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
ERRATA_MD = os.path.join(BASE_DIR, "output", "relatorios", "ERRATA.md")
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

@st.cache_resource(show_spinner="Treinando o modelo exploratório...")
def get_ml_model():
    return treinar_modelo(load_data())

def mostrar_grafico(fig):
    """Exibe um gráfico Plotly com vírgula decimal e ponto de milhar."""
    fig.update_layout(separators=",.")
    fig.update_xaxes(separatethousands=True)
    fig.update_yaxes(separatethousands=True)
    st.plotly_chart(fig, width="stretch")

df_completo = load_data()
df_resumo = load_resumo()

if df_completo.empty:
    st.error("Erro crítico: Nenhum dado disponível para análise. Verifique `data/bauru_limpo.csv`.")
    st.stop()

inicio_dados = df_completo['data_sinistro_dt'].min()
fim_dados = df_completo['data_sinistro_dt'].max()
periodo_dados = f"{inicio_dados:%m/%Y} a {fim_dados:%m/%Y}"
base_tipos = base_comparavel(df_completo)

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
severidades_selecionadas = st.sidebar.multiselect(
    "Severidade do Sinistro:",
    options=ORDEM_SEVERIDADE,
    default=ORDEM_SEVERIDADE
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
    "Com Motocicleta (🏍️)",
    "Com Automóvel (🚗)",
    "Com Pedestre (🚶)",
    "Com Bicicleta (🚲)",
    "Com Pesados / Ônibus / Caminhão (🚛)"
]
modal_selecionado = st.sidebar.selectbox("Modal Específico:", options=modal_opcoes, index=0)

# Filtro de Período da Semana
dia_semana_opcoes = ["Todos os Dias", "Apenas Dias Úteis (Seg-Sex)", "Apenas Fim de Semana (Sáb-Dom)"]
periodo_selecionado = st.sidebar.selectbox("Período da Semana:", options=dia_semana_opcoes, index=0)

# APLICAÇÃO DOS FILTROS
df_filtrado = df_completo[
    df_completo['ano'].isin(anos_selecionados)
    & df_completo['severidade_categoria'].isin(severidades_selecionadas)
]

if via_selecionada != "Todas":
    df_filtrado = df_filtrado[df_filtrado['tipo_via_simplificado'] == via_selecionada]

if sinistro_selecionado != "Todos":
    df_filtrado = df_filtrado[df_filtrado['tipo_sinistro_simplificado'] == sinistro_selecionado]

if modal_selecionado == "Com Motocicleta (🏍️)":
    df_filtrado = df_filtrado[df_filtrado['envolve_moto'] == 1]
elif modal_selecionado == "Com Automóvel (🚗)":
    df_filtrado = df_filtrado[df_filtrado['envolve_auto'] == 1]
elif modal_selecionado == "Com Pedestre (🚶)":
    df_filtrado = df_filtrado[df_filtrado['envolve_pedestre'] == 1]
elif modal_selecionado == "Com Bicicleta (🚲)":
    df_filtrado = df_filtrado[df_filtrado['envolve_bicicleta'] == 1]
elif modal_selecionado == "Com Pesados / Ônibus / Caminhão (🚛)":
    df_filtrado = df_filtrado[df_filtrado['envolve_pesado'] == 1]

if periodo_selecionado == "Apenas Dias Úteis (Seg-Sex)":
    df_filtrado = df_filtrado[df_filtrado['is_fim_de_semana'] == 0]
elif periodo_selecionado == "Apenas Fim de Semana (Sáb-Dom)":
    df_filtrado = df_filtrado[df_filtrado['is_fim_de_semana'] == 1]

if df_filtrado.empty:
    st.warning("Nenhum registro atende aos filtros selecionados.")
    st.stop()

df_comparavel = base_comparavel(df_filtrado)

# Métricas da Barra Lateral
st.sidebar.divider()
total_completo = len(df_completo)
total_atual = len(df_filtrado)
pct_selecionada = total_atual / total_completo * 100

st.sidebar.markdown("**Amostra Selecionada:**")
st.sidebar.markdown(f"- **{br(total_atual)}** de **{br(total_completo)}** registros (`{br(pct_selecionada, 1)}%`)")
st.sidebar.markdown(f"- **{br(df_filtrado['obitos'].sum())}** óbitos")
st.sidebar.markdown(f"- **{br(df_filtrado['feridos_graves'].sum())}** feridos graves")
st.sidebar.caption(f"Dados do Infosiga SP de {periodo_dados}.")

# ==============================================================================
# CABEÇALHO PRINCIPAL DA PÁGINA
# ==============================================================================
st.markdown(f"""
<div class="header-container">
    <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 12px;">
        <div>
            <div style="display: flex; gap: 8px; margin-bottom: 8px; flex-wrap: wrap;">
                <span class="badge badge-info">BAURU / SP (IBGE 3506003)</span>
                <span class="badge badge-success">INFOSIGA SP</span>
                <span class="badge badge-warning">{periodo_dados}</span>
                <span class="badge badge-danger">{br(total_completo)} REGISTROS</span>
            </div>
            <div class="header-title">🚦 Painel de Segurança Viária de Bauru</div>
            <div class="header-subtitle">
                Padrões dos registros de trânsito em vias urbanas e rodovias de Bauru/SP, com as limitações de cada indicador.
            </div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# ==============================================================================
# CARDS DE MÉTRICAS EXECUTIVAS (KPIS)
# ==============================================================================
total_registros = len(df_filtrado)
total_obitos = int(df_filtrado['obitos'].sum())
total_graves = int(df_filtrado['feridos_graves'].sum())
sem_info = int((df_filtrado['severidade_categoria'] == SEM_INFORMACAO).sum())
taxa_letalidade = (df_comparavel['obitos'] > 0).mean() * 100 if len(df_comparavel) > 0 else 0
df_com_modal = com_modal_informado(df_filtrado)
total_motos = int(df_com_modal['envolve_moto'].sum())
pct_motos = total_motos / len(df_com_modal) * 100 if len(df_com_modal) > 0 else 0

kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)

with kpi1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">🚨 Total de Registros</div>
        <div class="metric-value">{br(total_registros)}</div>
        <div class="metric-sub"><span class="badge badge-info">{br(sem_info)}</span> sem dados de vítimas</div>
    </div>
    """, unsafe_allow_html=True)

with kpi2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">✝️ Vítimas Fatais</div>
        <div class="metric-value" style="color: #f87171;">{br(total_obitos)}</div>
        <div class="metric-sub"><span class="badge badge-danger">Óbitos</span> registrados</div>
    </div>
    """, unsafe_allow_html=True)

with kpi3:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">🏥 Feridos Graves</div>
        <div class="metric-value" style="color: #fbbf24;">{br(total_graves)}</div>
        <div class="metric-sub"><span class="badge badge-warning">Pessoas</span> registradas</div>
    </div>
    """, unsafe_allow_html=True)

with kpi4:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">⚡ Letalidade</div>
        <div class="metric-value">{br(taxa_letalidade, 2)}%</div>
        <div class="metric-sub">Sinistros com óbito, base comparável</div>
    </div>
    """, unsafe_allow_html=True)

with kpi5:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">🏍️ Envolve Moto</div>
        <div class="metric-value" style="color: #818cf8;">{br(total_motos)}</div>
        <div class="metric-sub"><span class="badge badge-info">{br(pct_motos, 1)}%</span> com modal informado</div>
    </div>
    """, unsafe_allow_html=True)

st.write("")

# ==============================================================================
# ABAS DE NAVEGAÇÃO E ANÁLISE PROFUNDA
# ==============================================================================
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
    "📊 Evolução Anual & Histórico",
    "💥 Tipos de Sinistro & Letalidade",
    "🏍️ Modais",
    "⏰ Padrões Temporais & Teste de Welch",
    "🗺️ Mapa Geoespacial Interativo",
    "🤖 Modelo Exploratório (ML)",
    "🏛️ Recomendações",
    "📑 Relatório & Downloads"
])

# ------------------------------------------------------------------------------
# TAB 1: EVOLUÇÃO ANUAL & HISTÓRICO
# ------------------------------------------------------------------------------
with tab1:
    st.markdown("### 1. Evolução Histórica de Registros e Óbitos")

    pct_notificacoes = df_completo[df_completo['ano'] >= 2019].groupby('ano')['tipo_registro'].apply(
        lambda s: (s == 'NOTIFICACAO').mean() * 100
    )
    st.markdown(f"""
    <div class="insight-box">
        <strong>📌 Ressalva metodológica:</strong>
        <br>• <strong>2015 a 2018:</strong> o sistema registra apenas sinistros fatais.
        <br>• <strong>2019 em diante:</strong> entram sinistros não fatais e notificações. As notificações nunca trazem veículos e vão de {br(pct_notificacoes.min(), 1)}% a {br(pct_notificacoes.max(), 1)}% dos registros por ano, então o total anual não mede tendência.
        <br>• <strong>Base comparável:</strong> letalidade, perfis de gravidade e modelo usam sinistros de 2019 em diante, sem notificações.
    </div>
    """, unsafe_allow_html=True)

    col_chart, col_side = st.columns([2.2, 1])

    with col_chart:
        resumo_filtrado = df_filtrado.groupby('ano').agg(
            sinistros=('tipo_registro', lambda s: int((s != 'NOTIFICACAO').sum())),
            notificacoes=('tipo_registro', lambda s: int((s == 'NOTIFICACAO').sum())),
            obitos=('obitos', 'sum')
        ).reset_index()

        fig_anual = go.Figure()

        fig_anual.add_trace(go.Bar(
            x=resumo_filtrado['ano'],
            y=resumo_filtrado['sinistros'],
            name='Sinistros (fatais e não fatais)',
            marker_color='#3b82f6',
            yaxis='y'
        ))

        fig_anual.add_trace(go.Bar(
            x=resumo_filtrado['ano'],
            y=resumo_filtrado['notificacoes'],
            name='Notificações',
            marker_color='#94a3b8',
            yaxis='y'
        ))

        fig_anual.add_trace(go.Scatter(
            x=resumo_filtrado['ano'],
            y=resumo_filtrado['obitos'],
            name='Óbitos',
            line=dict(color='#ef4444', width=3),
            marker=dict(size=8, color='#ef4444'),
            mode='lines+markers+text',
            text=resumo_filtrado['obitos'],
            textposition='top center',
            yaxis='y2'
        ))

        fig_anual.update_layout(
            barmode='stack',
            title="Registros e Óbitos em Bauru/SP",
            xaxis=dict(title="Ano", tickmode='linear', dtick=1, tickformat='d'),
            yaxis=dict(title="Registros", showgrid=True, gridcolor='rgba(255,255,255,0.1)'),
            yaxis2=dict(title="Óbitos", overlaying='y', side='right', showgrid=False, range=[0, max(resumo_filtrado['obitos'].max(), 1) * 1.3]),
            legend=dict(x=0.02, y=0.98, bgcolor='rgba(15, 23, 42, 0.7)'),
            template='plotly_dark',
            margin=dict(l=20, r=20, t=50, b=30),
            height=430
        )
        mostrar_grafico(fig_anual)
        st.caption(f"O último ano é parcial: os dados vão até {fim_dados:%d/%m/%Y}.")

    with col_side:
        st.markdown("#### 📋 Resumo por Ano (base completa, sem filtros)")
        if not df_resumo.empty:
            df_display_resumo = df_resumo.rename(columns={
                'ano': 'Ano',
                'total_registros': 'Registros',
                'notificacoes': 'Notificações',
                'sinistros_fatais': 'Sinistros com Óbito',
                'obitos': 'Óbitos',
                'feridos_graves': 'Feridos Graves',
                'feridos_leves': 'Feridos Leves'
            })
            st.dataframe(formatar_tabela(df_display_resumo, sem_milhar=['Ano']), height=380, width="stretch", hide_index=True)

    with st.expander("🖼️ Visualizar Imagem Gerada pelo Pipeline (`output/graficos/acidentes_por_ano.png`)"):
        img_ano = os.path.join(GRAFICOS_DIR, "acidentes_por_ano.png")
        if os.path.exists(img_ano):
            st.image(img_ano, caption="Registros, notificações e óbitos por ano", width="stretch")
        else:
            st.info("Arquivo de imagem estática não encontrado no caminho especificado.")

# ------------------------------------------------------------------------------
# TAB 2: TIPOS DE SINISTRO & LETALIDADE
# ------------------------------------------------------------------------------
with tab2:
    st.markdown("### 2. Tipos de Sinistro e Letalidade")

    razao_choque, ic_choque_inf, ic_choque_sup = razao_letalidade(base_tipos, 'CHOQUE', 'COLISAO')
    letal_geral = tabela_letalidade(base_tipos).set_index('tipo_sinistro_simplificado')['letalidade_pct']
    urbano_tipos = base_tipos[base_tipos['tipo_via'] == 'VIAS URBANAS']
    rodovia_tipos = base_tipos[base_tipos['tipo_via'] == 'ESTRADAS E RODOVIAS']
    razao_urbana = razao_letalidade(urbano_tipos, 'CHOQUE', 'COLISAO')
    razao_rodovia = razao_letalidade(rodovia_tipos, 'CHOQUE', 'COLISAO')

    st.markdown(f"""
    <div class="insight-box-danger">
        <strong>⚠️ Base comparável, sem os filtros:</strong>
        <br>Atropelamentos têm {br(letal_geral['ATROPELAMENTO'], 2)}% de letalidade, choques {br(letal_geral['CHOQUE'], 2)}% e colisões {br(letal_geral['COLISAO'], 2)}%.
        <br>O choque tem {br(razao_choque, 1)} vezes a letalidade da colisão (IC95% {br(ic_choque_inf, 1)} a {br(ic_choque_sup, 1)}), mas a diferença é urbana: {br(razao_urbana[0], 1)} vezes nas vias urbanas e {br(razao_rodovia[0], 1)} nas rodovias (IC95% {br(razao_rodovia[1], 1)} a {br(razao_rodovia[2], 1)}).
        <br>Letalidade = sinistros com óbito ÷ sinistros do tipo. A base não informa velocidade nem qual objeto foi atingido.
    </div>
    """, unsafe_allow_html=True)

    comparacao_via = base_tipos[base_tipos['tipo_sinistro_simplificado'].isin(['ATROPELAMENTO', 'CHOQUE', 'COLISAO']) & (base_tipos['tipo_via'] != 'NAO DISPONIVEL')]
    st.dataframe(formatar_tabela(tabela_letalidade(comparacao_via, por=['tipo_via', 'tipo_sinistro_simplificado'])), width="stretch", hide_index=True)

    if df_comparavel.empty:
        st.info("Os filtros atuais não têm sinistros na base comparável.")
    else:
        tabela_tipo = tabela_letalidade(df_comparavel)

        col_t1, col_t2 = st.columns([1.2, 1])

        with col_t1:
            fig_bar_letal = px.bar(
                tabela_tipo,
                x='tipo_sinistro_simplificado',
                y='letalidade_pct',
                color='letalidade_pct',
                color_continuous_scale='Reds',
                text=tabela_tipo['letalidade_pct'].apply(lambda v: f"{br(v, 2)}%"),
                title="Letalidade (%) por Tipo de Sinistro (base comparável)",
                labels={'tipo_sinistro_simplificado': 'Tipo de Sinistro', 'letalidade_pct': 'Letalidade (% dos sinistros)'},
                template='plotly_dark'
            )
            fig_bar_letal.update_traces(textposition='outside')
            fig_bar_letal.update_layout(height=380, margin=dict(l=20, r=20, t=50, b=30), coloraxis_showscale=False)
            mostrar_grafico(fig_bar_letal)

        with col_t2:
            volume_tipo = tabela_tipo.sort_values(by='sinistros', ascending=True)
            fig_bar_vol = px.bar(
                volume_tipo,
                x='sinistros',
                y='tipo_sinistro_simplificado',
                orientation='h',
                text=volume_tipo['sinistros'].apply(br),
                title="Sinistros por Tipo (base comparável)",
                labels={'tipo_sinistro_simplificado': 'Tipo de Sinistro', 'sinistros': 'Sinistros'},
                color_discrete_sequence=['#6366f1'],
                template='plotly_dark'
            )
            fig_bar_vol.update_traces(textposition='outside')
            fig_bar_vol.update_layout(height=380, margin=dict(l=20, r=20, t=50, b=30))
            mostrar_grafico(fig_bar_vol)

        st.markdown("#### 📊 Tabela de Severidade por Tipo")
        st.dataframe(
            formatar_tabela(tabela_tipo.rename(columns={
                'tipo_sinistro_simplificado': 'Tipo de Sinistro',
                'sinistros': 'Sinistros',
                'sinistros_fatais': 'Sinistros com Óbito',
                'obitos': 'Óbitos (pessoas)',
                'feridos_graves': 'Feridos Graves (pessoas)',
                'letalidade_pct': 'Letalidade (%)'
            })),
            width="stretch",
            hide_index=True
        )

    with st.expander("🖼️ Visualizar Imagem (`output/graficos/tipos_e_veiculos.png`)"):
        img_tipo = os.path.join(GRAFICOS_DIR, "tipos_e_veiculos.png")
        if os.path.exists(img_tipo):
            st.image(img_tipo, caption="Letalidade por tipo e presença de modais", width="stretch")

# ------------------------------------------------------------------------------
# TAB 3: MODAIS
# ------------------------------------------------------------------------------
with tab3:
    st.markdown("### 3. Modais de Transporte")

    st.markdown("""
    <div class="insight-box">
        <strong>🏍️ Como ler estes dados:</strong>
        <br>• As proporções consideram apenas registros com veículo ou pedestre informado, pois as notificações vêm sem esses dados.
        <br>• A base não liga cada vítima ao seu veículo. Ela mostra a gravidade do sinistro com moto, não o risco individual do motociclista.
        <br>• Não há dado de frota nem de quilômetros rodados, então a presença de um modal não mede o risco dele.
    </div>
    """, unsafe_allow_html=True)

    col_m1, col_m2 = st.columns(2)

    with col_m1:
        total_modal = len(df_com_modal)
        modais_df = pd.DataFrame({
            'Modal': ['Automóvel', 'Motocicleta', 'Pedestre', 'Pesado (Caminhão/Ônibus)', 'Bicicleta'],
            'Volume': [
                int(df_com_modal['envolve_auto'].sum()),
                int(df_com_modal['envolve_moto'].sum()),
                int(df_com_modal['envolve_pedestre'].sum()),
                int(df_com_modal['envolve_pesado'].sum()),
                int(df_com_modal['envolve_bicicleta'].sum())
            ]
        })
        modais_df['Participacao_Pct'] = modais_df['Volume'] / total_modal * 100 if total_modal > 0 else 0

        fig_modal = px.bar(
            modais_df,
            x='Modal',
            y='Volume',
            color='Modal',
            color_discrete_sequence=['#3b82f6', '#ec4899', '#f97316', '#8b5cf6', '#10b981'],
            text=modais_df.apply(lambda r: f"{br(r['Volume'])} ({br(r['Participacao_Pct'], 1)}%)", axis=1),
            title="Presença dos Modais nos Registros",
            template='plotly_dark'
        )
        fig_modal.update_traces(textposition='outside')
        fig_modal.update_layout(height=380, showlegend=False, margin=dict(l=20, r=20, t=50, b=30))
        mostrar_grafico(fig_modal)

    with col_m2:
        # Perfil de severidade COM moto vs SEM moto, na base comparável
        df_comp_moto = df_comparavel.copy()
        df_comp_moto['Grupo'] = df_comp_moto['envolve_moto'].map({1: 'Com Motocicleta', 0: 'Sem Motocicleta'})
        perfil_moto = pd.crosstab(df_comp_moto['Grupo'], df_comp_moto['severidade_categoria'], normalize='index') * 100
        perfil_moto = perfil_moto.reindex(columns=ORDEM_SEVERIDADE, fill_value=0).reset_index().melt(
            id_vars='Grupo', var_name='Severidade', value_name='Percentual'
        )

        fig_perfil_moto = px.bar(
            perfil_moto,
            x='Grupo',
            y='Percentual',
            color='Severidade',
            color_discrete_map=CORES_SEVERIDADE,
            barmode='stack',
            text=perfil_moto['Percentual'].apply(lambda v: f"{br(v, 1)}%" if v > 4 else ""),
            title="Perfil de Severidade: Com Moto vs Sem Moto (base comparável)",
            template='plotly_dark'
        )
        fig_perfil_moto.update_layout(height=380, margin=dict(l=20, r=20, t=50, b=30), yaxis=dict(title="% do grupo"), xaxis=dict(title=""))
        mostrar_grafico(fig_perfil_moto)

    st.markdown("#### 🔍 Grave ou Fatal: Com Moto vs Sem Moto (base comparável)")
    col_c1, col_c2, col_c3 = st.columns(3)

    moto_comp = df_comparavel[df_comparavel['envolve_moto'] == 1]
    sem_moto_comp = df_comparavel[df_comparavel['envolve_moto'] == 0]
    taxa_grave_moto = moto_comp['severidade_grave_ou_fatal'].mean() * 100 if len(moto_comp) > 0 else 0
    taxa_grave_sem_moto = sem_moto_comp['severidade_grave_ou_fatal'].mean() * 100 if len(sem_moto_comp) > 0 else 0
    letal_moto = (moto_comp['obitos'] > 0).mean() * 100 if len(moto_comp) > 0 else 0
    letal_sem_moto = (sem_moto_comp['obitos'] > 0).mean() * 100 if len(sem_moto_comp) > 0 else 0

    with col_c1:
        st.metric("Sinistros com Motocicleta", br(len(moto_comp)), f"{br(len(moto_comp) / len(df_comparavel) * 100 if len(df_comparavel) > 0 else 0, 1)}% da base comparável", delta_color="off")
    with col_c2:
        st.metric("Grave ou Fatal COM Moto", f"{br(taxa_grave_moto, 1)}%", f"Letalidade: {br(letal_moto, 1)}%", delta_color="off")
    with col_c3:
        st.metric("Grave ou Fatal SEM Moto", f"{br(taxa_grave_sem_moto, 1)}%", f"Letalidade: {br(letal_sem_moto, 1)}%", delta_color="off")

# ------------------------------------------------------------------------------
# TAB 4: PADRÕES TEMPORAIS & TESTE ESTATÍSTICO
# ------------------------------------------------------------------------------
with tab4:
    st.markdown("### 4. Análise Temporal, Matriz de Calor e Teste de Welch")

    ordem_dias = ['Segunda-feira', 'Terça-feira', 'Quarta-feira', 'Quinta-feira', 'Sexta-feira', 'Sábado', 'Domingo']

    col_dia, col_hora = st.columns(2)

    with col_dia:
        dias_counts = df_filtrado['dia_da_semana_limpo'].value_counts().reindex(ordem_dias, fill_value=0).reset_index()
        dias_counts.columns = ['Dia da Semana', 'Volume']

        fig_dia = px.bar(
            dias_counts,
            x='Dia da Semana',
            y='Volume',
            color='Volume',
            color_continuous_scale='Blues',
            text=dias_counts['Volume'].apply(br),
            title="Registros por Dia da Semana em Bauru",
            template='plotly_dark'
        )
        fig_dia.update_traces(textposition='outside')
        fig_dia.update_layout(height=340, margin=dict(l=20, r=20, t=50, b=30), coloraxis_showscale=False)
        mostrar_grafico(fig_dia)

    with col_hora:
        horas_counts = df_filtrado['hora_num'].value_counts().reindex(range(24), fill_value=0).reset_index()
        horas_counts.columns = ['Hora', 'Volume']

        fig_hora = px.bar(
            horas_counts,
            x='Hora',
            y='Volume',
            text=horas_counts['Volume'].apply(br),
            title="Distribuição por Hora do Dia (0h às 23h)",
            color_discrete_sequence=['#60a5fa'],
            template='plotly_dark'
        )
        fig_hora.update_traces(textposition='outside')
        fig_hora.update_layout(
            xaxis=dict(tickmode='linear', tick0=0, dtick=2),
            height=340,
            margin=dict(l=20, r=20, t=50, b=30)
        )
        mostrar_grafico(fig_hora)
        top_horas = horas_counts.nlargest(3, 'Volume')['Hora'].tolist()
        st.caption(f"Maiores volumes: {', '.join(f'{h}h' for h in top_horas)}. Volume não equivale a risco: a base não traz o fluxo de veículos por horário.")

    st.markdown("#### 🔥 Matriz de Calor (Heatmap): Dia da Semana vs Hora do Dia")
    pivot_heat = df_filtrado[df_filtrado['hora_num'].notnull()].pivot_table(
        index='dia_da_semana_limpo',
        columns='hora_num',
        values='id_sinistro',
        aggfunc='count',
        fill_value=0
    ).reindex(index=ordem_dias, columns=range(24), fill_value=0)

    fig_heat = px.imshow(
        pivot_heat,
        labels=dict(x="Hora do Dia (0h - 23h)", y="Dia da Semana", color="Registros"),
        x=[f"{c}h" for c in pivot_heat.columns],
        y=pivot_heat.index,
        color_continuous_scale='YlOrRd',
        aspect="auto",
        template='plotly_dark',
        title="Registros por Dia da Semana e Hora em Bauru/SP"
    )
    fig_heat.update_layout(height=360, margin=dict(l=20, r=20, t=50, b=30))
    mostrar_grafico(fig_heat)

    st.markdown("---")
    st.markdown("#### 🧪 Comparação entre Dias Úteis e Fins de Semana (teste de Welch)")
    st.markdown("Registros de 2019 em diante, sem os filtros da barra lateral. Cada dia do calendário conta, inclusive os dias sem nenhum registro.")

    teste = comparar_dias(df_completo[df_completo['ano'] >= 2019])
    media_por_dia = teste['media_por_dia']

    col_t_stat1, col_t_stat2, col_t_stat3, col_t_stat4 = st.columns(4)
    with col_t_stat1:
        st.metric("Média Dias Úteis", f"{br(teste['media_uteis'], 2)} registros/dia")
    with col_t_stat2:
        st.metric("Média Fins de Semana", f"{br(teste['media_fds'], 2)} registros/dia")
    with col_t_stat3:
        st.metric("Diferença (IC95%)", br(teste['diferenca'], 2), f"{br(teste['ic95'][0], 2)} a {br(teste['ic95'][1], 2)}", delta_color="off")
    with col_t_stat4:
        st.metric("p-valor", br(teste['p_welch'], 3))

    conclusao_dias = "O intervalo exclui zero." if teste['p_welch'] < 0.05 else "O intervalo inclui zero: os dados não demonstram diferença, o que não prova que as médias sejam iguais."
    madrugada = base_tipos.groupby('is_fim_de_semana')['turno_ajustado'].apply(lambda s: (s == 'MADRUGADA').mean() * 100)

    st.markdown(f"""
    <div class="insight-box">
        <strong>📖 Interpretação:</strong>
        <br>• {conclusao_dias}
        <br>• Agrupar os dias em dois blocos esconde diferenças: sexta tem {br(media_por_dia[4], 2)} registros/dia, sábado {br(media_por_dia[5], 2)} e domingo {br(media_por_dia[6], 2)}, contra {br(media_por_dia[[0, 1, 2, 3]].mean(), 2)} de segunda a quinta.
        <br>• A madrugada responde por {br(madrugada[1], 1)}% dos sinistros de fim de semana e {br(madrugada[0], 1)}% dos de dias úteis. A base não mede alcoolemia nem velocidade, então a causa desse padrão não pode ser afirmada.
    </div>
    """, unsafe_allow_html=True)

# ------------------------------------------------------------------------------
# TAB 5: MAPEAMENTO GEOESPACIAL INTERATIVO
# ------------------------------------------------------------------------------
with tab5:
    st.markdown("### 5. Distribuição Geográfica dos Registros")

    obitos_totais = df_completo['obitos'].sum()
    obitos_via = df_completo.groupby('tipo_via')['obitos'].sum()
    registros_via = df_completo['tipo_via'].value_counts(normalize=True) * 100
    letal_via = base_tipos.groupby('tipo_via')['obitos'].apply(lambda s: (s > 0).mean() * 100)

    st.markdown(f"""
    <div class="insight-box">
        <strong>🗺️ Vias urbanas e rodovias (sem os filtros):</strong>
        <br>• <strong>Vias urbanas:</strong> {br(registros_via['VIAS URBANAS'], 1)}% dos registros e {br(obitos_via['VIAS URBANAS'])} dos {br(obitos_totais)} óbitos ({br(obitos_via['VIAS URBANAS'] / obitos_totais * 100)}%), com letalidade de {br(letal_via['VIAS URBANAS'], 1)}% por sinistro.
        <br>• <strong>Estradas e rodovias:</strong> {br(registros_via['ESTRADAS E RODOVIAS'], 1)}% dos registros e {br(obitos_via['ESTRADAS E RODOVIAS'])} óbitos ({br(obitos_via['ESTRADAS E RODOVIAS'] / obitos_totais * 100)}%), com letalidade de {br(letal_via['ESTRADAS E RODOVIAS'], 1)}% por sinistro.
        <br>• Os demais óbitos não têm tipo de via informado. A velocidade não consta na base.
    </div>
    """, unsafe_allow_html=True)

    total_geo_completo = int(df_completo['geo_valida'].sum())
    map_mode = st.radio(
        "Selecione o Modo de Visualização do Mapa:",
        options=[
            "⚡ Mapa Dinâmico Interativo (Plotly com Filtros Ativos)",
            f"🗺️ Mapa Completo do Pipeline ({br(total_geo_completo)} registros em HTML)"
        ],
        horizontal=True
    )

    if "Mapa Dinâmico" in map_mode:
        df_geo_filtered = df_filtrado[df_filtrado['geo_valida']].copy()
        total_pontos = len(df_geo_filtered)

        st.caption(f"Exibindo **{br(total_pontos)}** registros com os filtros atuais. A validação usa um retângulo ao redor do município, não o limite municipal. Coordenadas exatas se repetem em alguns pontos, então a localização pode indicar uma referência, e não o local do impacto.")

        if total_pontos > 0:
            # Amostragem para manter a performance da renderização fluida se o usuário não filtrar muito
            amostra_geo = df_geo_filtered if total_pontos <= 4000 else df_geo_filtered.sample(4000, random_state=42)
            if total_pontos > 4000:
                st.info(f"⚡ Para otimizar o desempenho do navegador, o mapa exibe uma amostra aleatória de 4.000 de um total de {br(total_pontos)} pontos.")

            fig_map_live = px.scatter_map(
                amostra_geo,
                lat='lat',
                lon='lon',
                color='severidade_categoria',
                color_discrete_map=CORES_SEVERIDADE,
                category_orders={'severidade_categoria': ORDEM_SEVERIDADE},
                hover_name='tipo_sinistro_simplificado',
                hover_data={
                    'lat': False,
                    'lon': False,
                    'data_sinistro': True,
                    'tipo_registro': True,
                    'tipo_via': True,
                    'logradouro': True,
                    'obitos': True,
                    'feridos_graves': True,
                    'envolve_moto': True
                },
                zoom=11.5,
                center={'lat': -22.3145, 'lon': -49.0587},
                map_style='carto-positron',
                title="Registros de Trânsito — Bauru/SP",
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
            mostrar_grafico(fig_map_live)
        else:
            st.warning("Nenhum registro com coordenadas válidas encontrado para os filtros selecionados.")

    else:
        # Modo HTML completo
        if os.path.exists(MAPA_HTML_FILE):
            with open(MAPA_HTML_FILE, 'r', encoding='utf-8') as f:
                html_data = f.read()
            st.iframe(html_data, height=750)
        else:
            st.error(f"Arquivo de mapa não encontrado em `{MAPA_HTML_FILE}`.")

    st.markdown("#### Vias com Mais Registros (filtros aplicados, sem notificações)")
    df_sem_notificacao = df_filtrado[df_filtrado['tipo_registro'] != 'NOTIFICACAO']
    col_v1, col_v2 = st.columns(2)
    colunas_vias = {
        'logradouro': 'Via / Logradouro',
        'sinistros': 'Sinistros',
        'obitos': 'Óbitos',
        'feridos_graves': 'Feridos Graves',
        'feridos_leves': 'Feridos Leves'
    }
    with col_v1:
        st.caption("Por número de sinistros")
        st.dataframe(formatar_tabela(ranking_vias(df_sem_notificacao).rename(columns=colunas_vias)), width="stretch", hide_index=True)
    with col_v2:
        st.caption("Por número de óbitos")
        st.dataframe(formatar_tabela(ranking_vias(df_sem_notificacao, por='obitos').rename(columns=colunas_vias)), width="stretch", hide_index=True)
    st.caption("Contagens brutas: não há fluxo de veículos para medir o risco de cada via.")

# ------------------------------------------------------------------------------
# TAB 6: MODELO EXPLORATÓRIO (MACHINE LEARNING)
# ------------------------------------------------------------------------------
with tab6:
    st.markdown("### 6. Modelo Exploratório de Gravidade (Random Forest)")

    resultado_ml = get_ml_model()
    rf_model = resultado_ml['modelo']
    feat_cols = resultado_ml['features']

    st.markdown(f"""
    <div class="insight-box">
        <strong>🤖 O que este modelo é:</strong>
        <br>• Treinado na base comparável (sem os filtros) para descrever associações com desfecho grave ou fatal, presente em {br(resultado_ml['prevalencia'] * 100, 1)}% dos sinistros.
        <br>• Usa dados conhecidos só depois do sinistro, portanto não prevê acidentes futuros.
    </div>
    """, unsafe_allow_html=True)

    col_ml_metrics1, col_ml_metrics2, col_ml_metrics3, col_ml_metrics4 = st.columns(4)
    with col_ml_metrics1:
        st.metric("Acurácia no teste", f"{br(resultado_ml['acuracia'] * 100, 1)}%")
    with col_ml_metrics2:
        st.metric("Sempre prever a classe mais comum", f"{br(resultado_ml['referencia'] * 100, 1)}%")
    with col_ml_metrics3:
        st.metric("Acurácia balanceada", f"{br(resultado_ml['acuracia_balanceada'] * 100, 1)}%")
    with col_ml_metrics4:
        st.metric("ROC-AUC", br(resultado_ml['auc'], 3), f"{br(resultado_ml['n_teste'])} sinistros de teste", delta_color="off")

    if resultado_ml['acuracia'] <= resultado_ml['referencia'] + 0.005:
        st.warning("O modelo não supera a referência de sempre prever a classe mais comum.")

    col_feat, col_sim = st.columns([1.1, 1.2])

    with col_feat:
        st.markdown("#### 🏆 Top 10 Variáveis por Importância de Permutação")
        top_10 = resultado_ml['importancias'].head(10).reset_index()
        top_10.columns = ['Variável', 'Importância']

        traducao_feats = {
            'hora_num': 'Hora do Sinistro (0-23h)',
            'envolve_moto': 'Presença de Motocicleta',
            'via_VIA URBANA': 'Via Urbana',
            'envolve_auto': 'Presença de Automóvel',
            'tipo_COLISAO': 'Tipo: Colisão',
            'tipo_OUTROS': 'Tipo: Outros',
            'tipo_OUTROS / NAO INFORMADO': 'Tipo: Não Informado',
            'is_fim_de_semana': 'Fim de Semana (Sáb/Dom)',
            'envolve_pedestre': 'Presença de Pedestre',
            'tipo_CHOQUE': 'Tipo: Choque',
            'turno_MANHA': 'Turno: Manhã (6h-12h)',
            'turno_TARDE': 'Turno: Tarde (12h-18h)',
            'turno_NOITE': 'Turno: Noite (18h-24h)',
            'envolve_pesado': 'Veículo Pesado (Ônibus/Caminhão)',
            'envolve_bicicleta': 'Presença de Bicicleta'
        }
        top_10['Nome Legível'] = top_10['Variável'].map(lambda x: traducao_feats.get(x, x))
        top_10 = top_10.sort_values(by='Importância', ascending=True)

        fig_feat = px.bar(
            top_10,
            x='Importância',
            y='Nome Legível',
            orientation='h',
            text=top_10['Importância'].apply(lambda v: br(v, 3)),
            title="Piora na log-loss ao embaralhar a variável",
            color='Importância',
            color_continuous_scale='Viridis',
            template='plotly_dark'
        )
        fig_feat.update_traces(textposition='outside')
        fig_feat.update_layout(height=420, margin=dict(l=20, r=20, t=50, b=30), coloraxis_showscale=False, yaxis=dict(title=""))
        mostrar_grafico(fig_feat)
        st.caption("A importância indica quanto o modelo usa a variável, não o sentido do efeito nem uma relação causal.")

    with col_sim:
        st.markdown("#### ⚡ Simulador Exploratório de Gravidade")
        st.caption("Estimativa da gravidade supondo que o sinistro ocorreu; não é a chance de ele ocorrer.")

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

        st.markdown("---")
        st.metric(
            "Estimativa do modelo de desfecho grave ou fatal",
            f"{br(prob_grave, 1)}%",
            f"Média da base comparável: {br(resultado_ml['prevalencia'] * 100, 1)}%",
            delta_color="off"
        )
        st.progress(min(prob_grave / 100.0, 1.0))

    with st.expander("🖼️ Visualizar Gráfico do Modelo (`output/graficos/importancia_features_ml.png`)"):
        img_ml = os.path.join(GRAFICOS_DIR, "importancia_features_ml.png")
        if os.path.exists(img_ml):
            st.image(img_ml, caption="Importância de permutação no Random Forest", width="stretch")

# ------------------------------------------------------------------------------
# TAB 7: RECOMENDAÇÕES PARA GESTÃO PÚBLICA
# ------------------------------------------------------------------------------
with tab7:
    st.markdown("### 7. Recomendações para a Gestão Pública Municipal de Bauru")

    st.markdown("""
    As ações abaixo são **hipóteses a validar** com contagem de tráfego, inspeção em campo e dados de velocidade e alcoolemia, que não constam nesta base:
    """)

    obitos_rodovias = df_completo[normalizar_via(df_completo['logradouro']).isin(['SP 300', 'SP 225', 'SP 294'])]['obitos'].sum()

    col_rec1, col_rec2 = st.columns(2)

    with col_rec1:
        st.markdown(f"""
        <div class="metric-card" style="border-left: 4px solid #f59e0b;">
            <h4 style="color: #fbbf24; margin-bottom: 8px;">1. Travessia Segura para Pedestres</h4>
            <p style="font-size: 0.9rem; color: #cbd5e1; line-height: 1.5;">
                • <strong>Locais de atropelamento:</strong> O tipo tem a maior letalidade da base comparável ({br(letal_geral['ATROPELAMENTO'], 2)}% dos sinistros). Vale começar pelos locais recorrentes, confirmados em campo.<br>
                • <strong>Possíveis medidas:</strong> Faixas elevadas, refúgios centrais, iluminação e redução de velocidade, conforme o que a inspeção indicar.
            </p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"""
        <div class="metric-card" style="border-left: 4px solid #ef4444;">
            <h4 style="color: #f87171; margin-bottom: 8px;">2. Choques em Vias Urbanas</h4>
            <p style="font-size: 0.9rem; color: #cbd5e1; line-height: 1.5;">
                • <strong>Evidência:</strong> Nas vias urbanas, o choque tem {br(razao_urbana[0], 1)} vezes a letalidade da colisão.<br>
                • <strong>Primeiro passo:</strong> Inspecionar os locais para identificar o que foi atingido, pois a base não informa o objeto, e só então avaliar defensas ou atenuadores.
            </p>
        </div>
        """, unsafe_allow_html=True)

    with col_rec2:
        st.markdown(f"""
        <div class="metric-card" style="border-left: 4px solid #10b981;">
            <h4 style="color: #34d399; margin-bottom: 8px;">3. Articulação com DER-SP e Concessionárias</h4>
            <p style="font-size: 0.9rem; color: #cbd5e1; line-height: 1.5;">
                • <strong>Evidência:</strong> SP-300, SP-225 e SP-294 somam {br(obitos_rodovias)} dos {br(obitos_totais)} óbitos ({br(obitos_rodovias / obitos_totais * 100)}%).<br>
                • <strong>Próximo passo:</strong> Revisar os trechos em conjunto, com dados de velocidade e de fluxo, antes de definir radares ou mudanças em acessos. Trevos específicos não foram analisados.
            </p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"""
        <div class="metric-card" style="border-left: 4px solid #3b82f6;">
            <h4 style="color: #60a5fa; margin-bottom: 8px;">4. Motociclistas nas Vias com Mais Registros</h4>
            <p style="font-size: 0.9rem; color: #cbd5e1; line-height: 1.5;">
                • <strong>Evidência:</strong> Há motocicleta em {br(com_modal_informado(df_completo)['envolve_moto'].mean() * 100, 1)}% dos registros com modal informado. A base não mede o risco individual do motociclista.<br>
                • <strong>Possíveis medidas:</strong> Avaliar faixas azuis e áreas de espera em semáforos nas vias e horários com mais registros, como a Av. Nações Unidas, com estudo de fluxo.
            </p>
        </div>
        """, unsafe_allow_html=True)

    st.divider()
    st.markdown("#### Limitações dos Dados")
    st.markdown("""
    - **Notificações:** Quase sempre vêm sem dados de vítimas e nunca trazem veículos, e parte pode repetir sinistros já registrados.
    - **Sem Denominador de Exposição:** Não há fluxo de veículos nem frota, então volumes não medem risco.
    - **Sem Variáveis Comportamentais:** A base não traz velocidade nem alcoolemia.
    - **Vítima sem Veículo:** A base não indica em qual veículo cada vítima estava.
    - **Campos Vazios:** Contagens vazias viram zero, o que pode subestimar envolvidos.
    """)

# ------------------------------------------------------------------------------
# TAB 8: RELATÓRIO TÉCNICO & CENTRAL DE DOWNLOADS
# ------------------------------------------------------------------------------
with tab8:
    st.markdown("### 8. Central de Documentação, Relatórios e Downloads")

    st.markdown("Acesse o dataset, os gráficos e o relatório técnico:")

    c_dw1, c_dw2, c_dw3, c_dw4 = st.columns(4)

    with c_dw1:
        if os.path.exists(RELATORIO_PDF):
            with open(RELATORIO_PDF, "rb") as f_pdf:
                st.download_button(
                    label="📄 PDF de 30/09/2026 (histórico)",
                    data=f_pdf,
                    file_name="relatorio_seguranca_viaria_bauru.pdf",
                    mime="application/pdf",
                    width="stretch"
                )
            st.caption("Contém conclusões corrigidas pela errata abaixo.")
        else:
            st.button("Relatório PDF não encontrado", disabled=True, width="stretch")

    with c_dw2:
        if os.path.exists(RESUMO_FILE):
            with open(RESUMO_FILE, "rb") as f_resumo:
                st.download_button(
                    label="📊 Resumo Anual (CSV)",
                    data=f_resumo,
                    file_name="resumo_anual_bauru.csv",
                    mime="text/csv",
                    width="stretch"
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
            width="stretch"
        )

    with c_dw4:
        if os.path.exists(MAPA_HTML_FILE):
            with open(MAPA_HTML_FILE, "rb") as f_map:
                st.download_button(
                    label="🗺️ Mapa HTML Completo",
                    data=f_map,
                    file_name="mapa_acidentes_bauru.html",
                    mime="text/html",
                    width="stretch"
                )

    st.markdown("---")
    st.markdown("#### 🖼️ Galeria de Gráficos em Alta Resolução (PNG)")

    col_g1, col_g2, col_g3 = st.columns(3)

    graficos_lista = [
        ("acidentes_por_ano.png", "Evolução Anual"),
        ("acidentes_dia_e_hora.png", "Distribuição por Dia e Hora"),
        ("tipos_e_veiculos.png", "Letalidade por Tipo e Modais"),
        ("heatmap_dia_hora.png", "Matriz de Calor Dia x Hora"),
        ("importancia_features_ml.png", "Importância de Variáveis no Modelo")
    ]

    for idx, (nome_arquivo, titulo_g) in enumerate(graficos_lista):
        col_dest = [col_g1, col_g2, col_g3][idx % 3]
        caminho_g = os.path.join(GRAFICOS_DIR, nome_arquivo)
        with col_dest:
            st.markdown(f"**{titulo_g}** (`{nome_arquivo}`)")
            if os.path.exists(caminho_g):
                with open(caminho_g, "rb") as f_img:
                    img_bytes = f_img.read()
                st.image(img_bytes, width="stretch")
                st.download_button(
                    label=f"⬇️ Baixar {nome_arquivo}",
                    data=img_bytes,
                    file_name=nome_arquivo,
                    mime="image/png",
                    key=f"btn_dl_{nome_arquivo}",
                    width="stretch"
                )
            else:
                st.caption("Imagem não encontrada")

    st.markdown("---")
    st.markdown("#### 📑 Relatório Técnico na Íntegra")

    if os.path.exists(RELATORIO_MD):
        with open(RELATORIO_MD, 'r', encoding='utf-8') as f_rel:
            rel_md_texto = f_rel.read()
        with st.expander("Clique aqui para expandir e ler o Relatório Técnico completo", expanded=False):
            st.markdown(rel_md_texto)
    else:
        st.info("Arquivo de relatório markdown não encontrado.")

    if os.path.exists(ERRATA_MD):
        with open(ERRATA_MD, 'r', encoding='utf-8') as f_errata:
            errata_texto = f_errata.read()
        with st.expander("Errata do estudo de 30/09/2026", expanded=False):
            st.markdown(errata_texto)

# ==============================================================================
# RODAPÉ
# ==============================================================================
st.markdown("---")
st.markdown(f"""
<div style="text-align: center; color: #64748b; font-size: 0.85rem; padding: 12px;">
    <strong>Projeto de Ciência de Dados — Segurança Viária em Bauru/SP ({periodo_dados})</strong><br>
    Dados: Sistema Infosiga SP • Código IBGE: 3506003<br>
    Construído com Streamlit, Plotly, Pandas e Scikit-Learn
</div>
""", unsafe_allow_html=True)
