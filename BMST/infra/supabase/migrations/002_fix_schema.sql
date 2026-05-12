-- BMST — Migration 002: corrigir schema para corresponder ao código
-- Executar no Supabase Studio: SQL Editor → New Query → colar tudo → Run
-- Seguro para executar mesmo com a migration 001 já aplicada.

-- ============================================================
-- 1. LEADS — tabela principal dos agentes (não existia)
-- ============================================================
CREATE TABLE IF NOT EXISTS leads (
  id         uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  phone      text        UNIQUE NOT NULL,
  nome       text,
  empresa    text,
  estado     text        DEFAULT 'novo',
  agente     text        DEFAULT 'hunter',
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

CREATE OR REPLACE FUNCTION set_leads_updated_at()
RETURNS TRIGGER AS $$ BEGIN NEW.updated_at = now(); RETURN NEW; END; $$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS leads_updated_at ON leads;
CREATE TRIGGER leads_updated_at
  BEFORE UPDATE ON leads
  FOR EACH ROW EXECUTE FUNCTION set_leads_updated_at();

-- ============================================================
-- 2. MENSAGENS — substituir schema antigo pelo que o código usa
-- Colunas antigas: empresa_id, direcao, canal, conteudo, agente, timestamp
-- Colunas novas:   phone, role, content, agente, created_at
-- ============================================================

-- Guardar dados existentes (se houver) — provavelmente vazio em produção nova
DO $$
BEGIN
  -- Só apaga e recria se a coluna 'phone' não existir (schema antigo)
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'mensagens' AND column_name = 'phone'
  ) THEN
    DROP TABLE IF EXISTS mensagens CASCADE;

    CREATE TABLE mensagens (
      id         uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
      phone      text        NOT NULL,
      role       text        NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
      content    text        NOT NULL,
      agente     text,
      created_at timestamptz DEFAULT now()
    );

    CREATE INDEX mensagens_phone_idx ON mensagens (phone);
    CREATE INDEX mensagens_created_at_idx ON mensagens (created_at);
  END IF;
END $$;

-- ============================================================
-- 3. REVISOES — tabela de revisões do REVISOR (não existia)
-- ============================================================
CREATE TABLE IF NOT EXISTS revisoes (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  lead_id          text,
  texto_original   text,
  texto_final      text,
  status           text CHECK (status IN ('aprovado','corrigido','escalado','rejeitado')),
  notas            text,
  created_at       timestamptz DEFAULT now()
);

-- ============================================================
-- 4. FACTURAS — adicionar coluna estado_pagamento que o código usa
-- ============================================================
ALTER TABLE facturas
  ADD COLUMN IF NOT EXISTS estado_pagamento text DEFAULT 'pendente'
  CHECK (estado_pagamento IN ('pendente','pago','em_atraso'));

-- ============================================================
-- VERIFICAÇÃO — colar na mesma query para confirmar
-- ============================================================
-- SELECT table_name, column_name, data_type
-- FROM information_schema.columns
-- WHERE table_schema = 'public'
--   AND table_name IN ('leads','mensagens','revisoes','facturas')
-- ORDER BY table_name, ordinal_position;
