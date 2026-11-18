import os
AQUI = os.path.dirname(os.path.abspath(__file__))
CHROME = "/usr/bin/google-chrome" if os.path.exists("/usr/bin/google-chrome") else None
import json, copy
src=open(os.path.join(AQUI, 'teste_fase1_gravacao.py')).read()
exec(src.split('with sync_playwright() as p:')[0])
def rico():
    d = dados()
    d["plannedItems"].append(dict(id="seg",description="Seguro",type="despesa",categoryId="moradia",value=100,mode="pontual",month="2026-10",grupo="eventual"))
    d["transactions"].append(dict(id="t6",date="2026-11-20",description="Loja",type="despesa",categoryId="moradia",value=80,isCartao=True,dueDate="2026-12-10",formaPagamento="cartao"))
    d["reservaMovs"] = [dict(id="r1",date="2026-11-12",tipo="guardar",valor=100)]
    return d
def db_de(d): return {"app_state":[{"user_id":"u1","data":d,"updated_at":"2026-11-17T10:00:00.000+00:00"}],"app_state_history":[]}

with sync_playwright() as p:
    br = p.chromium.launch(executable_path=CHROME, args=["--no-sandbox"])
    print("11) Conciliação dos saldos")
    pg, errs = nova_pagina(br, db_de(rico()))
    r = pg.evaluate("""() => {
      const c = conciliarSaldos(2026, 10);
      const pd = getPlannerData(getWithRunningBalance()).find(x=>x.key==='2026-11');
      const pb = getPeriodBounds(2026,10);
      const proj = saldoInicioProjetado(2026,10) + reservaAjusteLivre(null, addDaysISO(pb.start,-1)) + getMonthComparison(2026,10).totalAtualizadoReceita - getMonthComparison(2026,10).totalAtualizadoDespesa + reservaAjusteLivre(pb.start,pb.end);
      const stamp = [...document.querySelectorAll('.stamp .t2')].map(e=>e.textContent)[0];
      return {c, proj, plan: pd.saldoAcumulado, stamp};
    }""")
    c = r["c"]
    print("    caixa %.2f | aVencer %.2f | comp %.2f | pendAnt %.2f | pendMes %.2f | proj %.2f | ra %.2f | plan %.2f | resid %.4f" % (c["caixa"], c["aVencer"]["total"], c["competencia"], c["pendAnt"], c["pendMes"], c["projetado"], c["ra"], c["planejador"], c["classif"]+c["pendResid"]))
    check(abs(c["classif"] + c["pendResid"]) < 0.005, "resíduo zero")
    check(abs(c["projetado"] - r["proj"]) < 0.005, "projetado = Saldo final projetado da tela")
    check(abs(c["planejador"] - r["plan"]) < 0.005, "planejador = Acumulado do Planejador")
    check(abs(c["caixa"] - 2618.09) < 0.005 and r["stamp"].replace("\xa0"," ") == "R$ 2.618,09", "caixa = selo do saldo livre (%s)" % r["stamp"])
    check(abs(c["caixa"] + c["aVencer"]["total"] - c["pagosOutro"]["total"] - c["competencia"]) < 0.005, "caixa → competência fecha")
    pg.click("text=De onde vem cada saldo"); pg.wait_for_timeout(200)
    pg.locator("details.more:has-text('De onde vem cada saldo')").screenshot(path=os.path.join(AQUI, "telas", "5-conciliacao.png"))
    t = pg.inner_text("#app")
    check("Pendências de meses anteriores" in t and "Movimentos de reserva" in t and "Compras já feitas" in t, "quadro mostra as linhas esperadas")
    check("Outras diferenças" not in t, "sem linha de 'outras diferenças'")

    print("12) Verificação de consistência")
    pg.evaluate("() => { state.showCfg = true; state.showVerif = true; render(); }"); pg.wait_for_timeout(200)
    t = pg.inner_text("#app")
    check("Tudo certo" in t, "dados bons: tudo certo")
    pg.locator(".panel:has(.panel-title:has-text('Verificação de consistência'))").screenshot(path=os.path.join(AQUI, "telas", "6-verif-ok.png"))
    bad = rico()
    bad["transactions"].append(copy.deepcopy(bad["transactions"][1]))              # id duplicado
    bad["transactions"].append(dict(id="t9",date="2026-11-12",description="Órfão",type="despesa",categoryId="xyz",value=10,plannedItemId="nao-existe"))
    bad["parcelados"] = [dict(id="pc1",descricao="Geladeira",valor=100,total=10,numAtual=5,primeiraVenc="2026-11",cartaoId=None)]
    bad["transactions"].append(dict(id="t10",date="2026-11-03",description="Geladeira",type="despesa",categoryId="moradia",value=100,parcelaId="pc1",parcelaNum=3))  # parcela fora do intervalo
    pg2, e2 = nova_pagina(br, db_de(bad))
    pg2.evaluate("() => { state.showCfg = true; state.showVerif = true; render(); }"); pg2.wait_for_timeout(200)
    falhas = pg2.evaluate("() => verificarConsistencia().filter(x=>!x.ok).map(x=>x.titulo)")
    print("    ", falhas); t = "\n".join("⚠️ " + f for f in falhas)
    check("Lançamentos com identificador único" in t and "⚠️ Lançamentos com identificador único" in t, "acusa id duplicado")
    check("⚠️ Vínculo com meta válido" in t, "acusa meta apagada")
    check("⚠️ Lançamentos com categoria existente" in t, "acusa categoria apagada")
    check("⚠️ Todo lançamento conta uma vez só" in t, "acusa lançamento fora dos totais (parcela fora do intervalo)")
    pg2.locator(".panel:has(.panel-title:has-text('Verificação de consistência'))").screenshot(path=os.path.join(AQUI, "telas", "7-verif-problemas.png"))
    check(errs == [] and e2 == [], "sem erros de JavaScript %s %s" % (errs, e2))

    print("13) Rodapé de versão")
    check("versão 2026.11.17-e" in pg.inner_text("body"), "rodapé com versão")
    br.close()
