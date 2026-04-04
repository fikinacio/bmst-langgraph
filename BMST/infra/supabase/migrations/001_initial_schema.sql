-- BMST Skeleton Crew — Schema inicial
-- Executar no Supabase Studio: SQL Editor → New Query → colar tudo → Run

-- Extensões
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================================
-- EMPRESAS — base de prospecção do HUNTER
-- ============================================================
CREATE TABLE empresas (
  id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  nome               text NOT NULL,
  sector             text,
  segmento           char(1) CHECK (segmento IN ('A','B','C')),
  website            text,
  whatsapp           text,
  localizacao        text,
  n_funcionarios_est int,
  estado             text DEFAULT 'prospecto'
                     CHECK (estado IN ('prospecto','contactado','interessado',
                                       'neutro','fora_perfil','cliente')),
  fonte              text,
  created_at         timestamptz DEFAULT now(),
  updated_at         timestamptz DEFAULT now()
);

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$ BEGIN NEW.updated_at = now(); RETURN NEW; END; $$ LANGUAGE plpgsql;

CREATE TRIGGER empresas_updated_at
  BEFORE UPDATE ON empresas
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ============================================================
-- CONTACTOS — pessoas nas empresas
-- ============================================================
CREATE TABLE contactos (
  id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  empresa_id uuid REFERENCES empresas(id),
  nome       text,
  cargo      text,
  whatsapp   text,
  email      text,
  created_at timestamptz DEFAULT now()
);

-- ============================================================
-- DEALS — pipeline do CLOSER
-- ============================================================
CREATE TABLE deals (
  id                     uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  empresa_id             uuid REFERENCES empresas(id),
  contacto_id            uuid REFERENCES contactos(id),
  servico                text,
  valor_aoa              numeric,
  valor_usd              numeric,
  estado                 text DEFAULT 'novo'
                         CHECK (estado IN ('novo','diagnostico','proposta_enviada',
                                           'negociacao','fechado','perdido')),
  aprovado_pelo_fundador boolean DEFAULT false,
  data_proposta          date,
  data_fecho             date,
  created_at             timestamptz DEFAULT now()
);

-- ============================================================
-- MENSAGENS — histórico WhatsApp/Email
-- ============================================================
CREATE TABLE mensagens (
  id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  empresa_id uuid REFERENCES empresas(id),
  direcao    text CHECK (direcao IN ('entrada','saida')),
  canal      text CHECK (canal IN ('whatsapp','email')),
  conteudo   text,
  agente     text CHECK (agente IN ('hunter','closer','delivery','ledger','humano')),
  timestamp  timestamptz DEFAULT now()
);

-- ============================================================
-- PROJECTOS — gestão do DELIVERY
-- ============================================================
CREATE TABLE projectos (
  id                    uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  deal_id               uuid REFERENCES deals(id),
  empresa_id            uuid REFERENCES empresas(id),
  nome                  text,
  estado                text DEFAULT 'onboarding'
                        CHECK (estado IN ('onboarding','em_curso','bloqueado','concluido')),
  progresso_pct         int DEFAULT 0 CHECK (progresso_pct BETWEEN 0 AND 100),
  data_inicio           date,
  data_entrega_prevista date,
  created_at            timestamptz DEFAULT now()
);

-- ============================================================
-- FACTURAS — LEDGER + InvoiceNinja sync
-- ============================================================
CREATE TABLE facturas (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  deal_id          uuid REFERENCES deals(id),
  empresa_id       uuid REFERENCES empresas(id),
  valor_aoa        numeric,
  valor_usd        numeric,
  estado           text DEFAULT 'rascunho'
                   CHECK (estado IN ('rascunho','enviada','paga','atrasada')),
  data_emissao     date,
  data_vencimento  date,
  invoice_ninja_id text,
  created_at       timestamptz DEFAULT now()
);

-- ============================================================
-- EMBEDDINGS — RAG via pgvector
-- Dimensão 1536 = OpenAI ada-002 (default Dify).
-- Ajustar para 768 se usares nomic-embed-text ou outro modelo local.
-- ============================================================
CREATE TABLE embeddings (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  conteudo      text,
  embedding     vector(1536),
  tipo          text CHECK (tipo IN ('empresa','deal','mensagem','documento')),
  referencia_id uuid,
  created_at    timestamptz DEFAULT now()
);

CREATE INDEX ON embeddings USING ivfflat (embedding vector_cosine_ops);

-- ============================================================
-- VERIFICAÇÃO — correr após criar o schema
-- ============================================================
-- SELECT table_name FROM information_schema.tables
-- WHERE table_schema = 'public'
-- ORDER BY table_name;
-- Resultado esperado: contactos, deals, embeddings, empresas, facturas, mensagens, projectos
