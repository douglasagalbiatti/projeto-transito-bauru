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
### Projeto: Análise de Sinistros de Trânsito em Bauru/SP

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

    nbf.v4.new_code_cell("""import sys
sys.path.append('..')
from scripts.atualizar_dados_infosiga import filtrar_bauru_de_arquivo_csv

df_raw = pd.concat([filtrar_bauru_de_arquivo_csv(p) for p in data_files], ignore_index=True)
print(f"Total de registros de Bauru extraídos: {len(df_raw)}")
df_raw.head()"""),

    nbf.v4.new_markdown_cell("""## 2. Auditoria de Tipos de Registro e Quebra Metodológica
No Infosiga SP, os registros entre 2015 e 2018 são de sinistros **fatais**. A partir de 2019, entram também sinistros **não fatais** e **notificações**, que nunca trazem veículos, quase sempre vêm sem dados de vítimas e têm proporção muito variável por ano."""),

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
- O total anual de registros não mede tendência, pois a cobertura das notificações varia por ano.
- Análises de letalidade e gravidade devem usar a base comparável: sinistros de 2019 em diante, sem notificações.
- O próximo passo é o tratamento dos tipos de dados, limpeza das coordenadas e feature engineering no `02-limpeza.ipynb`.""")
]

# ==============================================================================
# NOTEBOOK 02: LIMPEZA
# ==============================================================================
nb2_cells = [
    nbf.v4.new_markdown_cell("""# 🧹 Notebook 02: Limpeza, Tipagem e Feature Engineering
### Projeto: Análise de Sinistros de Trânsito em Bauru/SP

Neste notebook realizamos a higienização completa da base de Bauru:
1. Padronização de datas (`datetime`), extração de componentes temporais;
2. Limpeza de horários e turnos;
3. Conversão de coordenadas geográficas e validação de *bounding box*;
4. Criação de variáveis analíticas (*Feature Engineering*) para modais, gravidade e infraestrutura viária;
5. Exportação do dataset definitivo consolidado: `data/bauru_limpo.csv`."""),

    nbf.v4.new_code_cell("""import os
import glob
import sys
import pandas as pd
import numpy as np

sys.path.append('..')
from scripts.atualizar_dados_infosiga import filtrar_bauru_de_arquivo_csv
from src.metricas import classificar_severidade

# Ingestão das ocorrências brutas filtradas de Bauru
data_files = sorted(glob.glob('../data/sinistros_*.csv'))
df = pd.concat([filtrar_bauru_de_arquivo_csv(p) for p in data_files], ignore_index=True)
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
    try:
        val = int(str(h).strip().split(':')[0])
    except ValueError:
        return np.nan
    return val if 0 <= val <= 23 else np.nan

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

