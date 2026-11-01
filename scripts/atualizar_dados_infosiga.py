"""
Script de Automação para Obtenção, Tratamento, Limpeza e Inserção Incremental
dos Dados do InfoSiga SP para o Projeto de Segurança Viária de Bauru/SP.

Fonte: Portal de Dados Abertos do Estado de São Paulo (API CKAN / InfoSiga)
Endpoint Oficial: https://dadosabertos.sp.gov.br/api/3/action/package_show?id=eventos-de-sinistro
"""

import os
import re
import sys
import json
import shutil
import argparse
import tempfile
import urllib.request
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.metricas import classificar_severidade

# ==============================================================================
# CONFIGURAÇÕES E CAMINHOS DO PROJETO
# ==============================================================================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
RELATORIOS_DIR = os.path.join(OUTPUT_DIR, "relatorios")

DATA_FILE_BAURU = os.path.join(DATA_DIR, "bauru_limpo.csv")
RESUMO_FILE = os.path.join(RELATORIOS_DIR, "resumo_anual_bauru.csv")

CKAN_API_URL = "https://dadosabertos.sp.gov.br/api/3/action/package_show?id=eventos-de-sinistro"
COD_IBGE_BAURU = 3506003
MUNICIPIO_NOME = "BAURU"

# Meses recentes são baixados de novo para incorporar revisões do Infosiga.
MESES_REVISAO = 3

COLUNAS_OBRIGATORIAS = [
    "id_sinistro", "tipo_registro", "data_sinistro", "ano_sinistro", "mes_sinistro", "hora_sinistro",
    "dia_da_semana", "logradouro", "tipo_via", "latitude", "longitude", "administracao", "tp_sinistro_primario",
    "qtd_gravidade_fatal", "qtd_gravidade_grave", "qtd_gravidade_leve", "qtd_gravidade_ileso",
    "qtd_gravidade_nao_disponivel", "qtd_pedestre", "qtd_bicicleta", "qtd_motocicleta", "qtd_automovel",
    "qtd_onibus", "qtd_caminhao", "qtd_veic_outros",
]


# ==============================================================================
# FUNÇÕES DE CONSULTA À API DO INFOSIGA (CKAN)
# ==============================================================================
def consultar_recursos_ckan():
    """
    Consulta a API REST do Portal de Dados Abertos de SP para obter a lista
    de arquivos mensais de sinistros disponíveis para download.
    """
    print("📡 Consultando API CKAN do Governo de São Paulo...")
    req = urllib.request.Request(
        CKAN_API_URL,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) DadosAbertosBauru/1.0"}
    )
    
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            conteudo = json.loads(response.read().decode("utf-8"))
            if not conteudo.get("success"):
                raise ValueError("A resposta da API CKAN indicou falha na requisição.")
            
            recursos = conteudo.get("result", {}).get("resources", [])
            print(f"✅ Sucesso: {len(recursos)} recursos mensais encontrados no portal.")
            return recursos
    except Exception as e:
        print(f"❌ Erro ao conectar à API CKAN: {e}")
        return []


def extrair_ano_mes_recurso(nome_recurso, url_recurso):
    """
    Extrai o ano e mês do nome ou URL do recurso.
    Exemplos de padrões comuns:
    - 'sinistros_09-2026.csv' -> ano=2026, mes=9
    - 'Eventos de Sinistro - Setembro de 2026' -> ano=2026, mes=9
    """
    # Tenta extrair pela URL: sinistros_MM-AAAA.csv
    match_url = re.search(r"sinistros_(\d{2})-(\d{4})\.csv", url_recurso, re.IGNORECASE)
    if match_url:
        mes = int(match_url.group(1))
        ano = int(match_url.group(2))
        return ano, mes, f"{ano}/{mes:02d}"
    
    # Mapeamento por extenso no nome
    meses_map = {
        "janeiro": 1, "fevereiro": 2, "março": 3, "marco": 3,
        "abril": 4, "maio": 5, "junho": 6, "julho": 7,
        "agosto": 8, "setembro": 9, "outubro": 10, "novembro": 11, "dezembro": 12
    }
    nome_lower = nome_recurso.lower()
    for mes_nome, mes_num in meses_map.items():
        if mes_nome in nome_lower:
            match_ano = re.search(r"(20\d{2})", nome_recurso)
            if match_ano:
                ano = int(match_ano.group(1))
                return ano, mes_num, f"{ano}/{mes_num:02d}"
                
    return None, None, None


