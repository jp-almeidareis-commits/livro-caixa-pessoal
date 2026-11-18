# Testes do Livro-Caixa

Testes automáticos que rodam o app de verdade num navegador (Chrome, via Playwright), com um
**Supabase simulado** (`stub.js`, banco em memória). Nada aqui acessa a nuvem nem seus dados reais.

| Arquivo | O que confere |
|---|---|
| `teste_fase1_gravacao.py` | Gravação segura: falha de carregamento não grava; conflito entre aparelhos não sobrescreve; gravações seguidas; erro de rede; versões anteriores; números de novembro (A pagar, Planejador). |
| `teste_fase2_saldos.py` | Conciliação dos três saldos (resíduo zero) e a Verificação de consistência acusando dados quebrados. |
| `snapshot.py` | "Fotografia" do HTML de 31 telas. Use antes e depois de uma mudança que **não** deveria alterar nada (ex.: reorganizar código) e compare. |
| `teste_fase4_backup_sugestoes.py` | Lembrete de backup e "Preparar exercício" (sugestões pelo histórico; aplicar a partir de um mês sem mudar o passado). |
| `dados.py` | Dados de teste (parecidos com nov/2026). |

## Como rodar (para quem for mexer no código — inclusive o Claude)

```bash
pip install playwright && playwright install chromium   # uma vez
python3 testes/teste_fase1_gravacao.py                  # deve terminar com "RESULTADO: TUDO OK"
python3 testes/teste_fase2_saldos.py
python3 testes/teste_fase4_backup_sugestoes.py
# mudança que não deveria alterar telas:
python3 testes/snapshot.py "$PWD/index.html" antes.json   # na versão antiga
python3 testes/snapshot.py "$PWD/index.html" depois.json  # na versão nova → comparar os dois JSON
```

Para testar outro arquivo: `LC_HTML=/caminho/index.html python3 testes/teste_fase1_gravacao.py`.

Regra: **nenhuma versão vai pro ar sem os dois testes passando** e sem a "Verificação de consistência"
(Configurar → 🩺) ficar toda verde com os dados reais.
