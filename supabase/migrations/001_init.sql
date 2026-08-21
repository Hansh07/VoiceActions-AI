-- VoiceActions AI — Supabase Database Schema
-- Run this in the Supabase SQL Editor

-- Enable pgvector extension for semantic search
create extension if not exists vector;

-- ─── Voice Notes ─────────────────────────────────────────
create table if not exists voice_notes (
  id uuid primary key default gen_random_uuid(),
  audio_url text default '',
  transcript text not null,
  language text default 'auto',
  duration_seconds float default 0,
  created_at timestamptz default now()
);

-- ─── Action Items ────────────────────────────────────────
create table if not exists actions (
  id uuid primary key default gen_random_uuid(),
  voice_note_id uuid references voice_notes(id) on delete cascade,
  task text not null,
  owner text default 'unassigned',
  deadline text default 'not specified',
  priority text check (priority in ('high', 'medium', 'low')) default 'medium',
  source_quote text default '',
  status text default 'pending',
  embedding vector(768),
  created_at timestamptz default now()
);

-- ─── Conflicts ───────────────────────────────────────────
create table if not exists conflicts (
  id uuid primary key default gen_random_uuid(),
  voice_note_id uuid references voice_notes(id) on delete cascade,
  action_a_id uuid references actions(id) on delete set null,
  action_b_id uuid references actions(id) on delete set null,
  reason text not null default '',
  severity text check (severity in ('high', 'medium', 'low')) default 'medium',
  affected_people text[] default '{}',
  created_at timestamptz default now()
);

-- ─── Processing Logs (Observability) ────────────────────
create table if not exists processing_logs (
  id uuid primary key default gen_random_uuid(),
  voice_note_id uuid references voice_notes(id) on delete cascade,
  step text not null,
  model_used text default '',
  tokens_input int default 0,
  tokens_output int default 0,
  latency_ms int default 0,
  estimated_cost_usd float default 0,
  prompt_version text default '',
  retries int default 0,
  fallback_used boolean default false,
  error text,
  created_at timestamptz default now()
);

-- ─── Indexes ─────────────────────────────────────────────
create index if not exists idx_actions_voice_note on actions(voice_note_id);
create index if not exists idx_conflicts_voice_note on conflicts(voice_note_id);
create index if not exists idx_logs_voice_note on processing_logs(voice_note_id);
create index if not exists idx_voice_notes_created on voice_notes(created_at desc);

-- ─── pgvector Semantic Search Function ──────────────────
create or replace function search_actions(query_embedding vector(768), match_count int default 10)
returns table(id uuid, task text, owner text, similarity float)
language plpgsql as $$
begin
  return query
  select 
    actions.id,
    actions.task,
    actions.owner,
    1 - (actions.embedding <=> query_embedding) as similarity
  from actions
  where actions.embedding is not null
  order by actions.embedding <=> query_embedding
  limit match_count;
end;
$$;

-- ─── Storage Bucket for Audio ───────────────────────────
-- Note: Create this in Supabase Dashboard > Storage > New Bucket
-- Bucket name: "audio"
-- Public: true
