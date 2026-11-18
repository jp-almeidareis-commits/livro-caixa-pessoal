import os
AQUI = os.path.dirname(os.path.abspath(__file__))
CHROME = "/usr/bin/google-chrome" if os.path.exists("/usr/bin/google-chrome") else None
import json, sys
from playwright.sync_api import sync_playwright
import sys; sys.path.insert(0, AQUI)
from dados import dados
HTML = "file://" + os.environ.get("LC_HTML", os.path.join(AQUI, "..", "index.html"))
STUB = open(os.path.join(AQUI, "stub.js")).read()
ok = True
def check(cond, msg):
    global ok
    print(("  OK  " if cond else "  FALHOU ") + msg)
    ok = ok and cond

def nova_pagina(br, db, fail=None):
    pg = br.new_page(viewport={"width":1300,"height":1000})
    pg.add_init_script("window.__db = %s; window.__fail = %s;" % (json.dumps(db), json.dumps(fail or {})))
    pg.route("**/@supabase/**", lambda r: r.fulfill(status=200, content_type="application/javascript", body=STUB))
    pg.route("https://fonts.**", lambda r: r.abort())
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("dialog", lambda d: d.accept())
    pg.goto(HTML); pg.wait_for_timeout(600)
    return pg, errs

def db_base():
    return {"app_state":[{"user_id":"u1","data":dados(),"updated_at":"2026-11-17T10:00:00.000000+00:00"}],"app_state_history":[]}

