"""ml-engine: análise estatística do histórico de sorteios.

Lê o histórico do S3 (results/{concurso}_{loteria}.json), calcula estatísticas por
modalidade (frequência, quente/frio, atraso, pares/ímpares, soma), gera sugestões de
jogos e grava no DynamoDB (item LATEST_PREDICTION) junto com os últimos resultados.

Disclaimer: loteria é evento independente — as sugestões são informativas e não
aumentam as chances reais de premiação.
"""
import json
import os
import re
import logging
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal

import boto3

from stats import (
    GAME_CONFIG, frequency, hot_cold, atraso, pares_impares_media, soma_media, build_suggestions,
)

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")

BUCKET = os.getenv("S3_BUCKET", "loterias-resultados")
TABLE = os.getenv("DYNAMO_TABLE", "LoteriasPredictiveData")
PREFIX = os.getenv("S3_PREFIX", "results/")

FILENAME_RE = re.compile(r"(\d+)_(megasena|lotofacil|lotomania)\.json$")
APINAME_TO_KEY = {"megasena": "mega-sena", "lotofacil": "lotofacil", "lotomania": "lotomania"}


def _load_history():
    """Retorna {apiname: [(concurso:int, dezenas:[int]), ...]} lido do S3."""
    per = defaultdict(list)
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=BUCKET, Prefix=PREFIX):
        for obj in page.get("Contents", []):
            m = FILENAME_RE.search(obj["Key"])
            if not m:
                continue
            concurso, loteria = int(m.group(1)), m.group(2)
            try:
                body = s3.get_object(Bucket=BUCKET, Key=obj["Key"])["Body"].read()
                dezenas = [int(x) for x in json.loads(body)["dezenas"]]
            except Exception as e:  # noqa: BLE001
                logger.warning("Ignorando %s: %s", obj["Key"], e)
                continue
            per[loteria].append((concurso, dezenas))
    return per


def lambda_handler(event, context):
    history = _load_history()
    suggestions, stats, latest = {}, {}, {}

    for loteria, entries in history.items():
        key = APINAME_TO_KEY[loteria]
        cfg = GAME_CONFIG[key]
        entries.sort(key=lambda e: e[0])  # por concurso (asc)
        draws = [dezenas for _, dezenas in entries]

        freq = frequency(draws)
        hot, cold = hot_cold(freq, cfg["min"], cfg["max"])
        atr = atraso(draws, cfg["min"], cfg["max"])
        top_atraso = sorted(atr.items(), key=lambda kv: kv[1], reverse=True)[:10]

        suggestions[key] = build_suggestions(freq, cfg, count=5)
        stats[key] = {
            "hot_numbers": hot,
            "cold_numbers": cold,
            "atraso": [{"dezena": n, "concursos": d} for n, d in top_atraso],
            "pares_impares": pares_impares_media(draws),
            "soma_media": soma_media(draws),
            "total_concursos": len(draws),
        }
        last_concurso, last_dezenas = entries[-1]
        latest[key] = {"concurso": last_concurso, "dezenas": sorted(last_dezenas)}
        logger.info("%s: %d concursos analisados", key, len(draws))

    if not suggestions:
        logger.warning("Nenhum histórico encontrado em s3://%s/%s", BUCKET, PREFIX)
        return {"statusCode": 200, "body": "Sem dados históricos."}

    item = {
        "id": "LATEST_PREDICTION",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "suggestions": suggestions,
        "stats": stats,
        "latest_results": latest,
    }
    # DynamoDB não aceita float -> converte para Decimal
    item = json.loads(json.dumps(item), parse_float=Decimal)
    dynamodb.Table(TABLE).put_item(Item=item)

    logger.info("Predição salva: %s", {k: len(v) for k, v in suggestions.items()})
    return {"statusCode": 200, "body": json.dumps("Análise concluída.")}
