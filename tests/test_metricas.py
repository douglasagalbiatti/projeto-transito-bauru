"""Testes das regras estatísticas e da limpeza do ETL."""

import os
import shutil
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

from scripts import atualizar_dados_infosiga as etl
from src import metricas
from src import modelo


def _registros(**colunas):
    base = {"obitos": [0], "feridos_graves": [0], "feridos_leves": [0], "ilesos": [0], "qtd_gravidade_nao_disponivel": [0]}
    return pd.DataFrame({**base, **colunas})


class TestMetricas(unittest.TestCase):
    def test_sem_dados_de_vitima_nao_vira_sem_vitimas(self):
        self.assertEqual(metricas.classificar_severidade(_registros())[0], metricas.SEM_INFORMACAO)
        self.assertEqual(metricas.classificar_severidade(_registros(ilesos=[2]))[0], metricas.SEM_FERIDOS)
        self.assertEqual(metricas.classificar_severidade(_registros(obitos=[1], ilesos=[2]))[0], "FATAL")

    def test_gravidade_nao_disponivel_impede_classificar_como_ilesos(self):
        registro = _registros(ilesos=[1], qtd_gravidade_nao_disponivel=[1])
        self.assertEqual(metricas.classificar_severidade(registro)[0], metricas.SEM_INFORMACAO)

    def test_base_comparavel_exclui_anos_antigos_e_notificacoes(self):
        df = pd.DataFrame({
            "ano": [2018, 2019, 2019],
            "tipo_registro": ["SINISTRO FATAL", "NOTIFICACAO", "SINISTRO NAO FATAL"],
        })
        self.assertEqual(metricas.base_comparavel(df).index.tolist(), [2])

    def test_serie_diaria_inclui_dias_sem_registro(self):
        df = pd.DataFrame({"data_sinistro_dt": ["2024-01-01", "2024-01-01", "2024-01-03"]})
        self.assertEqual(metricas.serie_diaria(df).tolist(), [2, 0, 1])

    def test_comparar_dias_usa_o_calendario_completo(self):
        # Segunda 01/01/2024 com 7 registros e domingo 07/01 com 1; demais dias vazios.
        df = pd.DataFrame({"data_sinistro_dt": ["2024-01-01"] * 7 + ["2024-01-07"]})
        resultado = metricas.comparar_dias(df)
        self.assertAlmostEqual(resultado["media_uteis"], 7 / 5)
        self.assertAlmostEqual(resultado["media_fds"], 1 / 2)
        self.assertAlmostEqual(resultado["dias_sem_registro_pct"], 5 / 7 * 100)

    def test_formato_brasileiro(self):
        self.assertEqual(metricas.br(1234.5, 2), "1.234,50")
        self.assertEqual(metricas.br(1360), "1.360")

    def test_formatar_tabela_preserva_numeros_e_codigos(self):
        df = pd.DataFrame({"ano": [2026], "total": [1360], "taxa": [15.22], "hora": [float("nan")], "data": pd.to_datetime(["2026-09-29"])})
        estilo = metricas.formatar_tabela(df, sem_milhar=["ano"])
        html = estilo.to_html()
        for esperado in [">2026<", ">1.360<", ">15,22<", ">29/09/2026<"]:
            self.assertIn(esperado, html)
        self.assertEqual(estilo.data["total"].iloc[0], 1360)

    def test_letalidade_separa_sinistros_e_pessoas(self):
        df = pd.DataFrame({
            "id_sinistro": [1, 2, 3, 4],
            "tipo_sinistro_simplificado": ["CHOQUE"] * 4,
            "obitos": [2, 0, 0, 0],
            "feridos_graves": [0, 1, 1, 0],
        })
        linha = metricas.tabela_letalidade(df).iloc[0]
        self.assertEqual((linha.sinistros_fatais, linha.obitos, linha.letalidade_pct), (1, 2, 25.0))

    def test_ranking_unifica_grafias_com_e_sem_acento(self):
        df = pd.DataFrame({
            "id_sinistro": [1, 2, 3],
            "logradouro": ["AVENIDA NAÇÕES UNIDAS", "AVENIDA NACOES UNIDAS", None],
            "obitos": [1, 0, 0],
            "feridos_graves": [0, 0, 0],
            "feridos_leves": [0, 0, 0],
        })
        ranking = metricas.ranking_vias(df)
        self.assertEqual(ranking["logradouro"].tolist(), ["AVENIDA NACOES UNIDAS"])
        self.assertEqual(ranking["sinistros"].iloc[0], 2)


