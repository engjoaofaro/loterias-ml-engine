# Loterias ML Engine

Motor preditivo desenvolvido em Python para execução no AWS Lambda.
Este serviço extrai os dados históricos de jogos do `Amazon S3` (gerados pela aplicação de captura), executa uma análise estatística e salva as combinações otimizadas no `DynamoDB`.

## Como Funciona

1. **Leitura:** Varre o bucket S3 em busca de JSONs com resultados processados (código 200).
2. **Análise de Frequência:** Descobre "Números Quentes" e "Frios".
3. **Simulação:** Monta jogos sugeridos misturando heurísticas para aumentar as probabilidades.
4. **Armazenamento:** Atualiza a tabela `LoteriasPredictiveData` (ID: `LATEST_PREDICTION`).

## Variáveis de Ambiente
- `S3_BUCKET`: Nome do bucket (Padrão: `loterias-resultados`)
- `DYNAMO_TABLE`: Nome da tabela (Padrão: `LoteriasPredictiveData`)
