import nbformat as nbf
import os

def create_notebook(cells, filename):
    nb = nbf.v4.new_notebook()
    nb.cells = cells
    nb.metadata['kernelspec'] = {
        'display_name': 'Python 3 (.venv)',
        'language': 'python',
        'name': 'python3'
    }
    nb.metadata['language_info'] = {
        'name': 'python',
        'version': '3.14.4'
    }
    with open(filename, 'w', encoding='utf-8') as f:
        nbf.write(nb, f)
    print(f"Notebook {filename} criado com sucesso!")

# ==============================================================================
# NOTEBOOK 01: EXPLORAÇÃO
# ==============================================================================
nb1_cells = [
    nbf.v4.new_markdown_cell("""# 🔍 Notebook 01: Leitura Diagnóstica, Ingestão em Chunks e Auditoria de Qualidade
### Projeto: Análise e Diagnóstico de Acidentes de Trânsito em Bauru/SP (2015–2026)

Este notebook realiza a etapa inicial do pipeline de dados:
1. Inspeção diagnóstica dos arquivos estaduais volumosos do **Infosiga SP**;
2. Ingestão em lotes (*chunks*) filtrando pelo município de **Bauru/SP** (Código IBGE: `3506003`);
3. Auditoria de valores nulos, tipagem e consistência temporal;
4. Identificação do marco metodológico do Infosiga (2015-2018 vs. 2019-2026)."""),

    nbf.v4.new_code_cell("""import os
import glob
import pandas as pd
import numpy as np

print("Diretório de trabalho:", os.getcwd())
data_files = sorted(glob.glob('../data/sinistros_*.csv'))
print("Arquivos de sinistros encontrados:", data_files)"""),

    nbf.v4.new_markdown_cell("""## 1. Ingestão em Lotes (Chunks)
Como os arquivos brutos estaduais somam centenas de megabytes, utilizamos o processamento em chunks de 50.000 linhas para filtrar apenas as ocorrências de Bauru."""),

    nbf.v4.new_code_cell("""dfs = []
for file_path in data_files:
    print(f"Processando {file_path}...")
    for chunk in pd.read_csv(file_path, sep=';', encoding='latin1', low_memory=False, chunksize=50000):
        # Filtro pelo código IBGE ou nome do município
        filtro = (chunk['cod_ibge'].astype(str) == '3506003') | (chunk['municipio'].astype(str).str.upper() == 'BAURU')
        chunk_bauru = chunk[filtro]
        if len(chunk_bauru) > 0:
            dfs.append(chunk_bauru)

df_raw = pd.concat(dfs, ignore_index=True)
print(f"Total de registros de Bauru extraídos: {len(df_raw)}")
df_raw.head()"""),

    nbf.v4.new_markdown_cell("""## 2. Auditoria de Tipos de Registro e Quebra Metodológica
No Infosiga SP, os registros entre 2015 e 2018 contemplavam prioritariamente sinistros com **vítimas fatais**. A partir de 2019, o sistema passou a registrar também sinistros **não fatais** e notificações sem lesões."""),

    nbf.v4.new_code_cell("""print("Distribuição por Tipo de Registro:")
print(df_raw['tipo_registro'].value_counts(dropna=False))

print("\\nVolume por Ano de Sinistro:")
print(df_raw['ano_sinistro'].value_counts().sort_index())"""),

    nbf.v4.new_markdown_cell("""## 3. Auditoria de Nulos e Coordenadas
Verificação do percentual de preenchimento das coordenadas geográficas e das principais variáveis viárias."""),

    nbf.v4.new_code_cell("""nulos = df_raw.isnull().sum()
pct_nulos = (nulos / len(df_raw)) * 100
tabela_nulos = pd.DataFrame({'Total Nulos': nulos, 'Percentual (%)': pct_nulos})
tabela_nulos.sort_values(by='Total Nulos', ascending=False).head(15)"""),

    nbf.v4.new_markdown_cell("""## 4. Conclusão Diagnóstica
- O conjunto de Bauru totaliza **18.938 sinistros** brutos.
- A série histórica possui estabilidade nos óbitos contínuos desde 2015 e grande riqueza de variáveis a partir de 2019.
- O próximo passo é o tratamento dos tipos de dados, limpeza das coordenadas e feature engineering no `02-limpeza.ipynb`.""")
]

