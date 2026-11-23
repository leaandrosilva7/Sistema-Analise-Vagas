# Sistema de Análise de Vagas Tech — versão RAD em Python

Porte do projeto original (React + Express + Supabase) para o modelo **RAD**:

| Requisito                         | Como foi atendido                                              |
|-----------------------------------|----------------------------------------------------------------|
| Linguagem **Python**              | Python 3.9+ (testado em 3.12)                                  |
| GUI **Tkinter**                   | `ui/` — ttk, abas, formulários, gráficos em Canvas             |
| Banco **SQLite3**                 | `core/db.py` — arquivo único `vagas.db`, criado automaticamente|
| **CRUD**: Inclusão                | Vagas ▸ **Nova vaga** (e Arquivo ▸ Importar CSV/JSON)          |
| **CRUD**: Consulta                | Vagas: filtros, paginação, detalhes, comparação                |
| **CRUD**: Alteração               | Vagas ▸ **Editar** (ou duplo clique ▸ Detalhes)                |
| **CRUD**: Remoção                 | Vagas ▸ **Excluir** (aceita várias; pede confirmação)          |
| **Relatório de Informações**      | Aba **Relatório** (tela, TXT e CSV) + Dashboard (CSV)          |

Não precisa instalar nada: só biblioteca padrão (`tkinter`, `sqlite3`).
No Linux, se faltar o Tkinter: `sudo apt install python3-tk`.

## Interface
Visual moderno só com `ttk`/Tkinter (sem dependências novas): navegação por botões no cabeçalho, cartões de indicadores,
gráficos redesenhados (ranking horizontal + linha com área), tabelas zebradas com seleção destacada, login com painel de
marca e opção de mostrar senha. Em Windows, a escala de tela (HiDPI) é respeitada. Tamanho mínimo da janela: 1040×700.
Todo o tema está em `ui/tema.py` (paleta e fontes no topo do arquivo).

## Conectar ao Supabase (opcional)
O ETL continua gravando no Supabase; o app só **copia** as vagas para o SQLite (leitura, nunca escreve lá).
1. `pip install -r requirements.txt` (instala `psycopg2-binary`).
2. Copie o `.env` do seu projeto ETL para esta pasta (precisa da linha `DATABASE_URL=...`). Há um `.env.example`.
3. No app: botão **⟳ Sincronizar** (ou Arquivo ▸ Sincronizar). Vagas novas entram e as existentes
   (mesma fonte + id_externo, ou mesmo link) são atualizadas. Vagas cadastradas só no app não são apagadas,
   e vagas removidas no Supabase não são removidas localmente.

## Executar
```
python main.py
```
1. Cadastre-se na tela inicial (senha com PBKDF2-SHA256 + salt).
2. Na primeira entrada o sistema oferece **dados de exemplo** (80 vagas fictícias).

## Mapa do projeto original → Python
| Original                                   | Agora                                  |
|--------------------------------------------|----------------------------------------|
| authController (registrar/login)           | `Servico.registrar / login`            |
| vagasController (listar/detalhar/comparar) | `Servico.listar_vagas / detalhes_vaga / comparar_vagas` |
| dashboardController                        | `Servico.metricas / tecnologias_demandadas / tendencias / estatisticas_salariais` |
| coletaController (POST /coleta/vagas)      | `Servico.importar_vagas / importar_arquivo` (dedupe por URL e fonte+id_externo) |
| salaryStats.js                             | `core/salary_stats.py`                 |
| formatters.js / exportCsv.js               | `core/formatadores.py` / `exportar_csv` (protege contra injeção de fórmula) |
| Pages Login/Register/Dashboard/Vagas/VagaDetalhes/CompararVagas | `ui/login.py`, `ui/dashboard.py`, `ui/vagas.py` |
| Tabelas Supabase (vaga, skill, vaga_skill) | mesmas tabelas em SQLite (+ `usuario`) |

### Diferenças intencionais
- Autenticação é **local** (tabela `usuario`), sem tokens/refresh — não há servidor.
- A coleta automática (Adzuna/Jobicy/ETL) foi substituída por **importação de arquivo CSV/JSON** e dados de exemplo.
- Métricas do dashboard são calculadas na hora (antes eram tabelas/views pré-calculadas).
- Estatística salarial considera só vagas em BRL com faixa entre R$ 500 e R$ 200.000 (regra original).
- Se a vaga não tem tecnologias, elas são detectadas pelo título/descrição (regra original).

## Formato de importação
CSV (`,` `;` ou tab) ou JSON (`[...]` ou `{"vagas": [...]}`). Colunas: `titulo`*, `empresa`*, e
`url_original` **ou** (`fonte` + `id_externo`)*; opcionais: `cidade, estado, modalidade, senioridade,
salario_min, salario_max, moeda, descricao, data_publicacao, skills` (separadas por vírgula).

## Testes
```
python -m unittest discover -s tests -t .      # regras de negócio (17 testes)
python tests/smoke_gui.py                       # interface (precisa de display)
```