def mes_na_janela(rotulo, ultimo_rotulo):
    """Indica se o mês AAAA/MM está na janela de revisão ou é posterior ao último mês da base."""
    ano, mes = map(int, rotulo.split("/"))
    ultimo_ano, ultimo_mes = map(int, ultimo_rotulo.split("/"))
    return (ano * 12 + mes) > (ultimo_ano * 12 + ultimo_mes - MESES_REVISAO)


def baixar_arquivo(url, destino, tentativas=3):
    """Baixa um arquivo; retorna False se todas as tentativas falharem."""
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 DadosAbertosBauru/1.0"})
    for tentativa in range(1, tentativas + 1):
        try:
            with urllib.request.urlopen(req, timeout=300) as resposta, open(destino, "wb") as arquivo:
                shutil.copyfileobj(resposta, arquivo)
            return True
        except OSError as e:
            print(f"⚠️ Falha no download (tentativa {tentativa}/{tentativas}): {type(e).__name__}")
    return False


def obter_ultimo_ano_mes_cadastrado():
    """
    Identifica qual é o último ano/mês presente na base local limpa de Bauru.
    """
    if not os.path.exists(DATA_FILE_BAURU):
        return None
    try:
        df = pd.read_csv(DATA_FILE_BAURU, sep=";", usecols=["ano_mes_sinistro"], low_memory=False)
        ult_ano_mes = df["ano_mes_sinistro"].dropna().sort_values().iloc[-1]
        return str(ult_ano_mes)
    except Exception as e:
        print(f"Aviso ao ler ano_mes_sinistro: {e}")
        return None


# ==============================================================================
# FUNÇÕES DE LIMPEZA E ENGENHARIA DE RECURSOS (ETL)
# ==============================================================================
def parse_hora(h):
    """Converte horários em formato string ('14:30', '14') para inteiro da hora (14)."""
    if pd.isna(h):
        return np.nan
    s = str(h).strip()
    try:
        val = int(s.split(":")[0])
    except ValueError:
        return np.nan
    return val if 0 <= val <= 23 else np.nan


def classificar_via(r):
    """Classifica a via entre 'RODOVIA / ESTRADA' e 'VIA URBANA'."""
    via = str(r.get("tipo_via", "")).upper()
    admin = str(r.get("administracao", "")).upper()
    if "RODOVIA" in via or "ESTRADA" in via or "DER" in admin or "CONCESSION" in admin:
        return "RODOVIA / ESTRADA"
    return "VIA URBANA"


def classificar_tipo_sinistro(tp):
    """Padroniza os tipos primários de sinistro em categorias limpas."""
    s = str(tp).upper()
    if "CHOQUE" in s:
        return "CHOQUE"
    elif "ATROPEL" in s:
        return "ATROPELAMENTO"
    elif "COLIS" in s:
        return "COLISAO"
    elif "CAPOTAMENTO" in s or "TOMBAMENTO" in s:
        return "CAPOTAMENTO/TOMBAMENTO"
    elif "OUTROS" in s:
        return "OUTROS"
    return "OUTROS / NAO INFORMADO"


def classificar_turno(h):
    """Determina o turno do dia com base na hora cheia."""
    if pd.isna(h):
        return "NAO INFORMADO"
    if 0 <= h < 6:
        return "MADRUGADA"
    elif 6 <= h < 12:
        return "MANHA"
    elif 12 <= h < 18:
        return "TARDE"
    else:
        return "NOITE"


