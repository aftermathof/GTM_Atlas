-- Read-only initialization audit. Run as postgres in Supabase SQL Editor.
select c.relname as table_name, c.relrowsecurity as rls_enabled
from pg_class c join pg_namespace n on n.oid = c.relnamespace
where n.nspname = 'public' and c.relname in (
  'users', 'auth_tokens', 'business_records', 'knowledge_documents', 'knowledge_chunks', 'alembic_version'
);
select schemaname, tablename, policyname, roles, cmd from pg_policies
where (schemaname = 'public' and tablename in ('users','auth_tokens','business_records','knowledge_documents','knowledge_chunks'))
   or (schemaname = 'storage' and policyname = 'gtm_private_read');
select id, public, file_size_limit from storage.buckets where id = 'gtm-private';
select tgname, tgenabled from pg_trigger where tgname = 'gtm_auth_profile';
select extname, extversion from pg_extension where extname = 'vector';
select count(*) as nonempty_compatibility_passwords from public.users where password_hash <> '';
select count(*) as auth_profiles_without_business_profile
from auth.users a left join public.users p on p.auth_uid = a.id
where a.email is not null and p.id is null;
-- Expected: all six tables RLS=true, private bucket public=false,
-- trigger enabled, vector installed, both counts=0.
