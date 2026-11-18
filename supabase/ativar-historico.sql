-- =====================================================================
-- Livro-Caixa — ativação do histórico automático de versões
-- Onde rodar: Supabase → SQL Editor → New query → cole tudo → Run.
-- Pode rodar mais de uma vez sem problema.
-- =====================================================================

-- 1) Tabela que guarda as versões anteriores
create table if not exists public.app_state_history (
  id         bigserial primary key,
  user_id    uuid        not null,
  data       jsonb       not null,
  saved_at   timestamptz,                    -- quando aquela versão tinha sido gravada
  created_at timestamptz not null default now()
);
create index if not exists app_state_history_user_idx
  on public.app_state_history (user_id, created_at desc);

-- 2) Cada usuário só vê e só cria as próprias versões
alter table public.app_state_history enable row level security;
drop policy if exists "historico: ver o proprio"   on public.app_state_history;
drop policy if exists "historico: criar o proprio" on public.app_state_history;
create policy "historico: ver o proprio"   on public.app_state_history
  for select using (auth.uid() = user_id);
create policy "historico: criar o proprio" on public.app_state_history
  for insert with check (auth.uid() = user_id);

-- 3) Gatilho: antes de cada gravação, guarda a versão que estava salva
--    (no máximo uma a cada 30 min por usuário; mantém as 100 mais recentes)
create or replace function public.guardar_versao_app_state()
returns trigger language plpgsql security definer set search_path = public as $$
begin
  if old.data is not null and not exists (
    select 1 from app_state_history h
    where h.user_id = old.user_id::uuid and h.created_at > now() - interval '30 minutes'
  ) then
    insert into app_state_history (user_id, data, saved_at)
    values (old.user_id::uuid, old.data, old.updated_at);

    delete from app_state_history
    where user_id = old.user_id::uuid
      and id not in (select id from app_state_history
                     where user_id = old.user_id::uuid
                     order by created_at desc limit 100);
  end if;
  return new;
end $$;

drop trigger if exists trg_guardar_versao on public.app_state;
create trigger trg_guardar_versao
  before update on public.app_state
  for each row execute function public.guardar_versao_app_state();

-- 4) Conferência de segurança (item 5 do plano): mostra se a proteção por usuário (RLS)
--    está ligada e quais regras existem. Me mande um print do resultado.
select c.relname as tabela, c.relrowsecurity as rls_ligado,
       p.policyname as regra, p.cmd as operacao, p.qual as condicao, p.with_check as condicao_gravar
from pg_class c
left join pg_policies p on p.tablename = c.relname and p.schemaname = 'public'
where c.relnamespace = 'public'::regnamespace and c.relname in ('app_state', 'app_state_history')
order by 1, 3;