print("\nRESULTADO:", "TUDO OK" if ok else "HÁ FALHAS")

# ---- versão d: centavos e exercícios dinâmicos ----
with sync_playwright() as p:
    br = p.chromium.launch(executable_path=CHROME, args=["--no-sandbox"])
    print("14) Meta que fecha exata não aparece estourada (centavos)")
    d = dados()
    d["plannedItems"].append(dict(id="merc",description="Mercado",type="despesa",categoryId="alimentacao",value=171,mode="recorrente",startMonth="2026-11",grupo="reserva"))
    d["transactions"] += [dict(id=f"m{i}",date=f"2026-11-0{i+1}",description="Mercado",type="despesa",categoryId="alimentacao",value=v,plannedItemId="merc") for i,v in enumerate([82.18,62.92,25.9])]
    pg, e = nova_pagina(br, db_de(d))
    r = pg.evaluate("() => { const x = getMonthComparison(2026,10).rows.find(r=>r.id==='merc'); return {real:x.realizado, exc:x.excedida, st: metaStatus(x).id}; }")
    check(r["real"] == 171 and not r["exc"] and r["st"] == "lancada", "82,18 + 62,92 + 25,90 = 171 → 'lançada' (%s)" % r)
    print("15) Exercícios dinâmicos")
    r = pg.evaluate("""() => { const real = Date; const anos = {};
      for (const hoje of ['2026-11-17','2027-12-31','2028-01-01','2031-06-10']) {
        window.localTodayISO = () => hoje; anos[hoje] = [anosExercicio().join(','), getPlannerMonths().slice(-1)[0].key]; }
      return anos; }""")
    print("    ", r)
    check(r["2026-11-17"] == ["2026,2027", "2027-12"], "hoje: 2026–2027 (igual ao que era)")
    check(r["2028-01-01"][1] == "2029-12" and "2028" in r["2028-01-01"][0], "em 2028 abre até dez/2029")
    check(e == [], "sem erros JS")
    br.close()
print("\nRESULTADO FINAL:", "TUDO OK" if ok else "HÁ FALHAS")