def aplicar_regras_limpeza_bauru(df_raw):
    """
    Aplica todas as transformações, cálculos e padronizações necessárias
    específicas para os dados de Bauru.
    """
    ausentes = sorted(set(COLUNAS_OBRIGATORIAS) - set(df_raw.columns))
    if ausentes:
        raise ValueError(f"Colunas ausentes no arquivo do Infosiga: {ausentes}")

    df = df_raw.copy()
    
    # Tratamento de datas
    df["data_sinistro_dt"] = pd.to_datetime(df["data_sinistro"], format="%d/%m/%Y", errors="coerce")
    df["ano"] = pd.to_numeric(df["ano_sinistro"], errors="coerce").fillna(df["data_sinistro_dt"].dt.year).fillna(0).astype(int)
    df["mes"] = pd.to_numeric(df["mes_sinistro"], errors="coerce").fillna(df["data_sinistro_dt"].dt.month).fillna(0).astype(int)
    
    # Ano/Mês no padrão AAAA/MM
    if "ano_mes_sinistro" not in df.columns or df["ano_mes_sinistro"].isnull().any():
        df["ano_mes_sinistro"] = df.apply(lambda r: f"{r['ano']}/{r['mes']:02d}" if r['ano'] > 0 and r['mes'] > 0 else np.nan, axis=1)

    # Tratamento da hora
    df["hora_num"] = df["hora_sinistro"].apply(parse_hora)
    
    # Tratamento de latitude e longitude
    lat_str = df["latitude"].astype(str).str.replace(",", ".").str.strip()
    lon_str = df["longitude"].astype(str).str.replace(",", ".").str.strip()
    df["lat"] = pd.to_numeric(lat_str, errors="coerce")
    df["lon"] = pd.to_numeric(lon_str, errors="coerce")
    
    # Bounding Box de Bauru
    df["geo_valida"] = (df["lat"].between(-22.6, -22.0)) & (df["lon"].between(-49.4, -48.8))
    
    # Contagem de vítimas e modais
    cols_qtd = [
        "qtd_gravidade_fatal", "qtd_gravidade_grave", "qtd_gravidade_leve", "qtd_gravidade_ileso", "qtd_gravidade_nao_disponivel",
        "qtd_pedestre", "qtd_bicicleta", "qtd_motocicleta", "qtd_automovel", "qtd_onibus", "qtd_caminhao", "qtd_veic_outros"
    ]
    for col in cols_qtd:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
            
    df["obitos"] = df["qtd_gravidade_fatal"]
    df["feridos_graves"] = df["qtd_gravidade_grave"]
    df["feridos_leves"] = df["qtd_gravidade_leve"]
    df["ilesos"] = df["qtd_gravidade_ileso"]
    
    df["envolve_moto"] = (df["qtd_motocicleta"] > 0).astype(int)
    df["envolve_auto"] = (df["qtd_automovel"] > 0).astype(int)
    df["envolve_pedestre"] = (df["qtd_pedestre"] > 0).astype(int)
    df["envolve_bicicleta"] = (df["qtd_bicicleta"] > 0).astype(int)
    df["envolve_pesado"] = ((df["qtd_caminhao"] > 0) | (df["qtd_onibus"] > 0)).astype(int)
    
    # Severidade
    df["severidade_grave_ou_fatal"] = ((df["obitos"] > 0) | (df["feridos_graves"] > 0)).astype(int)
    df["severidade_categoria"] = classificar_severidade(df)
    
    # Dia da semana padronizado
    mapa_dias = {
        "SEGUNDA-FEIRA": "Segunda-feira", "TERCA-FEIRA": "Terça-feira", "TERÇA-FEIRA": "Terça-feira",
        "QUARTA-FEIRA": "Quarta-feira", "QUINTA-FEIRA": "Quinta-feira", "SEXTA-FEIRA": "Sexta-feira",
        "SABADO": "Sábado", "SÁBADO": "Sábado", "DOMINGO": "Domingo"
    }
    df["dia_da_semana_limpo"] = df["dia_da_semana"].astype(str).str.upper().str.strip().map(
        lambda x: mapa_dias.get(x, x.capitalize())
    )
    df["is_fim_de_semana"] = df["dia_da_semana_limpo"].isin(["Sábado", "Domingo"]).astype(int)
    
    # Vias e Tipos de Sinistro Simplificados
    df["tipo_via_simplificado"] = df.apply(classificar_via, axis=1)
    df["tipo_sinistro_simplificado"] = df["tp_sinistro_primario"].apply(classificar_tipo_sinistro)
    df["turno_ajustado"] = df["hora_num"].apply(classificar_turno)

    # Mesmo formato de data da base gravada em CSV
    df["data_sinistro_dt"] = df["data_sinistro_dt"].dt.strftime("%Y-%m-%d")
    
    return df


