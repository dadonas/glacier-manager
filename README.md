O Glacier Manager foi criado para facilitar a gestão de arquivos no serviço Glacier da AWS.

# O Funcionamento do Glacier
No Glacier os arquivos ficam dentro de vaults. Através do console da AWS é possível visualizar somente esses vaults mas não os arquivos que estão dentro deles. \
Para recuperar a lista de arquivos (*inventory*), é necessário iniciar um *job*. Para baixar arquivos também é necessário iniciar um *job*. \
Existem dois tipos de operação de *job*:
- `inventory-retrieval`: para recuperação de lista de arquivos, ou seja, o inventário.
- `archive-retrieval`: para recuperação de arquivos.
\
Existem também os tipos de recuperação (*tier*) dessas informações:
- `Expedited`: recuperação entre 1-5 minutos. *Tier* mais caro.
- `Standard`: recuperação entre 1-3 horas. *Tier* de valor mediano.
- `Bulk`: recuperação entre 5-12 horas. *Tier* mais barato.

# Executando a Aplicação
## Instalar Python
- Instalar a última versão.
- O Python pode ser instalado diretamente no sistema operacional ou pode ser utilizado um gerenciador de versões como o `pyenv`.

## Instalar poetry
[Necessário somente no Windows]
- Habilitar execução de script no power shell: `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`

- Instalar as dependências: 
```
poetry install
poetry add 'fastapi[standard]'
```

## Executar a aplicação

```
# Iniciar o MongoDB
docker-compose up -d

# Iniciar Ambiente Virtual
poetry shell

# Iniciar Servidor Web
fastapi dev app.py
```

## Acessando as Informações do Mongo
`http://localhost:8081`

# Utilizando a Aplicação
## Configurar as Credenciais de Acesso a AWS
```
curl --location 'http://localhost:8000/configs' \
--header 'Content-Type: application/json' \
--data '{
    "account": "xxxxxxxxx",
    "key": "xxxxxxxxx",
    "secret": "xxxxxxxxxx",
    "region": "xxxxx",
    "sns_topic_arn": "xxxxxxxxxxxx"
}'
``` 
**account** - Código da conta AWS. \
**key e secret** - Chave de acesso criada no IAM da AWS com a permissão `AmazonGlacierFullAccess`. \
**region** - Região onde estão os vaults do Glacier. \
**sns_topic_arn** - ARN do tópico responsável por notificar quando os archives ou inventories estivem disponíveis. Essa configuração é opcional, porém, altamente recomendada. Quando é iniciado um job para recuperação do inventário ou para download de um archive, o job expira em 24 horas. Por isso é importante ser notificado.

## Listando Vaults
```
curl --location 'http://localhost:8000/vaults'
```

## ...