"""Testes dos indicadores e do README gerado a partir deles."""

import os
import re
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import URLError

import nbformat
import pandas as pd
from streamlit.testing.v1 import AppTest

from scripts import gerar_artefatos
from src.indicadores import (
    calcular_indicadores,
    frase_atropelamento_gestao,
    frase_choque_urbano,
    frase_notificacoes_veiculos,
)
from src.metricas import br, ler_artefato, ranking_vias
from src.modelo import treinar_modelo

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def _base():
    return pd.read_csv(os.path.join(RAIZ, "data", "bauru_limpo.csv"), sep=";", encoding="utf-8", low_memory=False)


def _com_novo_mes(df):
    novos = df[df["ano"] == df["ano"].max()].tail(30).copy()
    novos["id_sinistro"] = [f"novo-{n}" for n in range(len(novos))]
    novos["data_sinistro_dt"] = "2031-01-15"
    novos["ano"] = 2031
    return pd.concat([df, novos], ignore_index=True)


class TestArtefatos(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.df = _base()
        cls.resultado = treinar_modelo(cls.df)
        cls.indicadores = calcular_indicadores(cls.df, cls.resultado)

    def _readme(self, indicadores):
        with tempfile.TemporaryDirectory() as pasta:
            return gerar_artefatos.gerar_readme(indicadores, destino=os.path.join(pasta, "README.md"))

    def test_numeros_do_readme_vem_da_base(self):
        readme = self._readme(self.indicadores)
        self.assertIn(f"{br(len(self.df))} registros", readme)
        self.assertIn(f"{br(self.df['obitos'].sum())} óbitos", readme)
        self.assertIn(f"{br(self.df['feridos_graves'].sum())} feridos graves", readme)
        fim = pd.to_datetime(self.df["data_sinistro_dt"]).max()
        self.assertIn(f"a {fim:%d/%m/%Y}.", readme)

    def test_novo_mes_muda_o_readme(self):
        novo = calcular_indicadores(_com_novo_mes(self.df), self.resultado)
        readme = self._readme(novo)
        self.assertEqual(novo["total"], len(self.df) + 30)
        self.assertIn(f"{br(novo['total'])} registros", readme)
        self.assertNotIn(f"{br(len(self.df))} registros", readme)
        self.assertIn("a 15/01/2031.", readme)

    def test_readme_nao_deixa_marcadores_do_modelo(self):
        readme = self._readme(self.indicadores)
        self.assertNotIn("{{", readme)
        self.assertNotIn("{%", readme)

    def test_conclusoes_acompanham_os_dados(self):
        i = self.indicadores
        casos = [
            ("supera_referencia", "supera a de sempre prever", "é praticamente a de sempre prever"),
            ("rodovia_mais_letal", "é maior nas rodovias", "nas rodovias e"),
        ]
        for chave, verdadeiro, falso in casos:
            self.assertIn(verdadeiro, self._readme({**i, chave: True}), chave)
            self.assertIn(falso, self._readme({**i, chave: False}), chave)
        teste = i["teste"]
        self.assertIn("estatisticamente significativa", self._readme({**i, "teste": {**teste, "significativo": True}}))
        self.assertIn("não prova igualdade", self._readme({**i, "teste": {**teste, "significativo": False}}))

    def test_frase_do_choque_so_afirma_diferenca_urbana_com_respaldo(self):
        i = self.indicadores
        self.assertEqual("mas essa diferença é urbana" in i["frase_choque"], i["choque_so_urbano"])
        self.assertEqual("é urbana" in i["frase_choque_resumo"], i["choque_so_urbano"])

    def test_painel_sem_arquivo_local_nem_rede_nao_quebra(self):
        with patch("src.metricas.urlopen", side_effect=URLError("sem rede")):
            self.assertIsNone(ler_artefato("nao_existe.png"))

    def test_saidas_plotly_saem_do_notebook_executado(self):
        notebook = nbformat.v4.new_notebook(cells=[nbformat.v4.new_code_cell("x")])
        notebook.cells[0].outputs = [
            nbformat.v4.new_output("display_data", data={gerar_artefatos.SAIDA_PLOTLY: {}}),
            nbformat.v4.new_output("display_data", data={"image/png": "abc"}),
            nbformat.v4.new_output("stream", text="ok"),
        ]
        saidas = gerar_artefatos.remover_saidas_plotly(notebook).cells[0].outputs
        self.assertEqual(len(saidas), 2)
        self.assertNotIn(gerar_artefatos.SAIDA_PLOTLY, saidas[0]["data"])

    def test_notebooks_executados_sao_publicados_e_citados_no_readme(self):
        with open(os.path.join(RAIZ, "scripts", "publicar_artefatos.sh"), encoding="utf-8") as arquivo:
            self.assertIn("output/notebooks", arquivo.read())
        readme = self._readme(self.indicadores)
        for nome in gerar_artefatos.NOTEBOOKS:
            self.assertIn(f"blob/artefatos/output/notebooks/{nome}", readme)

    def test_ranking_de_vias_desempata_sempre_igual(self):
        df = pd.DataFrame({
            "id_sinistro": range(7),
            "logradouro": ["RUA B", "RUA A", "RUA C", "RUA C", "RUA D", "RUA D", "RUA D"],
            "obitos": [5, 5, 3, 2, 1, 2, 2],
            "feridos_graves": [0] * 7,
            "feridos_leves": [0] * 7,
        })
        for ordem in (df, df.iloc[::-1]):
            por_obitos = ranking_vias(ordem, por="obitos")["logradouro"].tolist()
            self.assertEqual(por_obitos, ["RUA D", "RUA C", "RUA A", "RUA B"])
            por_sinistros = ranking_vias(ordem, por="sinistros")["logradouro"].tolist()
            self.assertEqual(por_sinistros, ["RUA D", "RUA C", "RUA A", "RUA B"])

    def test_frases_do_painel_acompanham_os_dados(self):
        self.assertIn("a maior letalidade", frase_atropelamento_gestao(True, 11.6))
        self.assertNotIn("a maior letalidade", frase_atropelamento_gestao(False, 11.6))
        self.assertIn("5,9 vezes", frase_choque_urbano((5.9, 4.1, 8.7)))
        self.assertIn("não demonstram", frase_choque_urbano((1.2, 0.7, 2.0)))
        self.assertIn("nunca", frase_notificacoes_veiculos(True))
        self.assertIn("raramente", frase_notificacoes_veiculos(False))

    def test_painel_abre_com_as_frases_calculadas(self):
        painel = AppTest.from_file(os.path.join(RAIZ, "app.py"), default_timeout=120).run()
        self.assertFalse(painel.exception)
        textos = " ".join(bloco.value for bloco in painel.markdown)
        self.assertIn(self.indicadores["via_motos_urbana"], textos)
        self.assertIn(self.indicadores["frase_choque_urbano"], textos)

    def test_workflow_publica_antes_do_commit_e_nao_versiona_graficos(self):
        with open(os.path.join(RAIZ, ".github", "workflows", "atualizar_infosiga.yml"), encoding="utf-8") as arquivo:
            workflow = arquivo.read()
        self.assertLess(workflow.index("gerar_artefatos.py"), workflow.index("publicar_artefatos.sh"))
        self.assertLess(workflow.index("publicar_artefatos.sh"), workflow.index("git push origin main"))
        self.assertIn("requirements-artefatos.txt", workflow)
        self.assertIsNone(re.search(r"git add .*output/(graficos|notebooks)", workflow))


if __name__ == "__main__":
    unittest.main()
