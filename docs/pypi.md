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

A publicação é automática a partir de uma release (veja "Releases" em `CONTRIBUTING.md`):

1. O release-please mantém aberto um PR de release com a próxima versão em `pyproject.toml`,
   `uv.lock` e `.release-please-manifest.json`, e a nova entrada do `CHANGELOG.md`, calculadas a
   partir dos Conventional Commits. Revise o PR e confira o CI.
2. Ao fazer merge desse PR em `main`, o workflow
   [Release and publish CLI to PyPI](https://github.com/spassos/igarape/actions/workflows/publish-pypi.yml)
   cria a tag `vX.Y.Z` e a GitHub Release. Na mesma execução, um job monta o sdist e o wheel,
   instala o wheel e testa o projeto gerado; o seguinte publica esses mesmos artefatos. A
   publicação fica no mesmo workflow porque uma release criada com `GITHUB_TOKEN` não dispara
   outros workflows.
3. Se o upload falhar, use **Run workflow** na branch `main` para montar e publicar de novo a
   versão atual. Cada distribuição publicada precisa de uma versão inédita.
4. Após a conclusão, confira o número da versão, o repositório de origem e os arquivos na
   [página do pacote](https://pypi.org/project/igarape/). Em uma pasta vazia,
   execute `uvx --refresh igarape new orders-api` e valide a aplicação gerada.
5. Quando essa instalação pelo índice público estiver verificada, divulgue o comando
   `uvx igarape new orders-api`. Para instalação persistente, use `uv tool install igarape`.

Configuração do repositório para as releases: em **Settings → Actions → General**, habilite
**Allow GitHub Actions to create and approve pull requests** (o release-please abre o PR com
`GITHUB_TOKEN`).
