import random
import unittest

from stats import (
    GAME_CONFIG,
    frequency,
    hot_cold,
    atraso,
    pares_impares_media,
    soma_media,
    build_suggestions,
)


class TestFrequency(unittest.TestCase):
    def test_conta_dezenas(self):
        f = frequency([[1, 2, 3], [2, 3, 3]])
        self.assertEqual(f[3], 3)
        self.assertEqual(f[2], 2)
        self.assertEqual(f[1], 1)


class TestHotCold(unittest.TestCase):
    def test_quente_e_frio_sobre_o_universo(self):
        draws = [[1, 1, 1] and [1, 2]] * 0  # placeholder
        f = frequency([[1, 2], [1, 2], [1, 3]])
        hot, cold = hot_cold(f, 1, 5, n=2)
        self.assertEqual(hot[0], 1)          # 1 é o mais frequente (3x)
        self.assertIn(4, cold)               # 4 nunca saiu -> frio
        self.assertIn(5, cold)               # 5 nunca saiu -> frio

    def test_inclui_nao_sorteados_como_frios(self):
        f = frequency([[1, 2, 3]])
        hot, cold = hot_cold(f, 1, 10, n=3)
        for n in cold:
            self.assertIn(n, range(1, 11))


class TestAtraso(unittest.TestCase):
    def test_atraso_zero_para_ultimo_concurso(self):
        # draws em ordem crescente de concurso (mais antigo -> mais novo)
        a = atraso([[1, 2], [3, 4], [1, 5]], 1, 6)
        self.assertEqual(a[1], 0)   # 1 saiu no último
        self.assertEqual(a[5], 0)   # 5 saiu no último

    def test_atraso_conta_concursos_desde_a_ultima_aparicao(self):
        a = atraso([[1, 2], [3, 4], [5, 6]], 1, 6)
        self.assertEqual(a[1], 2)   # 1 saiu 2 concursos atrás
        self.assertEqual(a[3], 1)

    def test_nunca_sorteado_tem_atraso_maximo(self):
        a = atraso([[1, 2], [3, 4]], 1, 9)
        self.assertEqual(a[9], 2)   # nunca saiu em 2 concursos


class TestParesImparesSoma(unittest.TestCase):
    def test_pares_impares(self):
        r = pares_impares_media([[1, 2, 3, 4]])
        self.assertEqual(r["pares"], 2)
        self.assertEqual(r["impares"], 2)

    def test_soma_media(self):
        self.assertEqual(soma_media([[1, 2, 3], [4, 5, 6]]), 10.5)


class TestSuggestions(unittest.TestCase):
    def test_gera_jogos_validos_por_modalidade(self):
        rng = random.Random(42)
        for key, cfg in GAME_CONFIG.items():
            f = frequency([[cfg["min"], cfg["max"]]])
            games = build_suggestions(f, cfg, count=5, rng=rng)
            self.assertEqual(len(games), 5)
            for g in games:
                self.assertEqual(len(g), cfg["pick"])
                self.assertEqual(len(set(g)), cfg["pick"])  # sem duplicados
                self.assertEqual(g, sorted(g))              # ordenado
                for n in g:
                    self.assertTrue(cfg["min"] <= n <= cfg["max"])


if __name__ == "__main__":
    unittest.main()
