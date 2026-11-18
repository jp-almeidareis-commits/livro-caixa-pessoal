def dados():
    P=[
     dict(id="sal",description="Salário",type="receita",categoryId="salario",value=3472.99,mode="recorrente",startMonth="2026-09",grupo=""),
     dict(id="tv",description="TV / streaming",type="despesa",categoryId="moradia",value=35,mode="recorrente",startMonth="2026-11",diaVencimento="21",grupo="fixo"),
     dict(id="psi",description="Psicólogo (Marcelo)",type="despesa",categoryId="saude",value=260,mode="pontual",month="2026-11",grupo="eventual"),
     dict(id="carne",description="Carne pro fim de semana",type="despesa",categoryId="alimentacao",value=200,mode="recorrente",startMonth="2026-11",grupo="reserva"),
     dict(id="comb",description="Combustível",type="despesa",categoryId="transporte",value=330,mode="recorrente",startMonth="2026-11",grupo="reserva"),
    ]
    T=[
     dict(id="t1",date="2026-11-05",description="Salário",type="receita",categoryId="salario",value=3472.99,plannedItemId="sal",formaPagamento="pix"),
     dict(id="t2",date="2026-11-10",description="Psicólogo (Marcelo)",type="despesa",categoryId="saude",value=130,plannedItemId="psi",formaPagamento="pix"),
     dict(id="t3",date="2026-11-08",description="Carne pro fim de semana",type="despesa",categoryId="alimentacao",value=200.22,plannedItemId="carne",formaPagamento="pix"),
     dict(id="t4",date="2026-11-09",description="Combustível",type="despesa",categoryId="transporte",value=374.68,plannedItemId="comb",formaPagamento="pix"),
     dict(id="t5",date="2026-11-11",description="Farmácia",type="despesa",categoryId="saude",value=50,formaPagamento="pix"),
    ]
    return {"transactions":T,"plannedItems":P,"categories":[]}
