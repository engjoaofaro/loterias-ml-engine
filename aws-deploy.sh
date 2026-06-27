#!/bin/bash
# Script para deploy do Motor Preditivo (ML Engine) e criação das dependências na AWS

echo "1. Criando tabela no DynamoDB: LoteriasPredictiveData..."
aws dynamodb create-table \
    --table-name LoteriasPredictiveData \
    --attribute-definitions AttributeName=id,AttributeType=S \
    --key-schema AttributeName=id,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST \
    --region sa-east-1

echo "2. Empacotando a função Lambda..."
zip -r function.zip app.py

echo "3. Criando a função Lambda na AWS (loterias-ml-engine)..."
# Obs: É necessário substituir a Role abaixo por uma ARN válida com acesso ao S3 e DynamoDB.
ROLE_ARN="arn:aws:iam::585482653811:role/loterias-sim-lambda-role"

aws lambda create-function \
    --function-name loterias-ml-engine \
    --runtime python3.9 \
    --role $ROLE_ARN \
    --handler app.lambda_handler \
    --zip-file fileb://function.zip \
    --timeout 30 \
    --memory-size 256 \
    --region sa-east-1

echo "Deploy concluído!"