# Retângulo aproximado ao redor de Bauru (-22.6 a -22.0 lat, -49.4 a -48.8 lon); não é o limite municipal
df['geo_valida'] = (df['lat'].between(-22.6, -22.0)) & (df['lon'].between(-49.4, -48.8))
print(f"Pontos georreferenciados válidos: {df['geo_valida'].sum()} ({df['geo_valida'].sum()/len(df)*100:.1f}%)")"""),

    nbf.v4.new_markdown_cell("""## 3. Feature Engineering: Modais, Severidade e Vias"""),

    nbf.v4.new_code_cell("""# Conversão segura de colunas numéricas
cols_qtd = [
    'qtd_gravidade_fatal', 'qtd_gravidade_grave', 'qtd_gravidade_leve', 'qtd_gravidade_ileso', 'qtd_gravidade_nao_disponivel',
    'qtd_pedestre', 'qtd_bicicleta', 'qtd_motocicleta', 'qtd_automovel', 'qtd_onibus', 'qtd_caminhao', 'qtd_veic_outros'
]
for col in cols_qtd:
    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)

df['obitos'] = df['qtd_gravidade_fatal']
df['feridos_graves'] = df['qtd_gravidade_grave']
df['feridos_leves'] = df['qtd_gravidade_leve']
df['ilesos'] = df['qtd_gravidade_ileso']

# Flags binárias de modais
df['envolve_moto'] = (df['qtd_motocicleta'] > 0).astype(int)
df['envolve_auto'] = (df['qtd_automovel'] > 0).astype(int)
df['envolve_pedestre'] = (df['qtd_pedestre'] > 0).astype(int)
df['envolve_bicicleta'] = (df['qtd_bicicleta'] > 0).astype(int)
df['envolve_pesado'] = ((df['qtd_caminhao'] > 0) | (df['qtd_onibus'] > 0)).astype(int)

# Severidade binária (Grave ou Fatal)
df['severidade_grave_ou_fatal'] = ((df['obitos'] > 0) | (df['feridos_graves'] > 0)).astype(int)

# Classificação de severidade: registro sem dados de vítima não é 'sem vítimas'
df['severidade_categoria'] = classificar_severidade(df)

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
df['data_sinistro_dt'] = df['data_sinistro_dt'].dt.strftime('%Y-%m-%d')
df = df.drop_duplicates(subset=['id_sinistro'], keep='last').sort_values(by=['data_sinistro_dt', 'id_sinistro'])
df.to_csv(caminho_saida, index=False, sep=';', encoding='utf-8')
print(f"Dataset consolidado e limpo salvo com sucesso em {caminho_saida} ({len(df)} registros).")""")
]

