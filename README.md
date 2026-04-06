# cabecao

Sistema **self-hosted**: contabilidade em **partidas dobradas**, **estoque com custo médio**, **compras e vendas à vista** (lançamentos automáticos em Caixa, Estoque, Receita e CMV), **API REST** e **painel web** em `/`.

### Funcionalidades

| Módulo | Descrição |
|--------|-----------|
| Plano de contas | Seed automático: Caixa (`1.1.01`), Estoque (`1.1.02`), Receita (`4.1.01`), CMV (`5.1.01`) |
| Produtos | Cadastro SKU/nome, quantidade e custo médio |
| Compras | Dr Estoque / Cr Caixa; atualiza custo médio |
| Vendas | Dr Caixa / Cr Receita e Dr CMV / Cr Estoque; valida estoque |
| Painel | Abas: resumo, produtos, nova compra/venda, histórico |

### API (`/api`)

- `GET /api/dashboard/summary` — saldos de Caixa e Estoque, contagens
- `GET|POST /api/products`
- `GET|POST /api/purchases` · `GET /api/purchases/{id}`
- `GET|POST /api/sales` · `GET /api/sales/{id}`

Detalhes em `/docs` (Swagger).

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

4. Subir a API + site no navegador:

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

| O que | URL |
|--------|-----|
| **Site (painel)** | http://127.0.0.1:8000/ |
| API JSON | http://127.0.0.1:8000/health |
| Swagger | http://127.0.0.1:8000/docs |

Na rede local (celular/outro PC), use `--host 0.0.0.0` e acesse `http://SEU_IP:8000/` (veja firewall do Windows).

### Testar “online” por URL pública (temporário)

Ferramentas de túnel expõem o `localhost` na internet só enquanto o processo rodar — útil para demonstração, não substitui hospedagem de produção.

- [ngrok](https://ngrok.com/): após instalar, `ngrok http 8000` e abra a URL `https://....ngrok-free.app`.
- [Cloudflare Tunnel](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/) (`cloudflared tunnel --url http://localhost:8000`).

O painel em `/` chama `/health` e `/health/db` no mesmo origin; funciona atrás do túnel desde que o backend esteja no ar com o banco.

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
