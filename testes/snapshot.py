import os
AQUI = os.path.dirname(os.path.abspath(__file__))
CHROME = "/usr/bin/google-chrome" if os.path.exists("/usr/bin/google-chrome") else None
import json, sys, copy
from playwright.sync_api import sync_playwright
import sys; sys.path.insert(0, AQUI)
from dados import dados
STUB = open(os.path.join(AQUI, "stub.js")).read()

def dados_snap():
    d = dados()
    d["plannedItems"].append(dict(id="seg",description="Seguro <b>auto</b> & cia",type="despesa",categoryId="moradia",value=100,mode="pontual",month="2026-10",grupo="eventual"))
    d["plannedItems"].append(dict(id="spot",description="Spotify",type="despesa",categoryId="lazer",value=40.9,mode="recorrente",startMonth="2026-09",grupo="assinatura"))
    d["cartoes"] = [dict(id="nu",nome="Nubank",cor="#8A05BE",icone="💳",vencimentoDia=10)]
    d["parcelados"] = [dict(id="pc1",descricao="Geladeira",valor=100,total=10,numAtual=3,primeiraVenc="2026-10",cartaoId="nu")]
    d["transactions"] += [
      dict(id="t6",date="2026-11-20",description="Loja <x>",type="despesa",categoryId="moradia",value=80,isCartao=True,cartaoId="nu",dueDate="2026-12-10",formaPagamento="cartao"),
      dict(id="t7",date="2026-10-03",description="Geladeira",type="despesa",categoryId="moradia",value=100,isCartao=True,cartaoId="nu",dueDate="2026-10-10",parcelaId="pc1",parcelaNum=3),
      dict(id="t8",date="2026-10-28",description="Spotify",type="despesa",categoryId="lazer",value=40.9,isCartao=True,cartaoId="nu",dueDate="2026-11-10",plannedItemId="spot"),
      dict(id="t9",date="2026-09-05",description="Salário",type="receita",categoryId="salario",value=3472.99,plannedItemId="sal"),
      dict(id="t10",date="2026-08-20",description="Antigo",type="despesa",categoryId="moradia",value=30,isCartao=True,cartaoId="nu",dueDate="2026-09-10"),
    ]
    d["reservaMovs"] = [dict(id="r1",date="2026-11-12",tipo="guardar",valor=100)]
    d["finalizados"] = {}
    return d

TELAS = []
for mes in [8,9,10,11,"ANO"]:
    for area in ["projecoes","lancamentos"]:
        TELAS.append(dict(activeTab="planejamento", area=area, mes=mes))
for rt in ["geral","auditoria","bichos","calendario","cartao","categorias","emprestimos","evolucao","explorar","metas"]:
    TELAS.append(dict(activeTab="relatorios", reportTab=rt, mes=10))
TELAS.append(dict(activeTab="reservas", mes=10))
for flag in ["showCfg+showVerif","showCfg+showGoalsManager","showCfg+showCatManager","showCfg+showParcManager","showCfg+showBichoManager","showCfg+showCardManager","showForm","showCfg+showLoanManager"]:
    TELAS.append(dict(activeTab="planejamento", area="projecoes", mes=10, flags=flag.split("+")))

def run(html_path, out):
    res = {}
    with sync_playwright() as p:
        br = p.chromium.launch(executable_path=CHROME, args=["--no-sandbox"])
        pg = br.new_page(viewport={"width":1300,"height":1000})
        db = {"app_state":[{"user_id":"u1","data":dados_snap(),"updated_at":"2026-11-17T10:00:00.000+00:00"}],"app_state_history":[]}
        pg.add_init_script("window.__db = %s; window.__fail = {};" % json.dumps(db))
        pg.route("**/@supabase/**", lambda r: r.fulfill(status=200, content_type="application/javascript", body=STUB))
        pg.route("https://fonts.**", lambda r: r.abort())
        errs=[]; pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto("file://" + html_path); pg.wait_for_timeout(700)
        for i, t in enumerate(TELAS):
            js = """(t) => {
              ['showCfg','showVerif','showGoalsManager','showCatManager','showParcManager','showBichoManager','showCardManager','showForm','showLoanManager'].forEach(k=>state[k]=false);
              state.activeTab = t.activeTab; if (t.area) state.area = t.area; if (t.reportTab) state.reportTab = t.reportTab;
              state.selectedYear = 2026; if (t.mes === 'ANO') state.showAll = true; else { state.showAll = false; state.selectedMonth = t.mes; }
              (t.flags||[]).forEach(k=>state[k]=true);
              render();
              document.querySelectorAll('#app details').forEach(d=>d.open=true);
              return document.getElementById('app').innerHTML;
            }"""
            res[json.dumps(t, sort_keys=True)] = pg.evaluate(js, t)
        res["__calc"] = pg.evaluate("""() => JSON.stringify({p: getPlannerData(getWithRunningBalance()), c: conciliarSaldos(2026,10), v: verificarConsistencia(), m: [8,9,10,11].map(m=>{const x=getMonthComparison(2026,m); return [x.aPagar,x.aReceber,x.totalAtualizadoDespesa,x.totalRealizadoDespesa]})})""")
        res["__errs"] = errs
        br.close()
    json.dump(res, open(out,"w"))
    print(out, len(res), "telas; erros JS:", errs)

if __name__ == "__main__":
    run(sys.argv[1], sys.argv[2])
