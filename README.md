# cabecao

API **self-hosted** para controle contábil (partidas dobradas) e estoque — projeto próprio, sem dependência de ERP de terceiros.

## Requisitos

- Python 3.11+
- Docker (PostgreSQL) ou instância PostgreSQL acessível

## Configuração

1. Copie `.env.example` para `.env` e ajuste `DATABASE_URL`.
2. Suba o banco: `docker compose up -d`
3. Ambiente virtual e dependências:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

4. API:

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

- Saúde: http://127.0.0.1:8000/health  
- Documentação: http://127.0.0.1:8000/docs  

## Publicar no GitHub (repositório `cabecao`)

1. Crie o repositório vazio em [github.com/new](https://github.com/new) com o nome **cabecao** (sem README/licença gerados pelo site, se quiser evitar conflito no primeiro push).

2. No diretório do projeto:

```powershell
git init
git add .
git commit -m "Initial commit: base API contabil/estoque"
git branch -M main
git remote add origin https://github.com/SEU_USUARIO/cabecao.git
git push -u origin main
```

Substitua `SEU_USUARIO` pelo seu usuário ou organização no GitHub.

### GitHub CLI (opcional)

Com [GitHub CLI](https://cli.github.com/) instalado e autenticado (`gh auth login`):

```powershell
gh repo create cabecao --public --source=. --remote=origin --push
```

## Licença

Defina a licença no repositório conforme sua preferência.