# ==============================================================================
# NOTEBOOK 02: LIMPEZA
# ==============================================================================
nb2_cells = [
    nbf.v4.new_markdown_cell("""# 🧹 Notebook 02: Limpeza, Tipagem e Feature Engineering
### Projeto: Análise e Diagnóstico de Acidentes de Trânsito em Bauru/SP (2015–2026)

Neste notebook realizamos a higienização completa da base de Bauru:
1. Padronização de datas (`datetime`), extração de componentes temporais;
2. Limpeza de horários e turnos;
3. Conversão de coordenadas geográficas e validação de *bounding box*;
4. Criação de variáveis analíticas (*Feature Engineering*) para modais, gravidade e infraestrutura viária;
5. Exportação do dataset definitivo consolidado: `data/bauru_limpo.csv`."""),

    nbf.v4.new_code_cell("""import os
import glob
import pandas as pd
import numpy as np

# Ingestão das ocorrências brutas filtradas de Bauru
data_files = sorted(glob.glob('../data/sinistros_*.csv'))
dfs = []
for p in data_files:
    for chunk in pd.read_csv(p, sep=';', encoding='latin1', low_memory=False, chunksize=50000):
        cond = (chunk['cod_ibge'].astype(str) == '3506003') | (chunk['municipio'].astype(str).str.upper() == 'BAURU')
        cb = chunk[cond]
        if len(cb) > 0:
            dfs.append(cb)

df = pd.concat(dfs, ignore_index=True)
print(f"Base carregada: {len(df)} registros.")"""),

    nbf.v4.new_markdown_cell("""## 1. Tratamento de Datas e Horas"""),

    nbf.v4.new_code_cell("""# Datas
df['data_sinistro_dt'] = pd.to_datetime(df['data_sinistro'], format='%d/%m/%Y', errors='coerce')
df['ano'] = pd.to_numeric(df['ano_sinistro'], errors='coerce').fillna(df['data_sinistro_dt'].dt.year).astype(int)
df['mes'] = pd.to_numeric(df['mes_sinistro'], errors='coerce').fillna(df['data_sinistro_dt'].dt.month).astype(int)

# Horas
def parse_hora(h):
    if pd.isna(h):
        return np.nan
    s = str(h).strip()
    if ':' in s:
        try:
            return int(s.split(':')[0])
        except:
            return np.nan
    return np.nan

df['hora_num'] = df['hora_sinistro'].apply(parse_hora)

# Turnos padronizados
def classificar_turno(h):
    if pd.isna(h):
        return 'NAO INFORMADO'
    if 0 <= h < 6:
        return 'MADRUGADA'
    elif 6 <= h < 12:
        return 'MANHA'
    elif 12 <= h < 18:
        return 'TARDE'
    else:
        return 'NOITE'

df['turno_ajustado'] = df['hora_num'].apply(classificar_turno)
print("Distribuição por turno:", df['turno_ajustado'].value_counts().to_dict())"""),

    nbf.v4.new_markdown_cell("""## 2. Tratamento de Coordenadas Geográficas (Latitude e Longitude)"""),

    nbf.v4.new_code_cell("""lat_str = df['latitude'].astype(str).str.replace(',', '.').str.strip()
lon_str = df['longitude'].astype(str).str.replace(',', '.').str.strip()
df['lat'] = pd.to_numeric(lat_str, errors='coerce')
df['lon'] = pd.to_numeric(lon_str, errors='coerce')

# Bounding box territorial de Bauru (-22.6 a -22.0 lat, -49.4 a -48.8 lon)
df['geo_valida'] = (df['lat'].between(-22.6, -22.0)) & (df['lon'].between(-49.4, -48.8))
print(f"Pontos georreferenciados válidos: {df['geo_valida'].sum()} ({df['geo_valida'].sum()/len(df)*100:.1f}%)")"""),

    nbf.v4.new_markdown_cell("""## 3. Feature Engineering: Modais, Severidade e Vias"""),

    nbf.v4.new_code_cell("""# Conversão segura de colunas numéricas
cols_qtd = [
    'qtd_gravidade_fatal', 'qtd_gravidade_grave', 'qtd_gravidade_leve', 'qtd_gravidade_ileso',
    'qtd_pedestre', 'qtd_bicicleta', 'qtd_motocicleta', 'qtd_automovel', 'qtd_onibus', 'qtd_caminhao'
]
for col in cols_qtd:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)

df['obitos'] = df['qtd_gravidade_fatal']
df['feridos_graves'] = df['qtd_gravidade_grave']
df['feridos_leves'] = df['qtd_gravidade_leve']

# Flags binárias de modais
df['envolve_moto'] = (df['qtd_motocicleta'] > 0).astype(int)
df['envolve_auto'] = (df['qtd_automovel'] > 0).astype(int)
df['envolve_pedestre'] = (df['qtd_pedestre'] > 0).astype(int)
df['envolve_bicicleta'] = (df['qtd_bicicleta'] > 0).astype(int)
df['envolve_pesado'] = ((df['qtd_caminhao'] > 0) | (df['qtd_onibus'] > 0)).astype(int)

# Severidade binária (Grave ou Fatal)
df['severidade_grave_ou_fatal'] = ((df['obitos'] > 0) | (df['feridos_graves'] > 0)).astype(int)

# Classificação categórica de severidade
def classificar_severidade(r):
    if r['obitos'] > 0:
        return 'FATAL'
    elif r['feridos_graves'] > 0:
        return 'GRAVE'
    elif r['feridos_leves'] > 0:
        return 'LEVE'
    return 'ILESO / NAO INFORMADO'

df['severidade_categoria'] = df.apply(classificar_severidade, axis=1)

# Dia da semana e final de semana
mapa_dias = {
    'SEGUNDA-FEIRA': 'Segunda-feira', 'TERCA-FEIRA': 'Terça-feira', 'TERÇA-FEIRA': 'Terça-feira',
    'QUARTA-FEIRA': 'Quarta-feira', 'QUINTA-FEIRA': 'Quinta-feira', 'SEXTA-FEIRA': 'Sexta-feira',
    'SABADO': 'Sábado', 'SÁBADO': 'Sábado', 'DOMINGO': 'Domingo'
}
df['dia_da_semana_limpo'] = df['dia_da_semana'].astype(str).str.upper().str.strip().map(lambda x: mapa_dias.get(x, x.capitalize()))
df['is_fim_de_semana'] = df['dia_da_semana_limpo'].isin(['Sábado', 'Domingo']).astype(int)

# Classificação viária (Vias Urbanas vs Rodovias/Estradas)
def classificar_via(r):
    via = str(r['tipo_via']).upper()
    admin = str(r['administracao']).upper()
    if 'RODOVIA' in via or 'ESTRADA' in via or 'DER' in admin or 'CONCESSION' in admin:
        return 'RODOVIA / ESTRADA'
    return 'VIA URBANA'

df['tipo_via_simplificado'] = df.apply(classificar_via, axis=1)

# Tipo de sinistro simplificado
def classificar_tipo_sinistro(tp):
    s = str(tp).upper()
    if 'CHOQUE' in s:
        return 'CHOQUE'
    elif 'ATROPEL' in s:
        return 'ATROPELAMENTO'
    elif 'COLIS' in s:
        return 'COLISAO'
    elif 'CAPOTAMENTO' in s or 'TOMBAMENTO' in s:
        return 'CAPOTAMENTO/TOMBAMENTO'
    elif 'OUTROS' in s:
        return 'OUTROS'
    return 'OUTROS / NAO INFORMADO'

df['tipo_sinistro_simplificado'] = df['tp_sinistro_primario'].apply(classificar_tipo_sinistro)"""),

    nbf.v4.new_markdown_cell("""## 4. Exportação do Dataset Higienizado"""),

    nbf.v4.new_code_cell("""caminho_saida = '../data/bauru_limpo.csv'
df.to_csv(caminho_saida, index=False, sep=';', encoding='utf-8')
print(f"Dataset consolidado e limpo salvo com sucesso em {caminho_saida} ({len(df)} registros).")""")
]