with sync_playwright() as p:
    br = p.chromium.launch(executable_path=CHROME, args=["--no-sandbox"])

    print("1) Carregamento normal e números de novembro")
    pg, errs = nova_pagina(br, db_base())
    txt = pg.inner_text("#app").replace("\xa0"," ")
    check("A pagar" in txt, "abriu a tela principal")
    check("R$ 165,00" in txt, "A pagar = R$ 165,00")
    check("1 sem lançamento (R$ 35,00)" in txt and "1 parcial(is) (R$ 130,00)" in txt, "card A pagar mostra sem lançamento e parcial")
    plan = pg.evaluate("""() => { const d = getPlannerData(getWithRunningBalance()); const n = d.find(x=>x.key==='2026-11'); const o = d.find(x=>x.key==='2026-10');
       const mc = getMonthComparison(2026,10); return {net:n.net, acc:n.saldoAcumulado, accOut:o.saldoAcumulado, liq: mc.totalAtualizadoReceita - mc.totalAtualizadoDespesa, ini: saldoInicioProjetado(2026,10)}; }""")
    print("    ", plan)
    check(abs(plan["net"] - plan["liq"]) < 0.01, "Planejador nov = líquido projetado do mês (%.2f)" % plan["net"])
    check(abs(plan["accOut"] - plan["ini"]) < 0.01, "acumulado de out = saldo inicial projetado de nov")
    check(abs(plan["net"] - (3472.99 - (35+260+200.22+374.68+50))) < 0.01, "despesas previstas = 919,90 (inclui o que falta pagar)")

    print("2) Filtro Abertas")
    pg.click("text=ver quais"); pg.wait_for_timeout(200)
    sec = pg.inner_text("#app")
    check("Mostrando" in sec or "mostrando" in sec, "filtro ativo")
    secs = pg.evaluate("""() => [...document.querySelectorAll('.proj-section')].map(e=>e.innerText)""")
    desp = [x for x in secs if 'Despesas' in x][0]
    check("TV / streaming" in desp and "Psicólogo (Marcelo)" in desp and "Combustível" not in desp and "Carne pro fim de semana" not in desp, "mostra só TV e Psicólogo")
    pg.screenshot(path=os.path.join(AQUI, "telas", "1-abertas.png"), full_page=False)

    print("3) Gravações seguidas não geram conflito falso")
    pg.evaluate("() => { state.notes.x = 1; persist(); state.notes.y = 2; persist(); persist(); }")
    pg.wait_for_timeout(500)
    st = pg.evaluate("() => ({c: state.conflict, e: state.saveError, notes: window.__db.app_state[0].data.notes, ind: document.getElementById('save-ind').textContent})")
    check(not st["c"] and not st["e"], "sem conflito/erro")
    check(st["notes"].get("y") == 2, "última alteração chegou na nuvem")
    check("salvo" in st["ind"], "selo mostra 'salvo' (%s)" % st["ind"])

    print("4) Conflito: outro aparelho gravou no meio")
    pg.evaluate("() => { const r = window.__db.app_state[0]; r.data = JSON.parse(JSON.stringify(r.data)); r.data.notes = {outro:'aparelho'}; r.updated_at = '2026-11-17T18:00:00.000+00:00'; }")
    pg.evaluate("() => { state.notes.z = 3; persist(); }"); pg.wait_for_timeout(300)
    st = pg.evaluate("() => ({c: state.conflict, notes: window.__db.app_state[0].data.notes})")
    check(st["c"], "conflito detectado")
    check(st["notes"] == {"outro":"aparelho"}, "dados do outro aparelho NÃO foram sobrescritos")
    check("alterados em outro aparelho" in pg.inner_text("#app"), "aviso de conflito na tela")
    pg.screenshot(path=os.path.join(AQUI, "telas", "2-conflito.png"))
    w = pg.evaluate("window.__writes"); pg.evaluate("() => { state.notes.w = 9; persist(); }"); pg.wait_for_timeout(200)
    check(pg.evaluate("window.__writes") == w, "com conflito, novas ações não gravam")
    pg.click("text=Recarregar dados"); pg.wait_for_timeout(500)
    st = pg.evaluate("() => ({c: state.conflict, notes: state.notes})")
    check(not st["c"] and st["notes"] == {"outro":"aparelho"}, "recarregou a versão nova e liberou gravação")

    print("5) Voltar pra aba recarrega mudanças de outro aparelho")
    pg.evaluate("() => { const r = window.__db.app_state[0]; r.data = JSON.parse(JSON.stringify(r.data)); r.data.notes = {mudou:'sim'}; r.updated_at = '2026-11-17T19:00:00.000+00:00'; }")
    pg.evaluate("() => document.dispatchEvent(new Event('visibilitychange'))"); pg.wait_for_timeout(500)
    check(pg.evaluate("state.notes.mudou") == "sim", "dados atualizados ao voltar pra aba")

    print("6) Versões anteriores")
    pg.evaluate("() => { state.showCfg = true; render(); }")
    pg.click("text=Versões anteriores"); pg.wait_for_timeout(400)
    n = pg.locator("[data-action=restaurar-versao]").count()
    check(n >= 1, "lista versões (%d)" % n)
    pg.screenshot(path=os.path.join(AQUI, "telas", "3-versoes.png"))
    antes = pg.evaluate("window.__db.app_state_history.length")
    pg.locator("[data-action=restaurar-versao]").first.click(); pg.wait_for_timeout(600)
    st = pg.evaluate("() => ({c: state.conflict, e: state.saveError, h: window.__db.app_state_history.length, notesDb: window.__db.app_state[0].data.notes})")
    check(not st["c"] and not st["e"], "restaurou e gravou sem erro")
    check(st["h"] > antes, "versão atual guardada antes de restaurar")
    check(errs == [], "sem erros de JavaScript %s" % errs)

    print("7) Falha ao carregar: tela de erro e nenhuma gravação")
    pg2, errs2 = nova_pagina(br, db_base(), {"app_state.select": True})
    t = pg2.inner_text("#app")
    check("Não consegui carregar seus dados" in t, "tela de erro")
    pg2.screenshot(path=os.path.join(AQUI, "telas", "4-erro-load.png"))
    pg2.evaluate("() => { persist(); }"); pg2.wait_for_timeout(200)
    check(pg2.evaluate("window.__writes") == 0, "nada gravado na nuvem")
    check(pg2.evaluate("window.__db.app_state[0].data.transactions.length") == 5, "dados da nuvem intactos")
    pg2.evaluate("() => { window.__fail = {}; }"); pg2.click("text=Tentar de novo"); pg2.wait_for_timeout(600)
    check("A pagar" in pg2.inner_text("#app"), "'Tentar de novo' carrega normalmente")

    print("8) Erro ao salvar (sem internet)")
    pg2.evaluate("() => { window.__fail = {'app_state.update': true}; state.notes.q = 1; persist(); }"); pg2.wait_for_timeout(300)
    check("Não foi possível salvar" in pg2.inner_text("#app"), "aviso de erro ao salvar")
    pg2.evaluate("() => { window.__fail = {}; }"); pg2.click("text=Tentar salvar de novo"); pg2.wait_for_timeout(300)
    check(pg2.evaluate("window.__db.app_state[0].data.notes.q") == 1 and not pg2.evaluate("state.saveError"), "'Tentar salvar de novo' grava")

    print("9) Primeiro acesso (sem linha) cria a linha")
    pg3, e3 = nova_pagina(br, {"app_state":[], "app_state_history":[]})
    check(pg3.evaluate("window.__db.app_state.length") == 1 and not pg3.evaluate("state.loadError"), "linha criada")
    check(e2 := (errs2 + e3) == [], "sem erros JS nos cenários 7-9")

    print("10) Histórico sem a tabela criada")
    pg4, e4 = nova_pagina(br, {"app_state": db_base()["app_state"]})
    pg4.evaluate("() => { state.showCfg = true; state.showVersoes = true; carregarVersoes(); }"); pg4.wait_for_timeout(300)
    check("ainda não foi ativado" in pg4.inner_text("#app"), "mensagem 'histórico ainda não ativado'")
    br.close()
print("\nRESULTADO:", "TUDO OK" if ok else "HÁ FALHAS")
