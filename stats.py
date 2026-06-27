"""Estatística pura sobre o histórico de sorteios (sem dependências de AWS).

IMPORTANTE: loteria é evento independente — estas estatísticas são informativas
e NÃO aumentam as chances reais de premiação.
"""
import random
from collections import Counter

# Configuração por modalidade (chaves usadas no front/DynamoDB).
GAME_CONFIG = {
    "mega-sena": {"min": 1, "max": 60, "pick": 6},
    "lotofacil": {"min": 1, "max": 25, "pick": 15},
    "lotomania": {"min": 0, "max": 99, "pick": 50},
}


def frequency(draws):
    """Counter da frequência de cada dezena. draws = lista de listas de int."""
    c = Counter()
    for d in draws:
        c.update(d)
    return c


def hot_cold(freq, universe_min, universe_max, n=10):
    """Top-n dezenas mais quentes e mais frias considerando todo o universo
    (números nunca sorteados contam como frios)."""
    counts = [(num, freq.get(num, 0)) for num in range(universe_min, universe_max + 1)]
    ordered = sorted(counts, key=lambda kv: kv[1])
    cold = [num for num, _ in ordered[:n]]
    hot = [num for num, _ in ordered[::-1][:n]]
    return hot, cold


def atraso(draws_ordered, universe_min, universe_max):
    """Atraso de cada dezena = nº de concursos desde a última aparição.
    draws_ordered em ordem crescente de concurso (mais antigo -> mais novo).
    0 = saiu no concurso mais recente; total = nunca saiu."""
    last_index = {}
    for i, d in enumerate(draws_ordered):
        for num in d:
            last_index[num] = i
    total = len(draws_ordered)
    result = {}
    for num in range(universe_min, universe_max + 1):
        result[num] = (total - 1 - last_index[num]) if num in last_index else total
    return result


def pares_impares_media(draws):
    if not draws:
        return {"pares": 0, "impares": 0}
    pares = sum(sum(1 for x in d if x % 2 == 0) for d in draws) / len(draws)
    impares = sum(sum(1 for x in d if x % 2 == 1) for d in draws) / len(draws)
    return {"pares": round(pares, 1), "impares": round(impares, 1)}


def soma_media(draws):
    if not draws:
        return 0
    return round(sum(sum(d) for d in draws) / len(draws), 1)


def _weighted_sample(population, weights, k, rng):
    """Amostragem sem reposição ponderada pela frequência (suavizada)."""
    pop, w, chosen = list(population), list(weights), []
    for _ in range(k):
        total = sum(w)
        r = rng.uniform(0, total)
        upto = 0
        for i, wi in enumerate(w):
            upto += wi
            if upto >= r:
                chosen.append(pop.pop(i))
                w.pop(i)
                break
    return chosen


def build_suggestions(freq, config, count=5, rng=None):
    """Gera `count` jogos por modalidade, amostrando dezenas com peso na
    frequência histórica (suavizada com +1 para dar chance a todas)."""
    rng = rng or random.Random()
    universe = list(range(config["min"], config["max"] + 1))
    weights = [freq.get(n, 0) + 1 for n in universe]
    return [sorted(_weighted_sample(universe, weights, config["pick"], rng)) for _ in range(count)]
