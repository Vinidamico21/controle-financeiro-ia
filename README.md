# Controle Financeiro IA

Aplicacao em `Streamlit` para importar extratos em PDF, revisar transacoes, treinar a IA com feedback manual e acompanhar totalizadores gerenciais.

## Rodar localmente

```powershell
cd "c:\Users\vinic\OneDrive\Área de Trabalho\Controle Financeiro"
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
cd .\controle_financeiro
streamlit run app.py
```

## Persistencia

- Sem configuracao extra, a aplicacao usa SQLite local em `controle_financeiro/data/database.db`
- Se `DATABASE_URL` estiver configurado, a aplicacao usa PostgreSQL externo
- O modelo treinado da IA tambem passa a ser salvo no proprio banco, evitando perda de aprendizado em hospedagem cloud

## Deploy no Streamlit Community Cloud

Repositorio:

- `https://github.com/Vinidamico21/controle-financeiro-ia`

Configuracao recomendada no deploy:

- Repository: `Vinidamico21/controle-financeiro-ia`
- Branch: `main`
- Main file path: `controle_financeiro/app.py`

Antes de publicar, configure um banco PostgreSQL free e informe o segredo:

```toml
DATABASE_URL = "postgresql://usuario:senha@host:5432/database?sslmode=require"
```

Voce pode usar a referencia do arquivo `.streamlit/secrets.toml.example`.

## Sugestao de banco free

- Supabase
- Neon

Ambos funcionam bem para esse tipo de app e evitam perder dados/treino quando a hospedagem reinicia.
