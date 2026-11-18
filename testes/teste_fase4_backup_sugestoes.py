import os, json, sys
AQUI = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(AQUI, "teste_fase1_gravacao.py")).read()
exec(src.split('with sync_playwright() as p:')[0])

def db_de(d): return {"app_state":[{"user_id":"u1","data":d,"updated_at":"2026-11-17T10:00:00.000+00:00"}],"app_state_history":[]}
def com_historico():
    d = dados()
    d["plannedItems"].append(dict(id="merc",description="Mercado",type="despesa",categoryId="alimentacao",value=300,mode="recorrente",startMonth="2026-09",grupo="reserva"))
    d["plannedItems"].append(dict(id="luz",description="Energia",type="despesa",categoryId="moradia",value=330,mode="recorrente",startMonth="2026-09",grupo="fixo"))
    d["transactions"] += [
      dict(id="a1",date="2026-09-10",description="Mercado",type="despesa",categoryId="alimentacao",value=320,plannedItemId="merc"),
      dict(id="a2",date="2026-10-10",description="Mercado",type="despesa",categoryId="alimentacao",value=350,plannedItemId="merc"),
      dict(id="b1",date="2026-09-12",description="Energia",type="despesa",categoryId="moradia",value=331.4,plannedItemId="luz"),
      dict(id="b2",date="2026-10-12",description="Energia",type="despesa",categoryId="moradia",value=325.1,plannedItemId="luz"),
      dict(id="s9",date="2026-09-05",description="Salário",type="receita",categoryId="salario",value=3400,plannedItemId="sal"),
      dict(id="s10",date="2026-10-05",description="Salário",type="receita",categoryId="salario",value=3500,plannedItemId="sal"),
    ]
    return d

with sync_playwright() as p:
    br = p.chromium.launch(executable_path=CHROME, args=["--no-sandbox"])
    print("16) Lembrete de backup")
    pg, e = nova_pagina(br, db_base())
    check("Nenhum backup exportado" in pg.inner_text("#app"), "sem backup: lembrete aparece")
    pg.click("text=Lembrar amanhã"); pg.wait_for_timeout(200)
    check("Nenhum backup exportado" not in pg.inner_text("#app"), "'Lembrar amanhã' esconde o lembrete")
    pg.evaluate("() => { localStorage.removeItem('lc-backup-adiado'); render(); }")
    with pg.expect_download() as dl:
        pg.click(".backup-lembrete >> text=Exportar agora")
    pg.wait_for_timeout(300)
    st = pg.evaluate("() => ({ui: state.ultimoBackup, db: window.__db.app_state[0].data.ultimoBackup, txt: document.getElementById('app').innerText})")
    check(bool(st["ui"]) and st["db"] == st["ui"], "exportar grava a data do backup na nuvem")
    check("backup exportado" not in st["txt"], "lembrete some depois do backup")
    d = dados(); d["ultimoBackup"] = "2026-11-09T12:00:00.000Z"
    pg2, e2 = nova_pagina(br, db_de(d))
    check("há 8 dias" in pg2.inner_text("#app").replace("\xa0"," ") or "há 7 dias" in pg2.inner_text("#app"), "backup antigo: avisa há quantos dias")

    print("17) Preparar exercício — sugestões")
    pg3, e3 = nova_pagina(br, db_de(com_historico()))
    r = pg3.evaluate("""() => { const s = sugestoesMetas('2026-12'); const f = id => s.itens.find(x=>x.p.id===id);
        return {hist: s.hist, merc: [f('merc').sugerido, f('merc').relevante], luz: [f('luz').sugerido, f('luz').dif, f('luz').relevante], sal: [f('sal').sugerido, f('sal').dif], tv: f('tv').motivo}; }""")
    print("    ", r)
    check(r["hist"] == ["2026-09", "2026-10"], "usa os meses fechados (set e out)")
    check(r["merc"] == [335, True], "Mercado: 320 e 350 → sugere 335 (relevante)")
    check(r["luz"][0] == 329 and r["luz"][2] is False, "Energia: 331,40 e 325,10 → 329, diferença pequena (não relevante)")
    check(r["sal"][0] == 3450, "Salário (receita): 3400 e 3500 → 3450, arredondado pra baixo")
    check(r["tv"] == "sem histórico ainda", "meta nova: sem sugestão")
    antes = pg3.evaluate("() => getPlannerData(getWithRunningBalance()).filter(x=>x.key<='2026-11').map(x=>x.saldoAcumulado)")
    pg3.evaluate("() => { state.showCfg = true; state.showSugestoes = true; state.sugDesde = '2026-12'; render(); }")
    pg3.locator("[data-action=aplicar-sugestao][data-id=merc]").click(); pg3.wait_for_timeout(300)
    r = pg3.evaluate("""() => { const p = state.plannedItems.find(x=>x.id==='merc'); const v = k => getPlannedItemsForMonth([p], +k.slice(0,4), +k.slice(5,7)-1)[0].value;
        return {set: v('2026-09'), nov: v('2026-11'), dez: v('2026-12'), jan: v('2027-01'), hist: p.historicoValor, db: window.__db.app_state[0].data.plannedItems.find(x=>x.id==='merc').value,
                badge: getPlannedItemsForMonth([p], 2026, 9)[0].overridden || false}; }""")
    print("    ", r)
    check(r["set"] == 300 and r["nov"] == 300 and r["dez"] == 335 and r["jan"] == 335, "passado continua 300, a partir de dez = 335")
    check(r["db"] == 335 and r["badge"] is False, "gravado na nuvem e sem etiqueta 'só este mês' no passado")
    depois = pg3.evaluate("() => getPlannerData(getWithRunningBalance()).filter(x=>x.key<='2026-11').map(x=>x.saldoAcumulado)")
    check(antes == depois, "Planejador de set a nov não mudou")
    pg3.evaluate("() => aplicarValorMetaDesde('merc', 360, '2027-03')")
    r = pg3.evaluate("""() => { const p = state.plannedItems.find(x=>x.id==='merc'); const v = k => getPlannedItemsForMonth([p], +k.slice(0,4), +k.slice(5,7)-1)[0].value;
        return [v('2026-10'), v('2027-01'), v('2027-02'), v('2027-03'), JSON.stringify(p.historicoValor)]; }""")
    check(r[:4] == [300, 335, 335, 360], "segunda mudança: 300 → 335 (dez–fev) → 360 (mar) %s" % r[4])
    pg3.screenshot(path=os.path.join(AQUI, "telas", "8-sugestoes.png"), full_page=True) if os.path.isdir(os.path.join(AQUI, "telas")) else None
    check(pg3.evaluate("() => verificarConsistencia().every(x=>x.ok)"), "verificação de consistência segue verde")
    check(e == [] and e2 == [] and e3 == [], "sem erros de JavaScript")
    br.close()
print("\nRESULTADO:", "TUDO OK" if ok else "HÁ FALHAS")