# ==============================================================================
# INGESTÃO EM CHUNKS (MEMÓRIA EFICIENTE)
# ==============================================================================
def filtrar_bauru_de_arquivo_csv(caminho_csv):
    """
    Lê um arquivo CSV volumoso do Estado de SP em pedaços (chunks de 50.000 linhas)
    e extrai apenas os sinistros de Bauru.
    """
    print(f"📖 Processando em lotes (chunks): {caminho_csv}")
    
    # UTF-8 é validado primeiro, pois latin1 aceita qualquer sequência de bytes
    for enc in ["utf-8", "latin1"]:
        chunks_bauru = []
        try:
            for chunk in pd.read_csv(caminho_csv, sep=";", encoding=enc, low_memory=False, chunksize=50000):
                # Filtra Bauru por código IBGE ou nome do município
                condicao = (
                    (pd.to_numeric(chunk["cod_ibge"], errors="coerce") == COD_IBGE_BAURU) |
                    (chunk["municipio"].astype(str).str.upper().str.strip() == MUNICIPIO_NOME)
                )
                filtrado = chunk[condicao]
                if len(filtrado) > 0:
                    chunks_bauru.append(filtrado)
            break
        except UnicodeDecodeError:
            continue
            
    if not chunks_bauru:
        print("⚠️ Nenhum registro correspondente a Bauru encontrado neste arquivo.")
        return pd.DataFrame()
        
    df_bauru_bruto = pd.concat(chunks_bauru, ignore_index=True)
    print(f"🎯 Registros de Bauru identificados: {len(df_bauru_bruto):,}")
    return df_bauru_bruto


# ==============================================================================
# INSERÇÃO INCREMENTAL E ATUALIZAÇÃO DOS RELATÓRIOS
# ==============================================================================
def resumir_por_ano(df):
    """Resumo anual, com as notificações à parte porque sua cobertura varia por ano."""
    return df.groupby("ano").agg(
        total_registros=("id_sinistro", "count"),
        notificacoes=("tipo_registro", lambda s: int((s == "NOTIFICACAO").sum())),
        sinistros_fatais=("obitos", lambda s: int((s > 0).sum())),
        obitos=("obitos", "sum"),
        feridos_graves=("feridos_graves", "sum"),
        feridos_leves=("feridos_leves", "sum"),
    ).reset_index()


def mesclar_e_salvar_dados(df_novos_tratados):
    """
    Mescla os novos dados com a base existente 'bauru_limpo.csv', remove
    duplicatas garantindo integridade e atualiza os relatórios sumarizados.
    """
    if df_novos_tratados.empty:
        print("ℹ️ Nenhum dado novo para mesclar.")
        return False
        
    print(f"🔄 Mesclando novos dados com o dataset oficial...")
    
    if os.path.exists(DATA_FILE_BAURU):
        df_atual = pd.read_csv(DATA_FILE_BAURU, sep=";", low_memory=False)
        total_antes = len(df_atual)
        df_consolidado = pd.concat([df_atual, df_novos_tratados], ignore_index=True)
    else:
        total_antes = 0
        df_consolidado = df_novos_tratados
        
    # Deduplicação pelo ID do Sinistro (chave primária do InfoSiga)
    if "id_sinistro" in df_consolidado.columns:
        df_consolidado = df_consolidado.drop_duplicates(subset=["id_sinistro"], keep="last")
        
    # Reclassifica toda a base com a mesma regra dos registros novos
    df_consolidado["severidade_categoria"] = classificar_severidade(df_consolidado)

    # Ordenar por data e id, para que a ordem não dependa da ordem de chegada
    df_consolidado = df_consolidado.sort_values(by=["data_sinistro_dt", "id_sinistro"])
        
    total_depois = len(df_consolidado)
    novos_inseridos = total_depois - total_antes
    
    # Salvar base principal
    df_consolidado.to_csv(DATA_FILE_BAURU, sep=";", index=False, encoding="utf-8")
    print(f"💾 Base atualizada em: {DATA_FILE_BAURU}")
    print(f"📊 Registros anteriores: {total_antes:,} | Novos inseridos: {novos_inseridos:,} | Total agora: {total_depois:,}")
    
    # Atualizar resumo anual
    os.makedirs(RELATORIOS_DIR, exist_ok=True)
    resumir_por_ano(df_consolidado).to_csv(RESUMO_FILE, sep=";", index=False, encoding="utf-8")
    print(f"📈 Resumo anual atualizado em: {RESUMO_FILE}")
    
    return True