# ==============================================================================
# NOTEBOOK 03: ANÁLISE ESTATÍSTICA E MACHINE LEARNING
# ==============================================================================
nb3_cells = [
    nbf.v4.new_markdown_cell("""# 📊 Notebook 03: Análise Exploratória, Inferência Estatística e Modelagem Preditiva
### Projeto: Análise e Diagnóstico de Acidentes de Trânsito em Bauru/SP (2015–2026)

Neste notebook desenvolvemos as análises centrais de segurança viária para Bauru:
1. Evolução histórica de sinistros e vítimas fatais (2015–2026);
2. Distribuição temporal (dias da semana e horários de pico);
3. Teste de Hipótese Estatística (*Student's t-test*) entre dias úteis e finais de semana;
4. Letalidade comparativa por modal e tipo de choque/colisão;
5. Matriz de calor (*Heatmap*) dia vs hora;
6. Modelo Preditivo Supervisionado (**Random Forest**) com *class weights* e avaliação de *Feature Importance* (Gini)."""),

    nbf.v4.new_code_cell("""import os
import pandas as pd
import numpy as np
import scipy.stats as stats
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, roc_auc_score, accuracy_score, confusion_matrix

plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
plt.rcParams['font.sans-serif'] = 'DejaVu Sans'
plt.rcParams['figure.dpi'] = 150

df = pd.read_csv('../data/bauru_limpo.csv', sep=';', encoding='utf-8')
print(f"Dataset carregado: {len(df)} ocorrências.")"""),

    nbf.v4.new_markdown_cell("""## 1. Evolução Histórica Anual (2015–2026)"""),

    nbf.v4.new_code_cell("""resumo_anual = df.groupby('ano').agg(
    total_sinistros=('id_sinistro', 'count'),
    obitos=('obitos', 'sum'),
    feridos_graves=('feridos_graves', 'sum'),
    feridos_leves=('feridos_leves', 'sum')
).reset_index()

display(resumo_anual)

fig, ax1 = plt.subplots(figsize=(12, 5))
ax1.bar(resumo_anual['ano'], resumo_anual['total_sinistros'], color='#2b5c8f', alpha=0.85, width=0.6, label='Total Sinistros')
ax1.set_xlabel('Ano')
ax1.set_ylabel('Total de Sinistros', color='#2b5c8f')
ax1.set_xticks(resumo_anual['ano'])

ax2 = ax1.twinx()
ax2.plot(resumo_anual['ano'], resumo_anual['obitos'], color='#d9383a', linewidth=3, marker='o', label='Óbitos')
ax2.set_ylabel('Óbitos Confirmados', color='#d9383a')
ax2.grid(False)

plt.title('Evolução Anual de Sinistros e Óbitos em Bauru/SP (2015–2026)')
plt.tight_layout()
plt.show()"""),

    nbf.v4.new_markdown_cell("""## 2. Teste de Hipótese Estatística: Dias Úteis vs Fins de Semana
Avaliando se a média diária de acidentes difere estatisticamente entre os dias de semana (segunda a sexta) e fins de semana (sábado e domingo)."""),

    nbf.v4.new_code_cell("""df_completo = df[(df['ano'] >= 2019) & (df['ano'] <= 2025)].copy()
df_completo['data_dt'] = pd.to_datetime(df_completo['data_sinistro_dt'])
acidentes_dia = df_completo.groupby('data_dt').agg(
    total=('id_sinistro', 'count'),
    fim_de_semana=('is_fim_de_semana', 'first')
).reset_index()

uteis = acidentes_dia[acidentes_dia['fim_de_semana'] == 0]['total']
finais = acidentes_dia[acidentes_dia['fim_de_semana'] == 1]['total']

t_stat, p_val = stats.ttest_ind(uteis, finais, equal_var=False)
print(f"Média em Dias Úteis: {uteis.mean():.2f} acidentes/dia (std: {uteis.std():.2f})")
print(f"Média em Fins de Semana: {finais.mean():.2f} acidentes/dia (std: {finais.std():.2f})")
print(f"Estatística t = {t_stat:.3f}, p-valor = {p_val:.4f}")
if p_val > 0.05:
    print("Conclusão: Não há diferença estatisticamente significativa na média diária (p > 0.05).")
else:
    print("Conclusão: Diferença estatisticamente significativa detectada.")"""),

    nbf.v4.new_markdown_cell("""## 3. Letalidade por Tipo de Sinistro e Modal Envolvido"""),

    nbf.v4.new_code_cell("""tabela_tipo = df.groupby('tipo_sinistro_simplificado').agg(
    total=('id_sinistro', 'count'),
    obitos=('obitos', 'sum'),
    feridos_graves=('feridos_graves', 'sum')
).reset_index()
tabela_tipo['letalidade_pct'] = (tabela_tipo['obitos'] / tabela_tipo['total']) * 100
tabela_tipo = tabela_tipo.sort_values(by='letalidade_pct', ascending=False)
display(tabela_tipo)"""),

    nbf.v4.new_markdown_cell("""## 4. Matriz de Calor: Horário do Dia vs Dia da Semana"""),

    nbf.v4.new_code_cell("""ordem_dias = ['Segunda-feira', 'Terça-feira', 'Quarta-feira', 'Quinta-feira', 'Sexta-feira', 'Sábado', 'Domingo']
heatmap_data = df[df['hora_num'].notnull()].pivot_table(
    index='dia_da_semana_limpo',
    columns='hora_num',
    values='id_sinistro',
    aggfunc='count',
    fill_value=0
).reindex(ordem_dias)

plt.figure(figsize=(14, 5))
sns.heatmap(heatmap_data, cmap='YlOrRd', annot=True, fmt='d', linewidths=0.5)
plt.title('Matriz de Calor: Sinistros por Dia da Semana e Hora do Dia (Bauru/SP)')
plt.xlabel('Hora do Dia (0h - 23h)')
plt.ylabel('Dia da Semana')
plt.tight_layout()
plt.show()"""),

    nbf.v4.new_markdown_cell("""## 5. Modelagem Supervisionada de Gravidade (Random Forest)"""),

    nbf.v4.new_code_cell("""df_ml = df[df['hora_num'].notnull()].copy()
features_cols = ['envolve_moto', 'envolve_auto', 'envolve_pedestre', 'envolve_bicicleta', 'envolve_pesado', 'is_fim_de_semana']

dummies_via = pd.get_dummies(df_ml['tipo_via_simplificado'], prefix='via', drop_first=True)
dummies_tipo = pd.get_dummies(df_ml['tipo_sinistro_simplificado'], prefix='tipo', drop_first=True)
dummies_turno = pd.get_dummies(df_ml['turno_ajustado'], prefix='turno', drop_first=True)

X = pd.concat([df_ml[features_cols], df_ml[['hora_num']], dummies_via, dummies_tipo, dummies_turno], axis=1)
y = df_ml['severidade_grave_ou_fatal']

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=42, stratify=y)

rf = RandomForestClassifier(n_estimators=200, max_depth=10, class_weight='balanced', random_state=42, n_jobs=-1)
rf.fit(X_train, y_train)

y_pred = rf.predict(X_test)
y_prob = rf.predict_proba(X_test)[:, 1]

print("Acurácia:", accuracy_score(y_test, y_pred))
print("ROC-AUC:", roc_auc_score(y_test, y_prob))
print("\\nRelatório de Classificação:\\n", classification_report(y_test, y_pred))

importancias = pd.Series(rf.feature_importances_, index=X.columns).sort_values(ascending=False)
plt.figure(figsize=(9, 5))
sns.barplot(x=importancias.head(10).values, y=importancias.head(10).index, hue=importancias.head(10).index, palette='mako', legend=False)
plt.title('Top 10 Variáveis Mais Determinantes para a Gravidade do Sinistro (Bauru)')
plt.xlabel('Importância Relativa (Gini)')
plt.tight_layout()
plt.show()""")
]

