# Publicar o CLI no PyPI

O nome da distribuição e do executável é `igarape`. O workflow de publicação pertence
ao repositório do CLI. Os serviços gerados têm seu próprio ciclo de release.

## Configuração inicial

Na conta PyPI que ficará responsável pelo projeto, abra [Publishing](https://pypi.org/manage/account/publishing/)
e adicione um **pending publisher** do GitHub para a primeira publicação.

| Campo | Valor |
|---|---|
| PyPI project name | `igarape` |
| Owner | `spassos` |
| Repository name | `igarape` |
| Workflow name | `publish-pypi.yml` |
| Environment name | `pypi` |

Para um projeto já criado, cadastre o publisher nas configurações do próprio projeto. O PyPI
verifica a identidade do job do GitHub Actions por OpenID Connect. As credenciais da conta
permanecem no PyPI.

## Publicar e conferir

1. Confira a versão em `pyproject.toml`, o lockfile e o CI da revisão em `main`. Cada
   distribuição publicada precisa de uma versão inédita.
2. Em [Publish CLI to PyPI](https://github.com/spassos/igarape/actions/workflows/publish-pypi.yml),
   escolha **Run workflow** na branch `main`. O primeiro job monta o sdist e o wheel,
   instala o wheel e testa o projeto gerado. O segundo publica esses mesmos artefatos.
3. Após a conclusão, confira o número da versão, o repositório de origem e os arquivos na
   [página do pacote](https://pypi.org/project/igarape/). Em uma pasta vazia,
   execute `uvx --refresh igarape new orders-api` e valide a aplicação gerada.
4. Quando essa instalação pelo índice público estiver verificada, divulgue o comando
   `uvx igarape new orders-api`. Para instalação persistente, use `uv tool install igarape`.