# ==============================================================================
# FLUXO DE EXECUÇÃO PRINCIPAL (CLI)
# ==============================================================================
def main():
    parser = argparse.ArgumentParser(
        description="Pipeline Automatizado de Atualização do InfoSiga para Bauru/SP."
    )
    parser.add_argument(
        "--verificar",
        action="store_true",
        help="Apenas verifica se há novos meses disponíveis na API do Governo sem realizar download."
    )
    parser.add_argument(
        "--arquivo",
        type=str,
        help="Processa um arquivo CSV baixado manualmente (ex: data/sinistros_novos.csv)."
    )
    parser.add_argument(
        "--automatico",
        action="store_true",
        help="Baixa e processa automaticamente todos os novos meses disponíveis na API oficial."
    )
    
    args = parser.parse_args()
    
    # Se nenhum argumento for passado, exibe o status de verificação por padrão
    if not args.verificar and not args.arquivo and not args.automatico:
        args.verificar = True
        
    ult_ano_mes = obter_ultimo_ano_mes_cadastrado()
    print(f"📅 Ano/Mês mais recente na base local de Bauru: {ult_ano_mes or 'Nenhum dado cadastrado'}")
    
    # MODO 1: Processar arquivo fornecido manualmente
    if args.arquivo:
        if not os.path.exists(args.arquivo):
            print(f"❌ Arquivo não encontrado: {args.arquivo}")
            sys.exit(1)
        print(f"🚀 Iniciando processamento do arquivo manual: {args.arquivo}")
        df_raw = filtrar_bauru_de_arquivo_csv(args.arquivo)
        if not df_raw.empty:
            df_limpo = aplicar_regras_limpeza_bauru(df_raw)
            mesclar_e_salvar_dados(df_limpo)
        sys.exit(0)
        
    # MODO 2: Consulta à API CKAN Oficial
    recursos = consultar_recursos_ckan()
    if not recursos:
        print("⚠️ Não foi possível listar os recursos da API. Tente novamente mais tarde.")
        sys.exit(1)
        
    # Filtrar recursos pendentes
    pendentes = []
    for r in recursos:
        if str(r.get("format", "")).upper() != "CSV":
            continue
        nome = r.get("name", "")
        url = r.get("url", "")
        ano, mes, rotulo = extrair_ano_mes_recurso(nome, url)
        
        if rotulo and (not ult_ano_mes or mes_na_janela(rotulo, ult_ano_mes)):
            pendentes.append({"nome": nome, "url": url, "rotulo": rotulo})

    meses_novos = [p for p in pendentes if not ult_ano_mes or p["rotulo"] > ult_ano_mes]
            
    print(f"\n📋 Status da Sincronização:")
    print(f"• Meses disponíveis no InfoSiga: {len(recursos)}")
    print(f"• Meses novos pendentes de ingestão: {len(meses_novos)}")
    print(f"• Meses recentes a reprocessar por revisão: {len(pendentes) - len(meses_novos)}")
    
    for p in pendentes:
        print(f"   -> [{p['rotulo']}] {p['nome']}")
        
    if args.verificar:
        if not meses_novos:
            print("\n🎉 O projeto está 100% atualizado com a última publicação do InfoSiga SP!")
        else:
            print("\n💡 Para baixar e processar os meses pendentes acima, execute:")
            print("   python scripts/atualizar_dados_infosiga.py --automatico")
        sys.exit(0)
        
    # MODO 3: Download Automático e Ingestão
    if args.automatico:
        if not pendentes:
            print("⚠️ Nenhum mês encontrado no catálogo para processar.")
            sys.exit(1)
            
        temp_dir = tempfile.mkdtemp(prefix="infosiga_download_")
        print(f"📁 Diretório temporário de download: {temp_dir}")
        
        total_acumulado = []
        try:
            for item in pendentes:
                url = item["url"]
                rotulo = item["rotulo"]
                nome_arq = f"sinistros_{rotulo.replace('/', '_')}.csv"
                destino = os.path.join(temp_dir, nome_arq)
                
                print(f"\n⬇️ Baixando [{rotulo}]: {url[:70]}...")
                # Nada é gravado em caso de falha: o próximo ciclo tenta de novo, sem deixar lacuna
                if not baixar_arquivo(url, destino):
                    print(f"❌ Pipeline interrompido: falha no download de {rotulo}.")
                    sys.exit(1)
                
                df_bruto = filtrar_bauru_de_arquivo_csv(destino)
                if not df_bruto.empty:
                    df_limpo = aplicar_regras_limpeza_bauru(df_bruto)
                    total_acumulado.append(df_limpo)
                    
            if total_acumulado:
                df_novos_todos = pd.concat(total_acumulado, ignore_index=True)
                mesclar_e_salvar_dados(df_novos_todos)
                print("\n✨ Atualização incremental concluída com sucesso!")
            else:
                print("\nℹ️ Foram baixados os arquivos, mas nenhum sinistro novo pertencia a Bauru.")
                
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
            print("🧹 Diretório temporário removido.")


if __name__ == "__main__":
    main()
