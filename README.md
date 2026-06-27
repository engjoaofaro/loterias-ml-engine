# loterias-ml-engine

Motor de **análise estatística de frequência** das loterias brasileiras, em
**Python / AWS Lambda**. Lê o histórico de resultados gravado no S3 pelo
`loterias-capture-results`, calcula números "quentes" e "frios" e grava jogos
sugeridos no DynamoDB, que são servidos ao frontend via `loterias-sim-api`
(`GET /sugestoes`).

> Parte do ecossistema **Loterias Sim**. Visão geral em [Arquitetura](#arquitetura-e-fluxo).

> ⚠️ **Aviso importante (honestidade estatística):** apesar do nome "ML Engine",
> **não há machine learning** aqui — é contagem de frequência. E, do ponto de vista
> matemático, números mais ou menos sorteados no passado **não aumentam nem diminuem**
> a chance de sair no próximo sorteio: cada sorteio é um evento independente
> (falácia do apostador). As sugestões servem para entretenimento/UX, não como
> vantagem estatística real. Recomenda-se exibir esse disclaimer ao usuário final.

---

## Visão geral

| Item | Valor |
|------|-------|
| Runtime | Python **3.9** |
| Handler | `app.lambda_handler` |
| Função Lambda | `loterias-ml-engine` |
| Entrada | Objetos JSON do bucket S3 `loterias-resultados` |
| Saída | Item `LATEST_PREDICTION` na tabela DynamoDB `LoteriasPredictiveData` |
| Região | `sa-east-1` |
| Memória / Timeout | 256 MB / 30 s |

---

## Como funciona (`app.py`)

1. **Leitura (S3):** `list_objects_v2` no bucket (até **500** objetos) e
   `get_object` em cada um.
2. **Extração:** para cada arquivo, lê `Payload` (com suporte a `Payload` aninhado de
   Step Functions); se `code == 200`, agrega o array `Dezenas Sorteadas`.
   - Se nenhum dado válido for encontrado, usa **fallback** de 1000 números aleatórios
     `01..60` (apenas demonstração).
3. **Análise de frequência** (`collections.Counter`):
   - `most_common(15)` → 15 números **quentes**
   - `most_common()[-10:]` → 10 números **frios**
4. **Geração de jogos (Mega-Sena):** 5 jogos, cada um com **4 quentes + 2 frios**
   (`random.sample`), ordenados.
5. **Gravação (DynamoDB):** `put_item` em `id = "LATEST_PREDICTION"` com `suggestions`
   e `stats` (`hot_numbers`, `cold_numbers`).

### Formato esperado do arquivo no S3
```json
{ "Payload": { "code": 200, "Dezenas Sorteadas": ["01","15","23","45","50","59"] } }
```

### Item gravado no DynamoDB
```json
{
  "id": "LATEST_PREDICTION",
  "timestamp": "CURRENT_TIMESTAMP",
  "suggestions": { "mega-sena": [[...]], "lotofacil": [], "lotomania": [] },
  "stats": { "hot_numbers": [...], "cold_numbers": [...] }
}
```

---

## Variáveis de ambiente

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `S3_BUCKET` | `loterias-resultados` | Bucket com o histórico de resultados |
| `DYNAMO_TABLE` | `LoteriasPredictiveData` | Tabela de saída das sugestões |

---

## Recursos AWS e permissões (IAM)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    { "Effect": "Allow", "Action": ["s3:GetObject","s3:ListBucket"],
      "Resource": ["arn:aws:s3:::loterias-resultados","arn:aws:s3:::loterias-resultados/*"] },
    { "Effect": "Allow", "Action": ["dynamodb:PutItem"],
      "Resource": "arn:aws:dynamodb:sa-east-1:585482653811:table/LoteriasPredictiveData" }
  ]
}
```

---

## Deploy

`aws-deploy.sh` cria a tabela (se necessário), empacota e cria a função:

```bash
aws dynamodb create-table --table-name LoteriasPredictiveData \
  --attribute-definitions AttributeName=id,AttributeType=S \
  --key-schema AttributeName=id,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST --region sa-east-1

zip -r function.zip app.py
aws lambda create-function --function-name loterias-ml-engine \
  --runtime python3.9 --role arn:aws:iam::585482653811:role/loterias-sim-lambda-role \
  --handler app.lambda_handler --zip-file fileb://function.zip \
  --timeout 30 --memory-size 256 --region sa-east-1
```

> ⚠️ O zip só inclui `app.py`. As deps do `requirements.txt` (`boto3`, `pandas`,
> `scikit-learn`) **não** são empacotadas. Hoje o código só usa `boto3` (disponível no
> runtime Lambda), então funciona — mas `pandas`/`scikit-learn` estão no
> `requirements.txt` sem uso. Limpe o arquivo ou empacote via Lambda Layer caso passe
> a usá-las.

---

## Arquitetura e fluxo

```
loterias-capture-results ─► S3 (loterias-resultados) ─► loterias-ml-engine ─► DynamoDB (LoteriasPredictiveData)
                                                                                      │
                                                                 GET /sugestoes ◄── loterias-sim-api ◄── Web
```

Disparo: idealmente por agendamento (EventBridge) após a captura de resultados. Hoje
não há gatilho versionado neste repositório.

---

## Pontos de atenção e melhorias

- 🐞 **Bug de timestamp:** grava a string literal `'CURRENT_TIMESTAMP'`. Trocar por
  `datetime.now(timezone.utc).isoformat()`.
- 🚧 **Só Mega-Sena implementada:** `lotofacil` e `lotomania` ficam como listas vazias.
- ⚠️ **Fallback com faixa errada:** gera `01..60` (válido só para Mega-Sena);
  Lotofácil é `01..25` e Lotomania `00..99`.
- ⚠️ **Sem histórico:** sempre sobrescreve `LATEST_PREDICTION`. Para análises
  temporais, usar chave composta (ex.: `id = "mega-sena#2026-06-27"`).
- ⚠️ **Limite de 500 objetos** por execução (`MaxKeys=500`) — com mais arquivos, parte
  do histórico é ignorada. Usar paginação (`get_paginator`).
- 🔇 **Falhas silenciosas:** arquivos inválidos são ignorados sem log. Adotar logging
  estruturado.
- Limpar dependências não usadas; remover/condicionar o fallback aleatório em produção.
- Renomear/reposicionar como "engine estatística" e exibir disclaimer de jogo
  responsável.