# ==============================================================================
# NOTEBOOK 03: ANÁLISE ESTATÍSTICA E MACHINE LEARNING
# ==============================================================================
nb3_cells = [
    nbf.v4.new_markdown_cell("""# 📊 Notebook 03: Análise Exploratória, Inferência Estatística e Modelo Exploratório
### Projeto: Análise de Sinistros de Trânsito em Bauru/SP

Neste notebook desenvolvemos as análises centrais:
1. Evolução anual de registros, notificações e óbitos;
2. Comparação entre dias úteis e fins de semana (teste de Welch), com todos os dias do calendário;
3. Letalidade por tipo de sinistro e por tipo de via, na base comparável;
4. Matriz de calor dia vs hora;
5. Modelo exploratório (**Random Forest**), comparado à referência de sempre prever a classe mais comum.

**Base comparável:** sinistros de 2019 em diante, sem notificações. As regras estão em `src/metricas.py` e `src/modelo.py`, usadas também pelo painel e pelo relatório."""),

    nbf.v4.new_code_cell("""import sys
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

sys.path.append('..')
from src.metricas import base_comparavel, comparar_dias, razao_letalidade, tabela_letalidade
from src.modelo import treinar_modelo

plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
plt.rcParams['font.sans-serif'] = 'DejaVu Sans'
plt.rcParams['figure.dpi'] = 150

df = pd.read_csv('../data/bauru_limpo.csv', sep=';', encoding='utf-8', low_memory=False)
comparavel = base_comparavel(df)
print(f"Registros: {len(df)} | Base comparável: {len(comparavel)}")"""),

    nbf.v4.new_markdown_cell("""## 1. Evolução Anual
Até 2018 só há sinistros fatais. Desde 2019, a proporção de notificações varia muito, então o total anual não mede tendência. O último ano é parcial."""),

    nbf.v4.new_code_cell("""resumo_anual = df.groupby('ano').agg(
    sinistros=('tipo_registro', lambda s: int((s != 'NOTIFICACAO').sum())),
    notificacoes=('tipo_registro', lambda s: int((s == 'NOTIFICACAO').sum())),
    obitos=('obitos', 'sum'),
    feridos_graves=('feridos_graves', 'sum'),
    feridos_leves=('feridos_leves', 'sum')
).reset_index()

display(resumo_anual)

fig, ax1 = plt.subplots(figsize=(12, 5))
ax1.bar(resumo_anual['ano'], resumo_anual['sinistros'], color='#2b5c8f', width=0.6, label='Sinistros')
ax1.bar(resumo_anual['ano'], resumo_anual['notificacoes'], bottom=resumo_anual['sinistros'], color='#adb5bd', width=0.6, label='Notificações')
ax1.set_xlabel('Ano')
ax1.set_ylabel('Registros')
ax1.set_xticks(resumo_anual['ano'])
ax1.legend(loc='upper left')

ax2 = ax1.twinx()
ax2.plot(resumo_anual['ano'], resumo_anual['obitos'], color='#d9383a', linewidth=3, marker='o')
ax2.set_ylabel('Óbitos', color='#d9383a')
ax2.set_ylim(0, resumo_anual['obitos'].max() * 1.3)
ax2.grid(False)

plt.title('Registros e Óbitos em Bauru/SP')
plt.tight_layout()
plt.show()"""),

    nbf.v4.new_markdown_cell("""## 2. Dias Úteis vs Fins de Semana
Cada dia do calendário conta, inclusive os dias sem nenhum registro. Um p-valor alto não prova que as médias sejam iguais."""),

    nbf.v4.new_code_cell("""teste = comparar_dias(df[df['ano'] >= 2019])
print(f"Média em dias úteis: {teste['media_uteis']:.2f} registros/dia")
print(f"Média em fins de semana: {teste['media_fds']:.2f} registros/dia")
print(f"Diferença: {teste['diferenca']:.2f} (IC95% {teste['ic95'][0]:.2f} a {teste['ic95'][1]:.2f}), p = {teste['p_welch']:.3f}")
print(f"Dias sem registro: {teste['dias_sem_registro_pct']:.1f}%")
print("Média por dia (segunda a domingo):", teste['media_por_dia'].round(2).tolist())"""),

    nbf.v4.new_markdown_cell("""## 3. Letalidade na Base Comparável
Letalidade = sinistros com óbito ÷ sinistros do tipo. A base não informa velocidade nem qual objeto foi atingido."""),

    nbf.v4.new_code_cell("""display(tabela_letalidade(comparavel))

for tipo_via, base in comparavel[comparavel['tipo_via'] != 'NAO DISPONIVEL'].groupby('tipo_via'):
    razao, inferior, superior = razao_letalidade(base, 'CHOQUE', 'COLISAO')
    print(f"{tipo_via}: choque/colisão = {razao:.2f} (IC95% {inferior:.2f} a {superior:.2f})")"""),

    nbf.v4.new_markdown_cell("""## 4. Matriz de Calor: Horário do Dia vs Dia da Semana
Volume não equivale a risco, pois a base não traz o fluxo de veículos."""),

    nbf.v4.new_code_cell("""ordem_dias = ['Segunda-feira', 'Terça-feira', 'Quarta-feira', 'Quinta-feira', 'Sexta-feira', 'Sábado', 'Domingo']
heatmap_data = df[df['hora_num'].notnull()].pivot_table(
    index='dia_da_semana_limpo',
    columns='hora_num',
    values='id_sinistro',
    aggfunc='count',
    fill_value=0
).reindex(index=ordem_dias, columns=range(24), fill_value=0)

plt.figure(figsize=(14, 5))
sns.heatmap(heatmap_data, cmap='YlOrRd', annot=True, fmt='d', linewidths=0.5)
plt.title('Registros por Dia da Semana e Hora do Dia (Bauru/SP)')
plt.xlabel('Hora do Dia (0h - 23h)')
plt.ylabel('Dia da Semana')
plt.tight_layout()
plt.show()"""),

    nbf.v4.new_markdown_cell("""## 5. Modelo Exploratório (Random Forest)
O modelo usa dados conhecidos só depois do sinistro, então não prevê acidentes. A importância de permutação não indica sentido nem causa."""),

    nbf.v4.new_code_cell("""resultado = treinar_modelo(df)
print(f"Acurácia: {resultado['acuracia']:.3f} | Sempre prever a classe mais comum: {resultado['referencia']:.3f}")
print(f"Acurácia balanceada: {resultado['acuracia_balanceada']:.3f} | ROC-AUC: {resultado['auc']:.3f}")

top = resultado['importancias'].head(10)
plt.figure(figsize=(9, 5))
sns.barplot(x=top.values, y=top.index, color='#2b5c8f')
plt.title('Top 10 Variáveis por Importância de Permutação')
plt.xlabel('Piora na log-loss ao embaralhar a variável')
plt.tight_layout()
plt.show()""")
]