class TestModelo(unittest.TestCase):
    def test_modelo_ignora_notificacoes_e_anos_antigos(self):
        n = 200
        df = pd.DataFrame({
            "ano": [2020] * n + [2018] * 10 + [2020] * 50,
            "tipo_registro": ["SINISTRO NAO FATAL"] * n + ["SINISTRO FATAL"] * 10 + ["NOTIFICACAO"] * 50,
            "hora_num": [i % 24 for i in range(n + 60)],
            "severidade_grave_ou_fatal": [int(i % 4 == 0) for i in range(n)] + [1] * 10 + [0] * 50,
            "tipo_via_simplificado": ["VIA URBANA", "RODOVIA / ESTRADA"] * ((n + 60) // 2),
            "tipo_sinistro_simplificado": ["COLISAO", "CHOQUE"] * ((n + 60) // 2),
            "turno_ajustado": ["MANHA", "NOITE"] * ((n + 60) // 2),
            **{coluna: [0, 1] * ((n + 60) // 2) for coluna in modelo.FEATURES_NUMERICAS if coluna != "hora_num"},
        })
        resultado = modelo.treinar_modelo(df)
        self.assertEqual(resultado["n_treino"] + resultado["n_teste"], n)
        self.assertAlmostEqual(resultado["prevalencia"], 0.25)
        self.assertTrue(resultado["temporal"].empty)
        self.assertEqual(int(resultado["validacao_cruzada"]["rodadas"].iloc[0]), modelo.DOBRAS_CV * modelo.REPETICOES_CV)
        self.assertLessEqual(resultado["auc_ic"][0], resultado["auc"])
        self.assertGreaterEqual(resultado["auc_ic"][1], resultado["auc"])
        caso = df.head(1).copy()
        caso["turno_ajustado"] = "MADRUGADA"  # categoria que o modelo não viu
        prob = modelo.prever_probabilidade(resultado, caso)
        self.assertTrue(0 <= prob[0] <= 1)

    def test_validacao_temporal_treina_so_com_anos_anteriores(self):
        anos = list(range(2019, 2025))
        n_ano = 80
        n = n_ano * len(anos)
        base = pd.DataFrame({
            "ano": [a for a in anos for _ in range(n_ano)],
            "severidade_grave_ou_fatal": [int(i % 5 == 0) for i in range(n)],
        })
        X = pd.DataFrame({"x": [i % 7 for i in range(n)]})
        temporal = modelo.validacao_temporal(base, X, base["severidade_grave_ou_fatal"])
        self.assertEqual(temporal["ano"].tolist(), anos[modelo.ANOS_MINIMOS_TREINO:])
        self.assertEqual(temporal["anos_treino"].iloc[0], "2019–2021")
        self.assertTrue((temporal["n_teste"] == n_ano).all())

    def test_razao_de_chance_bate_com_a_tabela_2x2(self):
        # Exposto: 30 graves e 70 não graves; não exposto: 10 graves e 90 não graves
        x = [1] * 100 + [0] * 100
        y = [1] * 30 + [0] * 70 + [1] * 10 + [0] * 90
        X = pd.DataFrame({"exposto": x}, dtype=float)
        clf = modelo.novo_classificador().fit(X, y)
        rc = modelo.razoes_de_chance(clf, X).loc["exposto"]
        esperado = (30 * 90) / (70 * 10)
        erro_padrao = np.sqrt(1 / 30 + 1 / 70 + 1 / 10 + 1 / 90)
        self.assertAlmostEqual(rc["razao_chance"], esperado, places=3)
        self.assertAlmostEqual(rc["ic_inf"], esperado * np.exp(-1.96 * erro_padrao), places=3)
        self.assertAlmostEqual(rc["ic_sup"], esperado * np.exp(1.96 * erro_padrao), places=3)
        self.assertEqual(rc["n_casos"], 100)

    def test_referencia_ausente_usa_a_categoria_mais_comum(self):
        df = pd.DataFrame({
            "tipo_via_simplificado": ["VIA URBANA", "RODOVIA / ESTRADA", "VIA URBANA"],
            "tipo_sinistro_simplificado": ["CHOQUE", "CHOQUE", "ATROPELAMENTO"],
            "turno_ajustado": ["NOITE", "MANHA", "NOITE"],
        })
        refs = modelo.referencias(df)
        self.assertEqual(refs["tipo_via_simplificado"], "VIA URBANA")
        self.assertEqual(refs["tipo_sinistro_simplificado"], "CHOQUE")
        self.assertEqual(refs["turno_ajustado"], "NOITE")

    def test_metricas_classe_rara_usam_limiar_da_prevalencia(self):
        m = modelo.metricas_classe_rara([0, 0, 0, 1], [0.1, 0.2, 0.3, 0.4], prevalencia_treino=0.25)
        self.assertAlmostEqual(m["sensibilidade"], 1.0)
        self.assertAlmostEqual(m["precisao"], 1 / 2)
        self.assertAlmostEqual(m["auc"], 1.0)
        self.assertAlmostEqual(m["brier_ref"], 0.1875)


def _bruto(**extras):
    linha = {coluna: [1] for coluna in etl.COLUNAS_OBRIGATORIAS}
    linha.update({
        "cod_ibge": [etl.COD_IBGE_BAURU], "municipio": ["BAURU"], "data_sinistro": ["05/01/2026"], "hora_sinistro": ["17:30"],
        "ano_mes_sinistro": ["2026/01"], "ano_sinistro": [2026], "mes_sinistro": [1], "dia_da_semana": ["Segunda-feira"],
        "latitude": ["-22,3"], "longitude": ["-49,0"], "tipo_via": ["VIAS URBANAS"], "administracao": ["PREFEITURA"],
        "tp_sinistro_primario": ["COLISAO"], "tipo_registro": ["SINISTRO NAO FATAL"], "logradouro": ["RUA A"],
    })
    linha.update(extras)
    return pd.DataFrame(linha)


class TestEtl(unittest.TestCase):
    def setUp(self):
        self.pasta = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.pasta)

    def test_coluna_ausente_interrompe_em_vez_de_zerar(self):
        with self.assertRaises(ValueError):
            etl.aplicar_regras_limpeza_bauru(_bruto().drop(columns="qtd_gravidade_fatal"))

    def test_hora_invalida_vira_ausente(self):
        self.assertEqual(etl.parse_hora("14:30"), 14)
        self.assertEqual(etl.parse_hora("7"), 7)
        self.assertTrue(pd.isna(etl.parse_hora("25:00")))
        self.assertTrue(pd.isna(etl.parse_hora("sem hora")))

    def test_cod_ibge_texto_ou_decimal_e_aceito(self):
        caminho = os.path.join(self.pasta, "bruto.csv")
        _bruto(cod_ibge=["3506003.0"], municipio=["OUTRO"]).to_csv(caminho, sep=";", index=False)
        self.assertEqual(len(etl.filtrar_bauru_de_arquivo_csv(caminho)), 1)

    def test_utf8_nao_e_lido_como_latin1(self):
        caminho = os.path.join(self.pasta, "bruto.csv")
        _bruto(dia_da_semana=["Terça-feira"]).to_csv(caminho, sep=";", index=False, encoding="utf-8")
        self.assertEqual(etl.filtrar_bauru_de_arquivo_csv(caminho)["dia_da_semana"].iloc[0], "Terça-feira")

    def test_latin1_recomeca_sem_duplicar_registros(self):
        caminho = os.path.join(self.pasta, "bruto.csv")
        _bruto(dia_da_semana=["Terça-feira"]).to_csv(caminho, sep=";", index=False, encoding="latin1")
        resultado = etl.filtrar_bauru_de_arquivo_csv(caminho)
        self.assertEqual(len(resultado), 1)
        self.assertEqual(resultado["dia_da_semana"].iloc[0], "Terça-feira")

    def test_periodo_usa_nome_quando_url_nao_tem_data(self):
        self.assertEqual(etl.extrair_ano_mes_recurso("Agosto de 2026", "https://x/arquivo.csv")[:2], (2026, 8))

    def test_janela_de_revisao_reprocessa_meses_recentes(self):
        self.assertTrue(etl.mes_na_janela("2026/07", "2026/09"))
        self.assertTrue(etl.mes_na_janela("2025/12", "2026/02"))
        self.assertFalse(etl.mes_na_janela("2026/06", "2026/09"))

    def _mesclar(self, df_atual, df_novo):
        caminho = os.path.join(self.pasta, "base.csv")
        df_atual.to_csv(caminho, sep=";", index=False)
        with patch.object(etl, "DATA_FILE_BAURU", caminho), \
                patch.object(etl, "RELATORIOS_DIR", self.pasta), \
                patch.object(etl, "RESUMO_FILE", os.path.join(self.pasta, "resumo.csv")):
            etl.mesclar_e_salvar_dados(df_novo)
        return pd.read_csv(caminho, sep=";")

    def test_mesclagem_aceita_base_gravada_e_registros_novos(self):
        # A data lida do CSV é texto; misturá-la a datetime derrubou o pipeline em 31/10/2026.
        atual = etl.aplicar_regras_limpeza_bauru(_bruto(id_sinistro=[1], data_sinistro=["10/01/2026"]))
        novo = etl.aplicar_regras_limpeza_bauru(_bruto(id_sinistro=[2], data_sinistro=["05/01/2026"]))
        resultado = self._mesclar(atual, novo)
        self.assertEqual(resultado["id_sinistro"].tolist(), [2, 1])
        self.assertEqual(resultado["data_sinistro_dt"].tolist(), ["2026-01-05", "2026-01-10"])

    def test_mesclagem_mantem_a_versao_revisada_e_reclassifica(self):
        atual = etl.aplicar_regras_limpeza_bauru(_bruto(id_sinistro=[1], qtd_gravidade_fatal=[0], qtd_gravidade_grave=[0], qtd_gravidade_leve=[1]))
        atual["severidade_categoria"] = "ILESO / NAO INFORMADO"
        antigo = atual.assign(id_sinistro=3, feridos_leves=0, feridos_graves=0, ilesos=0, qtd_gravidade_nao_disponivel=0)
        revisado = etl.aplicar_regras_limpeza_bauru(_bruto(id_sinistro=[1], qtd_gravidade_fatal=[1]))
        resultado = self._mesclar(pd.concat([atual, antigo]), revisado).set_index("id_sinistro")
        self.assertEqual(resultado.loc[1, "severidade_categoria"], "FATAL")
        self.assertEqual(resultado.loc[3, "severidade_categoria"], metricas.SEM_INFORMACAO)

    def test_falha_de_download_nao_altera_a_base(self):
        recursos = [{"format": "CSV", "url": "https://x/sinistros_09-2026.csv", "name": ""}]
        with patch.object(etl, "consultar_recursos_ckan", return_value=recursos), \
                patch.object(etl, "obter_ultimo_ano_mes_cadastrado", return_value="2026/08"), \
                patch.object(etl, "baixar_arquivo", return_value=False), \
                patch.object(etl, "mesclar_e_salvar_dados") as mesclar, \
                patch("sys.argv", ["etl", "--automatico"]):
            with self.assertRaises(SystemExit) as saida:
                etl.main()
        self.assertEqual(saida.exception.code, 1)
        mesclar.assert_not_called()


if __name__ == "__main__":
    unittest.main()
