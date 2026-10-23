-- GTM Atlas: run in a NEW Supabase project's SQL Editor as postgres.
-- This is the Supabase initialization path; do not also run Alembic 0001.
-- Passwords are managed exclusively by auth.users / Supabase Auth.
begin;
create schema if not exists extensions;
create extension if not exists vector with schema extensions;
set local search_path = public, extensions;

create table if not exists public.users (
  id varchar(36) primary key,
  auth_uid uuid not null unique references auth.users(id) on delete cascade,
  email varchar(254) not null unique,
  password_hash text not null default '' check (password_hash = ''),
  preferences jsonb not null default '{}'::jsonb,
  constraint user_identity_matches check (id = auth_uid::text)
);
comment on column public.users.password_hash is 'Compatibility column; always empty. Supabase Auth owns credentials.';

create table if not exists public.auth_tokens (
  digest varchar(64) primary key,
  user_id varchar(36) not null references public.users(id) on delete cascade,
  expires_at timestamptz not null
);
comment on table public.auth_tokens is 'Local-development compatibility only. Supabase mode never issues local tokens.';

create table if not exists public.knowledge_documents (
  id varchar(100) primary key,
  title text not null,
  kind varchar(20) not null,
  body text not null,
  meta jsonb not null,
  sha256 varchar(64) not null,
  path text not null
);
create table if not exists public.knowledge_chunks (
  id varchar(150) primary key,
  doc_id varchar(100) not null references public.knowledge_documents(id) on delete cascade,
  heading text not null,
  body text not null,
  embedding vector(1536),
  embedding_model varchar(150)
);

-- Aggregates preserve existing application behavior without lossy data migration.
-- mock: questions/answers/evaluations; career/resume_version: confirmed facts/patches;
-- chat_thread: scope/context boundary; conversation: question/answer/citations;
-- resume/private_jd: metadata & extracted text; render_job/checkpoint: task state.
create table if not exists public.business_records (
  id varchar(36) primary key,
  owner varchar(36) not null references public.users(id) on delete cascade,
  kind varchar(40) not null,
  parent_id varchar(36),
  idempotency_key varchar(200),
  data jsonb not null,
  created_at timestamptz not null default now(),
  unique(owner, kind, idempotency_key)
);
create index if not exists ix_business_records_owner on public.business_records(owner);
create index if not exists ix_business_records_kind on public.business_records(kind);
create index if not exists ix_business_records_parent_id on public.business_records(parent_id);
create index if not exists business_history on public.business_records(owner, created_at desc);
create index if not exists ix_knowledge_documents_kind on public.knowledge_documents(kind);
create index if not exists ix_knowledge_chunks_doc_id on public.knowledge_chunks(doc_id);
create index if not exists knowledge_chunks_fts on public.knowledge_chunks using gin(to_tsvector('simple', body));
create index if not exists knowledge_embeddings_hnsw on public.knowledge_chunks using hnsw(embedding vector_cosine_ops);

-- This trigger executes on signup, including accounts awaiting email confirmation.
-- Client metadata is deliberately not trusted for privileges or ownership.
create or replace function public.sync_auth_profile()
returns trigger language plpgsql security definer set search_path = '' as $$
begin
  insert into public.users(id, auth_uid, email, password_hash, preferences)
  values(new.id::text, new.id, new.email, '', '{}'::jsonb)
  on conflict(id) do update set email = excluded.email;
  return new;
end;
$$;
revoke all on function public.sync_auth_profile() from public, anon, authenticated;
drop trigger if exists gtm_auth_profile on auth.users;
create trigger gtm_auth_profile after insert or update of email on auth.users
for each row execute function public.sync_auth_profile();
insert into public.users(id, auth_uid, email, password_hash)
select id::text, id, email, '' from auth.users where email is not null
on conflict(id) do update set email = excluded.email;

alter table public.users enable row level security;
alter table public.auth_tokens enable row level security;
alter table public.business_records enable row level security;
alter table public.knowledge_documents enable row level security;
alter table public.knowledge_chunks enable row level security;

-- Browser reads may only see its own profile and public licensed knowledge.
-- All business mutations go through the API: clients cannot forge resume
-- approvals, render status, scores, trace records or chat context boundaries.
revoke all on public.users, public.auth_tokens, public.business_records,
  public.knowledge_documents, public.knowledge_chunks from anon, authenticated;
grant select on public.users, public.business_records to authenticated;
grant select on public.knowledge_documents, public.knowledge_chunks to anon, authenticated;
drop policy if exists own_profile on public.users;
create policy own_profile on public.users for select to authenticated
  using(id = (select auth.uid())::text);
drop policy if exists own_records on public.business_records;
create policy own_records on public.business_records for select to authenticated
  using(owner = (select auth.uid())::text);
drop policy if exists public_documents on public.knowledge_documents;
create policy public_documents on public.knowledge_documents for select to anon, authenticated
  using(meta->>'permission' = 'public_display' and coalesce(meta->>'deprecated', 'false') <> 'true');
drop policy if exists public_chunks on public.knowledge_chunks;
create policy public_chunks on public.knowledge_chunks for select to anon, authenticated
  using(exists(select 1 from public.knowledge_documents d where d.id = doc_id
    and d.meta->>'permission' = 'public_display' and coalesce(d.meta->>'deprecated','false') <> 'true'));

-- Server DB connection uses a secret connection string, never an anon key.
grant all on public.users, public.auth_tokens, public.business_records,
  public.knowledge_documents, public.knowledge_chunks to service_role;

insert into storage.buckets(id, name, public, file_size_limit)
values('gtm-private', 'gtm-private', false, 10485760)
on conflict(id) do update set public = false, file_size_limit = excluded.file_size_limit;
-- No browser write policies: only the trusted API may create/delete artifacts.
-- Do not create public URLs or broad policies for this bucket.
drop policy if exists gtm_private_read on storage.objects;
create policy gtm_private_read on storage.objects for select to authenticated
using(bucket_id = 'gtm-private' and (storage.foldername(name))[1] = (select auth.uid())::text);

-- Schema matches application migration 0001. Startup must NOT recreate it.
create table if not exists public.alembic_version(version_num varchar(32) primary key);
insert into public.alembic_version(version_num) values('0001') on conflict do nothing;
alter table public.alembic_version enable row level security;
revoke all on public.alembic_version from anon, authenticated;
commit;