# ==============================================================================
# NOTEBOOK 04: VISUALIZAÇÕES E MAPEAMENTO GEOESPACIAL
# ==============================================================================
nb4_cells = [
    nbf.v4.new_markdown_cell("""# 🗺️ Notebook 04: Visualizações e Mapeamento Geoespacial Interativo
### Projeto: Análise de Sinistros de Trânsito em Bauru/SP

Neste notebook construímos o mapa dos registros:
1. Filtragem dos registros com coordenadas em um retângulo aproximado ao redor de Bauru;
2. Construção do mapa interativo via **Plotly Express** sobre renderização **Carto Positron**;
3. Estratificação visual de severidade, com os registros sem informação de vítimas à parte;
4. Exportação do arquivo interativo `output/graficos/mapa_acidentes.html`."""),

    nbf.v4.new_code_cell("""import sys
import pandas as pd
import plotly.express as px

sys.path.append('..')
from src.metricas import CORES_SEVERIDADE, ORDEM_SEVERIDADE

df = pd.read_csv('../data/bauru_limpo.csv', sep=';', encoding='utf-8', low_memory=False)
df_geo = df[df['geo_valida']].copy()
print(f"Registros com coordenadas no retângulo: {len(df_geo)} de {len(df)} ({len(df_geo)/len(df)*100:.1f}%)")"""),

    nbf.v4.new_markdown_cell("""## 1. Configuração do Mapa Temático Interativo"""),

    nbf.v4.new_code_cell("""fig = px.scatter_map(
    df_geo,
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
        'tipo_via': True,
        'logradouro': True,
        'obitos': True,
        'feridos_graves': True,
        'envolve_moto': True
    },
    zoom=11.5,
    center={'lat': -22.3145, 'lon': -49.0587},
    map_style='carto-positron',
    title='Registros de Trânsito em Bauru/SP',
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

    nbf.v4.new_markdown_cell("""## 2. Mapa Estático por Severidade

O GitHub não exibe o mapa interativo dentro do notebook; esta figura mostra os mesmos pontos em uma imagem."""),

    nbf.v4.new_code_cell("""import matplotlib.pyplot as plt
from src.metricas import br

fig_estatica, eixo = plt.subplots(figsize=(10, 9))
# Do menos grave ao fatal, para que os casos graves fiquem por cima
for severidade in ORDEM_SEVERIDADE[::-1]:
    pontos = df_geo[df_geo['severidade_categoria'] == severidade]
    eixo.scatter(
        pontos['lon'], pontos['lat'], c=CORES_SEVERIDADE[severidade],
        s=12 if severidade == 'FATAL' else 4, alpha=0.7, label=f"{severidade} ({br(len(pontos))})",
    )
eixo.set_aspect(1.08)  # Compensa a escala da longitude na latitude de Bauru
eixo.set_title(f"Registros com coordenadas em Bauru/SP ({br(len(df_geo))})", fontweight='bold')
eixo.set_xlabel('Longitude')
eixo.set_ylabel('Latitude')
eixo.legend(title='Severidade', loc='upper left', markerscale=2)
plt.show()"""),

    nbf.v4.new_markdown_cell("""## 3. Exportação do Artefato Interativo HTML"""),

    nbf.v4.new_code_cell("""import os

saida_mapa = '../output/graficos/mapa_acidentes.html'
os.makedirs('../output/graficos', exist_ok=True)
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