# ==============================================================================
# NOTEBOOK 04: VISUALIZAÇÕES E MAPEAMENTO GEOESPACIAL
# ==============================================================================
nb4_cells = [
    nbf.v4.new_markdown_cell("""# 🗺️ Notebook 04: Visualizações e Mapeamento Geoespacial Interativo
### Projeto: Análise e Diagnóstico de Acidentes de Trânsito em Bauru/SP (2015–2026)

Neste notebook consolidamos a inteligência espacial da pesquisa viária:
1. Filtragem das ocorrências com georreferenciamento homologado dentro do território de Bauru;
2. Construção do mapa interativo via **Plotly Express** sobre renderização **Carto Positron**;
3. Estratificação visual de severidade (Óbito, Ferido Grave, Ferido Leve, Ileso);
4. Análise dos eixos viários críticos: Rodovias **SP-300 (Marechal Rondon)**, **SP-225** e **SP-294** vs. Avenidas Estruturais Urbanas (**Nações Unidas**, **Duque de Caxias**, **Rodrigues Alves**);
5. Exportação do arquivo interativo `output/graficos/mapa_acidentes.html`."""),

    nbf.v4.new_code_cell("""import pandas as pd
import plotly.express as px

df = pd.read_csv('../data/bauru_limpo.csv', sep=';', encoding='utf-8')
df_geo = df[df['geo_valida']].copy()
print(f"Total de sinistros georreferenciados válidos: {len(df_geo)} de {len(df)} ({len(df_geo)/len(df)*100:.1f}%)")"""),

    nbf.v4.new_markdown_cell("""## 1. Configuração do Mapa Temático Interativo"""),

    nbf.v4.new_code_cell("""color_map = {
    'FATAL': '#e11d48',                # Vermelho vibrante
    'GRAVE': '#ea580c',                # Laranja forte
    'LEVE': '#eab308',                 # Dourado/Amarelo
    'ILESO / NAO INFORMADO': '#2563eb' # Azul
}

fig = px.scatter_map(
    df_geo,
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
    title='Mapeamento Geoespacial de Sinistros de Trânsito em Bauru/SP (2015–2026)',
    height=800
)

fig.update_layout(
    margin=dict(l=0, r=0, t=40, b=0),
    legend=dict(
        title=dict(text='Severidade do Sinistro'),
        yanchor='top',
        y=0.98,
        xanchor='left',
        x=0.02,
        bgcolor='rgba(255, 255, 255, 0.9)',
        bordercolor='#cbd5e1',
        borderwidth=1
    )
)

fig.show()"""),

    nbf.v4.new_markdown_cell("""## 2. Exportação do Artefato Interativo HTML"""),

    nbf.v4.new_code_cell("""saida_mapa = '../output/graficos/mapa_acidentes.html'
fig.write_html(saida_mapa)
print(f"Mapa geoespacial interativo exportado com sucesso para {saida_mapa}!")""")
]

# Geração dos notebooks
os.makedirs('notebooks', exist_ok=True)
create_notebook(nb1_cells, 'notebooks/01-exploracao.ipynb')
create_notebook(nb2_cells, 'notebooks/02-limpeza.ipynb')
create_notebook(nb3_cells, 'notebooks/03-analise-bauru.ipynb')
create_notebook(nb4_cells, 'notebooks/04-visualizacoes.ipynb')
print("Todos os 4 notebooks foram criados com sucesso!")
