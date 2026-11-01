"""Reconstrói data/bauru_limpo.csv a partir dos arquivos brutos e regenera os artefatos."""

import glob
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import atualizar_dados_infosiga as etl
import gerar_artefatos


def main():
    arquivos = sorted(glob.glob(os.path.join(etl.DATA_DIR, "sinistros_*.csv")))
    if not arquivos:
        # Sem arquivos brutos, a base atual é mantida
        print("Nenhum arquivo data/sinistros_*.csv encontrado. Baixe-os do Infosiga SP antes de reconstruir a base.")
        return 1

    brutos = [etl.filtrar_bauru_de_arquivo_csv(arquivo) for arquivo in arquivos]
    df = etl.aplicar_regras_limpeza_bauru(pd.concat(brutos, ignore_index=True))
    df = df.drop_duplicates(subset=["id_sinistro"], keep="last").sort_values(by=["data_sinistro_dt", "id_sinistro"])
    df.to_csv(etl.DATA_FILE_BAURU, sep=";", index=False, encoding="utf-8")
    os.makedirs(etl.RELATORIOS_DIR, exist_ok=True)
    etl.resumir_por_ano(df).to_csv(etl.RESUMO_FILE, sep=";", index=False, encoding="utf-8")
    print(f"Base reconstruída com {len(df)} registros.")

    gerar_artefatos.main()
    return 0


if __name__ == "__main__":
    sys.exit(main())
