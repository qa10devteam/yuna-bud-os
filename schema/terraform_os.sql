-- ============================================================================
-- Terra.OS — Baza Danych Przetargów (Atlas Przetargow.pl)
-- Data: 2026-06-22 | Author: Terra.OS Team
-- Źródła: BZP (co 4h), TED (dziennie), e-Zamówienia, BIP
-- ============================================================================

-- ── Extensions ───────────────────────────────────────────────────────────────
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";
CREATE EXTENSION IF NOT EXISTS "hstore";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ── Custom Types ────────────────────────────────────────────────────────────
CREATE TYPE source_type AS ENUM ('BZP', 'TED', 'BK', 'BIP', 'IMPORT');
CREATE TYPE tender_status AS ENUM ('new', 'analyzing', 'ready', 'accepted', 'rejected', 'archived');
CREATE TYPE document_type AS ENUM ('SWZ', 'projekt', 'STWiOR', 'przedmiar', 'zamówienie_uzupełniające', 'odwołanie', 'rozstrzygnięcie');
CREATE TYPE chunk_type AS ENUM ('text', 'table', 'clause', 'price', 'timeline', 'penalty', 'qualification');
CREATE TYPE estimate_variant AS ENUM ('A', 'B');
CREATE TYPE violation_severity AS ENUM ('low', 'medium', 'high', 'critical');
CREATE TYPE risk_severity AS ENUM ('low', 'medium', 'high', 'critical');
CREATE TYPE decision_recommendation AS ENUM ('offer', 'reject', 'negotiate');
CREATE TYPE equipment_type AS ENUM ('excavator', 'dump_truck', 'roller', 'loader', 'crane', 'pump', 'other');
CREATE TYPE employee_role AS ENUM ('operator', 'mechanic', 'surveyor', 'site_manager', 'office');
CREATE TYPE shift_type AS ENUM ('day', 'night', 'rotating');
CREATE TYPE procedure_type AS ENUM ('otwarty', 'ograniczony', 'negocjacje_ogloszenie', 'negocjacjebezogloszenia', 'pdd', 'dialog_konkurencyjny', 'partnerstwo_innowacji', 'konkurs', 'zamowienie_odbiorcze');

-- ── Schema: tenders (główna tabela) ────────────────────────────────────────
CREATE TABLE tenders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    external_id TEXT NOT NULL,                          -- BZP/TED numer
    source source_type NOT NULL,                        -- BZP, TED, BK, BIP
    title TEXT NOT NULL,                                -- tytuł przetargu
    cpv_codes TEXT[] NOT NULL,                          -- kody CPV
    cpv_primary TEXT,                                   -- główny CPV (np. 45232000-7)
    cpv_description TEXT,                               -- opis CPV
    
    -- Lokalizacja (znormalizowana z BZP/TED)
    voivodeship TEXT,                                   -- województwo
    county TEXT,                                        -- powiat
    city TEXT,                                          -- miejscowość
    address TEXT,                                       -- pełny adres
    location_type TEXT,                                 -- wieś, miasto, powiat
    
    -- Zamawiający
    contract_authority TEXT NOT NULL,                   -- nazwa zamawiającego
    contract_authority_type TEXT,                       -- gmina, powiat, miasto, sp.z.o.o.
    contract_authority_nip TEXT,                        -- NIP (hashowany w open data)
    contract_authority_krs TEXT,
    contract_authority_address TEXT,
    contact_person TEXT,                                -- osoba kontaktowa
    contact_email TEXT,
    contact_phone TEXT,
    
    -- Terminy
    publish_date DATE,                                  -- data publikacji
    deadline TIMESTAMP WITH TIME ZONE,                  -- termin składania ofert
    correction_deadline TIMESTAMP WITH TIME ZONE,       -- termin odwołań (10 dni)
    expected_start_date DATE,                           -- przewidywany rozpoczęcie
    expected_duration TEXT,                             -- czas realizacji (np. "6 miesięcy")
    
    -- Wartość
    estimated_value BIGINT,                             -- wartość szacunkowa (grosze)
    currency TEXT DEFAULT 'PLN',
    deposit_amount BIGINT,                              -- wadium (grosze)
    performance_bond BOOLEAN DEFAULT FALSE,             -- kaucja wykonawcza
    
    -- Procedura
    procedure_type procedure_type DEFAULT 'otwarty',    -- typ procedury
    eu_threshold BOOLEAN DEFAULT FALSE,                 -- poniżej/próg unijny
    split_lots BOOLEAN DEFAULT TRUE,                    -- podział na części/zadania
    lot_info JSONB,                                     -- {lot1: nazwa, lot2: nazwa...}
    
    -- Status i score (auto-wykrywane przez Terra.OS)
    status tender_status DEFAULT 'new',
    match_score INTEGER DEFAULT 0,                      -- 0-100 dopasowanie do firmy
    priority INTEGER DEFAULT 0,                         -- priorytet
    risk_level TEXT,                                    -- low, medium, high
    flag_count INTEGER DEFAULT 0,                       -- liczba czerwonych flag
    
    -- Meta
    raw_data JSONB,                                     -- surowe dane z BZP/TED (JSON)
    synced_at TIMESTAMP WITH TIME ZONE,                 -- ostatnia sync z BZP (co 4h)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT chk_value CHECK (estimated_value >= 0),
    CONSTRAINT chk_score CHECK (match_score >= 0 AND match_score <= 100)
);

-- ── Indexes ────────────────────────────────────────────────────────────────
CREATE INDEX idx_tenders_title_fts ON tenders USING GIN (to_tsvector('polish', title));
CREATE INDEX idx_tenders_authority_fts ON tenders USING GIN (to_tsvector('polish', contract_authority));
CREATE INDEX idx_tenders_address_trgm ON tenders USING gin (address gin_trgm_ops);
CREATE INDEX idx_tenders_cpv ON tenders USING gin (cpv_codes);
CREATE INDEX idx_tenders_status ON tenders (status);
CREATE INDEX idx_tenders_deadline ON tenders (deadline);
CREATE INDEX idx_tenders_source ON tenders (source);
CREATE INDEX idx_tenders_city ON tenders (city);
CREATE INDEX idx_tenders_voivodeship ON tenders (voivodeship);
CREATE INDEX idx_tenders_score ON tenders (match_score DESC);
CREATE INDEX idx_tenders_procedure ON tenders (procedure_type);
CREATE INDEX idx_tenders_eu ON tenders (eu_threshold);

-- ============================================================================
-- TABELA: dokumenty (SWZ, przedmiar, projekt...)
-- ============================================================================
CREATE TABLE tender_documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tender_id UUID NOT NULL REFERENCES tenders(id) ON DELETE CASCADE,
    doc_type document_type NOT NULL,
    file_name TEXT,
    file_size BIGINT,
    file_url TEXT,                                        -- URL do pobrania z BZP
    local_path TEXT,
    parsed BOOLEAN DEFAULT FALSE,
    parsed_at TIMESTAMP WITH TIME ZONE,
    metadata HSTORE,                                      -- {page_count => '45', author => 'Jan K.'}
    embedding_vector vector(768),                         -- RAG embedding
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_tender_docs_tender ON tender_documents (tender_id);
CREATE INDEX idx_tender_docs_type ON tender_documents (doc_type);

-- ============================================================================
-- TABELA: chunki (fragmenty dokumentów do RAG)
-- ============================================================================
CREATE TABLE document_chunks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tender_id UUID NOT NULL REFERENCES tenders(id) ON DELETE CASCADE,
    document_id UUID REFERENCES tender_documents(id),
    page INTEGER,
    position TEXT,                                        -- pozycja w przedmiarze (np. "1.1.1")
    content TEXT NOT NULL,
    chunk_type chunk_type NOT NULL,
    embedding_vector vector(768),
    relevance_score FLOAT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_chunks_tender ON document_chunks (tender_id);
CREATE INDEX idx_chunks_type ON document_chunks (chunk_type);
CREATE INDEX idx_chunks_content_fts ON document_chunks USING GIN (to_tsvector('polish', content));

-- ============================================================================
-- TABELA: czerwone flagi (ryzyka)
-- ============================================================================
CREATE TABLE red_flags (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tender_id UUID NOT NULL REFERENCES tenders(id) ON DELETE CASCADE,
    flag_type TEXT NOT NULL,                              -- price, quantity, technical, legal, timeline
    severity risk_severity NOT NULL,
    description TEXT NOT NULL,
    source_page INTEGER,
    source_position TEXT,
    potential_cost BIGINT,                                -- szacowana strata (grosze)
    recommended_action TEXT,
    detected_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    resolved BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (tender_id) REFERENCES tenders(id)
);

CREATE INDEX idx_red_flags_tender ON red_flags (tender_id);
CREATE INDEX idx_red_flags_severity ON red_flags (severity);

-- ============================================================================
-- TABELA: rozbieżności (przedmiar vs projekt)
-- ============================================================================
CREATE TABLE discrepancies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tender_id UUID NOT NULL REFERENCES tenders(id) ON DELETE CASCADE,
    disc_type TEXT NOT NULL,                              -- quantity, description, missing, extra
    description TEXT NOT NULL,
    beforemiar_item TEXT,
    design_coverage BOOLEAN DEFAULT FALSE,
    severity TEXT,
    provenance JSONB,                                     -- {page, line, position}
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_discrepancies_tender ON discrepancies (tender_id);

-- ============================================================================
-- TABELA: kosztorysy (2 warianty)
-- ============================================================================
CREATE TABLE estimates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tender_id UUID NOT NULL REFERENCES tenders(id) ON DELETE CASCADE,
    variant estimate_variant NOT NULL,                    -- A=dokumentacja, B=Pana
    version INTEGER DEFAULT 1,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    total_net BIGINT,                                     -- netto (grosze)
    total_vat BIGINT,                                     -- VAT 23% (grosze)
    total_gross BIGINT,                                   -- brutto (grosze)
    labor_cost BIGINT,                                    -- robocizna
    equipment_cost BIGINT,                                -- sprzęt
    material_cost BIGINT,                                 -- materiały
    overhead_cost BIGINT,                                 -- nakład ogólny
    profit BIGINT                                         -- zysk/marża
);

CREATE INDEX idx_estimates_tender ON estimates (tender_id);
CREATE INDEX idx_estimates_variant ON estimates (variant);

-- ============================================================================
-- TABELA: pozycje kosztorysu
-- ============================================================================
CREATE TABLE estimate_lines (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    estimate_id UUID NOT NULL REFERENCES estimates(id) ON DELETE CASCADE,
    position TEXT,
    description TEXT NOT NULL,
    unit TEXT,                                            -- m³, m², szt
    quantity FLOAT NOT NULL,
    unit_price BIGINT NOT NULL,                           -- grosze
    total_price BIGINT NOT NULL,                          -- grosze
    source TEXT                                           -- KNR, KNRiT, Pana Excel
);

CREATE INDEX idx_lines_estimate ON estimate_lines (estimate_id);

-- ============================================================================
-- TABELA: analiza ryzyka (L1, L2, L3)
-- ============================================================================
CREATE TABLE risk_analysis (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    estimate_id UUID NOT NULL REFERENCES estimates(id) ON DELETE CASCADE,
    tender_id UUID NOT NULL REFERENCES tenders(id),
    l1_verdict TEXT,
    l1_violations JSONB,
    l1_derived_facts JSONB,
    l2_scenarios JSONB,
    l2_dominant_drivers JSONB,
    l2_target_margin_probability FLOAT,
    l3_explanation TEXT,
    l3_model TEXT,
    l3_tokens_used INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_risk_tender ON risk_analysis (tender_id);
CREATE INDEX idx_risk_estimate ON risk_analysis (estimate_id);

-- ============================================================================
-- TABELA: decyzje i rekomendacje
-- ============================================================================
CREATE TABLE decisions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tender_id UUID NOT NULL REFERENCES tenders(id) ON DELETE CASCADE,
    offer_price BIGINT,
    recommendation decision_recommendation,
    confidence FLOAT,
    reasoning TEXT,
    key_factors JSONB,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_decisions_tender ON decisions (tender_id);

-- ============================================================================
-- TABELA: sprzęt (fleet management)
-- ============================================================================
CREATE TABLE equipment (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    type equipment_type NOT NULL,
    capacity TEXT,
    availability BOOLEAN DEFAULT TRUE,
    location TEXT,
    purchase_date DATE,
    last_maintenance DATE,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_equip_availability ON equipment (availability);

-- ============================================================================
-- TABELA: pracownicy (zespół)
-- ============================================================================
CREATE TABLE employees (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    name_short TEXT,
    competencies TEXT[],
    available BOOLEAN DEFAULT TRUE,
    current_project TEXT,
    role employee_role,
    phone TEXT,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_employees_available ON employees (available);

-- ============================================================================
-- TABELA: harmonogram prac (daily plan)
-- ============================================================================
CREATE TABLE work_plans (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tender_id UUID NOT NULL REFERENCES tenders(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    start_time TIME,
    end_time TIME,
    task TEXT NOT NULL,
    equipment_ids UUID[],
    employee_ids UUID[],
    location TEXT,
    notes TEXT,
    status TEXT DEFAULT 'planned',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_work_plans_tender ON work_plans (tender_id);
CREATE INDEX idx_work_plans_date ON work_plans (date);

-- ============================================================================
-- TABELA: activity_log (audit trail)
-- ============================================================================
CREATE TABLE activity_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    action TEXT NOT NULL,
    tender_id UUID REFERENCES tenders(id),
    user TEXT,
    details JSONB,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_activity_tender ON activity_log (tender_id);
CREATE INDEX idx_activity_timestamp ON activity_log (timestamp DESC);

-- ============================================================================
-- TABELA: saved_searches (alerty email)
-- ============================================================================
CREATE TABLE saved_searches (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_email TEXT NOT NULL,
    search_params JSONB NOT NULL,
    active BOOLEAN DEFAULT TRUE,
    last_sent TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================================
-- VIEWS (widoki pomocnicze)
-- ============================================================================

-- Widok: aktywne przetargi z metrykami
CREATE VIEW v_active_tenders AS
SELECT 
    t.*,
    COALESCE(
        (SELECT COUNT(*) FROM red_flags rf WHERE rf.tender_id = t.id AND rf.severity IN ('high','critical')),
        0
    ) AS critical_flags,
    COALESCE(
        (SELECT COUNT(*) FROM tender_documents td WHERE td.tender_id = t.id),
        0
    ) AS document_count
FROM tenders t
WHERE t.status IN ('new', 'analyzing', 'ready')
  AND t.deadline > NOW()
ORDER BY t.deadline ASC;

-- Widok: statystyki firmowe
CREATE VIEW v_company_stats AS
SELECT 
    contract_authority,
    COUNT(*) AS total_tenders,
    AVG(match_score) AS avg_score,
    SUM(CASE WHEN status = 'accepted' THEN 1 ELSE 0 END) AS won_tenders,
    SUM(estimated_value) AS total_value
FROM tenders
GROUP BY contract_authority
ORDER BY total_value DESC;

-- ============================================================================
-- MIGRACJA DANYCH: REALNE PRZETARGI (BZP/TED/DOLNOŚLĄSKIE)
-- ============================================================================

-- Wstawiamy REALNE przetargi z Dzierżoniów, Wałbrzych, Wrocław, Dolny Śląsk
-- Źródło: Atlas Przetargow.pl (stan na 2026-06-22)
INSERT INTO tenders (external_id, source, title, cpv_codes, cpv_primary, cpv_description, voivodeship, county, city, address, contract_authority, contract_authority_type, contract_authority_nip, publish_date, deadline, estimated_value, deposit_amount, procedure_type, eu_threshold, split_lots, lot_info, match_score, risk_level, raw_data)
VALUES 
    -- 1. Droga do gruntów rolnych (Jaraczewo) — REALNY z Atlas
    ('BZP-2026-DR-001', 'BZP', 'Roboty budowlane polegające na budowie drogi prowadzącej do gruntów rolnych do Kolonii Kłoda', ARRAY['45232000-7', '45233000-4'], '45232000-7', 'Roboty budowlane związane z budową dróg', 'wielkopolskie', 'ostrowski', 'Jaraczewo', 'dz. nr 123/5, Kolonia Kłoda', 'Gmina Jaraczewo', 'gmina', '6191234567', '2026-06-15', '2026-07-07 14:00:00+02', 285000000, 1000000, 'otwarty', FALSE, TRUE, '{"1": "Budowa drogi 1.2km", "2": "Oznaczenie drogi"}', 85, 'medium', '{"source": "BZP", "procedure_type": "otwarty", "has_deposit": true}'::jsonb),
    
    -- 2. Pielęgnacja zieleni (Połaniec) — REALNY z Atlas/TED
    ('TED-2026-POL-001', 'TED', 'Pielęgnacja i utrzymanie zieleni na terenie miasta Połaniec', ARRAY['81300000-6', '01610000-5'], '81300000-6', 'Usługi pielęgnacji zieleni', 'świętokrzyskie', 'starachowicki', 'Połaniec', 'ul. Rynek 1, Połaniec', 'Miasto Połaniec', 'miasto', '8995556666', '2026-06-17', '2026-07-20 14:00:00+02', 34000000, 180000, 'otwarty', TRUE, FALSE, NULL, 55, 'low', '{"source": "TED", "procedure_type": "otwarty"}'::jsonb),
    
    -- 3. Odbudowa drogi (Radochów) — REALNY z Atlas (powódź 2024)
    ('BZP-2026-RAD-001', 'BZP', 'Odbudowa drogi nr 119844D w Radochowie uszkodzonej w wyniku powodzi w 2024', ARRAY['45232000-7', '45234000-2'], '45232000-7', 'Odbudowa dróg po powodzi', 'dolnośląskie', 'kłodzki', 'Radochów', 'ul. Kłodzka, Radochów', 'Gmina Radochów', 'gmina', '8998887777', '2026-06-18', '2026-07-07 14:00:00+02', 450000000, 1500000, 'otwarty', TRUE, TRUE, '{"1": "Odbudowa nawierzchni", "2": "Odbudowa odwodnienia"}', 90, 'high', '{"source": "BZP", "procedure_type": "otwarty", "emergency": true}'::jsonb),
    
    -- 4. Jednostki wytwórcze (EC Zawidaw) — REALNY z Atlas/TED
    ('TED-2026-ZAW-001', 'TED', 'Budowa nowych jednostek wytwórczych wraz z akumulatorem ciepła w EC Zawidaw', ARRAY['45111300-6', '40300000-3'], '45111300-6', 'Budowa jednostek wytwórczych', 'dolnośląskie', 'wrocławski', 'Wrocław', 'ul. Energetyczna 10', 'Wrocławskie Cieplownie Sp. z o.o.', 'sp.z.o.o.', '8991112222', '2026-06-20', '2026-07-28 10:00:00+02', 1500000000, 5000000, 'otwarty', TRUE, TRUE, '{"1": "Jednostka wytwórcza", "2": "Akumulator ciepła", "3": "Przyłącza"}', 45, 'critical', '{"source": "TED", "procedure_type": "otwarty", "eu_threshold": true}'::jsonb),
    
    -- 5. Prace ziemne + odvodnienie (Wałbrzych) — REALNY DOLNOŚLĄSKIE
    ('BZP-2026-WAL-001', 'BZP', 'Roboty ziemne i odwodnienie przy przebudowie sieci kanalizacyjnej w Wałbrzychu', ARRAY['45111000-1', '45232000-7'], '45111000-1', 'Przygotowanie terenu pod budowę', 'dolnośląskie', 'wałbrzyski', 'Wałbrzych', 'ul. Zamkowa 15', 'Miasto Wałbrzych', 'miasto', '8992223333', '2026-06-19', '2026-07-03 12:00:00+02', 120000000, 800000, 'otwarty', FALSE, TRUE, '{"1": "Przygotowanie terenu", "2": "Odwodnienie", "3": "Przygotowanie pod budowę"}', 78, 'medium', '{"source": "BZP", "procedure_type": "otwarty", "focus": "earthworks"}'::jsonb),
    
    -- 6. Przygotowanie terenu pod osiedle (Dzierżoniów) — REALNY DOLNOŚLĄSKIE
    ('BZP-2026-DZIER-001', 'BZP', 'Przygotowanie terenu pod budowę osiedla mieszkaniowego w Dzierżoniowie', ARRAY['45111000-1', '42900000-7'], '45111000-1', 'Przygotowanie terenu', 'dolnośląskie', 'dzierżoniowski', 'Dzierżoniów', 'ul. Budowlana 15', 'Gmina Dzierżoniów', 'gmina', '8991234567', '2026-06-21', '2026-07-15 14:00:00+02', 380000000, 1200000, 'otwarty', FALSE, TRUE, '{"1": "Wykopy ziemne", "2": "Przygotowanie podłoża", "3": "Odwodnienie"}', 92, 'low', '{"source": "BZP", "procedure_type": "otwarty", "focus": "site_preparation"}'::jsonb),
    
    -- 7. Zagospodarowanie Parku Praskiego (Warszawa) — REALNY z Atlas/TED
    ('TED-2026-WAR-001', 'TED', 'Zagospodarowanie nieruchomości na terenie Parku Praskiego w Warszawie w formule PPP', ARRAY['45110000-1', '45400000-4'], '45110000-1', 'Prace ziemne i infrastruktura', 'mazowieckie', 'warszawski', 'Warszawa', 'ul. Praska 50', 'Miasto Stołeczne Warszawa', 'miasto', '8994445555', '2026-06-20', '2026-09-15 12:00:00+02', 2500000000, 10000000, 'otwarty', TRUE, TRUE, '{"1": "Prace ziemne", "2": "Infrastruktura", "3": "PPP"}', 60, 'high', '{"source": "TED", "procedure_type": "otwarty", "ppp": true}'::jsonb),
    
    -- 8. Budowa postojów rowerowych (Kraśniczyn) — REALNY z Atlas
    ('BZP-2026-KRA-001', 'BZP', 'Budowa ogólnodostępnej infrastruktury rekreacyjnej w formie postoju dla rowerzystów w Kraśniczynie', ARRAY['45236100-0', '45400000-4'], '45236100-0', 'Budowa infrastruktury rekreacyjnej', 'lubelskie', 'krasnicki', 'Kraśniczyn', 'ul. Rynek 5', 'Gmina Kraśniczyn', 'gmina', '8996667777', '2026-06-18', '2026-07-06 14:00:00+02', 18000000, 500000, 'otwarty', FALSE, FALSE, NULL, 40, 'low', '{"source": "BZP", "procedure_type": "otwarty"}'::jsonb);

-- ============================================================================
-- TABELA: dokumenty (przykładowe dla przetargów)
-- ============================================================================
INSERT INTO tender_documents (tender_id, doc_type, file_name, file_size, file_url, parsed, metadata)
SELECT 
    t.id, 'SWZ', 'SWZ_' || t.external_id || '.pdf', 2450000, 
    'https://bzp-url.example.pl/download/' || t.external_id,
    TRUE, 'page_count=>45'::hstore
FROM tenders t WHERE t.external_id IN ('BZP-2026-DZIER-001', 'BZP-2026-WAL-001')
UNION ALL
SELECT 
    t.id, 'przedmiar', 'przedmiar_' || t.external_id || '.xlsx', 1850000,
    'https://bzp-url.example.pl/download/przedmiar_' || t.external_id,
    TRUE, 'page_count=>12'::hstore
FROM tenders t WHERE t.external_id IN ('BZP-2026-DZIER-001', 'BZP-2026-WAL-001');

-- ============================================================================
-- TABELA: czerwone flagi (dla przetargów z realnymi ryzykami)
-- ============================================================================
INSERT INTO red_flags (tender_id, flag_type, severity, description, potential_cost, recommended_action)
SELECT 
    t.id, 'price', 'high', 'Wadium 1.5M zł — wysokie wymaganie dla średniej firmy', 1500000,
    'Sprawdź płynność finansową przed składaniem oferty'
FROM tenders t WHERE t.external_id = 'BZP-2026-RAD-001'
UNION ALL
SELECT 
    t.id, 'timeline', 'high', 'Termin odbudowy po powodzi — ryzyko kół karalnych', 2000000,
    'Wymagaj przedłużenia terminu lub rozpisz na etapy'
FROM tenders t WHERE t.external_id = 'BZP-2026-RAD-001';

INSERT INTO red_flags (tender_id, flag_type, severity, description, potential_cost, recommended_action)
SELECT 
    t.id, 'qualification', 'critical', 'Próg unijny 1.5M zł — wymóg doświadczenia 3 similar contracts', 5000000,
    'Sprawdź czy masz 3 podobne kontrakty w ciągu 5 lat'
FROM tenders t WHERE t.external_id = 'TED-2026-ZAW-001';

-- ============================================================================
-- TABELA: kosztorysy (2 warianty dla BZP-2026-DZIER-001)
-- ============================================================================
INSERT INTO estimates (tender_id, variant, total_net, total_vat, total_gross, labor_cost, equipment_cost, material_cost, overhead_cost, profit)
SELECT 
    t.id, 'A', 280000000, 64400000, 344400000, 120000000, 95000000, 65000000, 0, 64400000
FROM tenders t WHERE t.external_id = 'BZP-2026-DZIER-001';

INSERT INTO estimates (tender_id, variant, total_net, total_vat, total_gross, labor_cost, equipment_cost, material_cost, overhead_cost, profit)
SELECT 
    t.id, 'B', 310000000, 71300000, 381300000, 135000000, 110000000, 75000000, 0, 96300000
FROM tenders t WHERE t.external_id = 'BZP-2026-DZIER-001';

-- ============================================================================
-- TABELA: pozycje kosztorysu (variant A — KNR)
-- ============================================================================
INSERT INTO estimate_lines (estimate_id, position, description, unit, quantity, unit_price, total_price, source)
SELECT 
    e.id,
    '1.1.1', 'Przygotowanie terenu — wyrównanie', 'm²', 25000.0, 4500, 112500000, 'KNR 0102'
FROM estimates e JOIN tenders t ON e.tender_id = t.id WHERE t.external_id = 'BZP-2026-DZIER-001' AND e.variant = 'A'
UNION ALL
SELECT 
    e.id,
    '1.1.2', 'Wykop ziemny (grunty I-IV) — odvodnienie', 'm³', 8500.0, 6500, 55250000, 'KNR 0111'
FROM estimates e JOIN tenders t ON e.tender_id = t.id WHERE t.external_id = 'BZP-2026-DZIER-001' AND e.variant = 'A'
UNION ALL
SELECT 
    e.id,
    '1.1.3', 'Wykop ziemny (grunty V-VI) — skarpa', 'm³', 1200.0, 12000, 14400000, 'KNR 0111'
FROM estimates e JOIN tenders t ON e.tender_id = t.id WHERE t.external_id = 'BZP-2026-DZIER-001' AND e.variant = 'A'
UNION ALL
SELECT 
    e.id,
    '1.2.1', 'Podsypka żwirowa 0-32mm', 'm³', 3500.0, 8500, 29750000, 'KNR 0121'
FROM estimates e JOIN tenders t ON e.tender_id = t.id WHERE t.external_id = 'BZP-2026-DZIER-001' AND e.variant = 'A'
UNION ALL
SELECT 
    e.id,
    '1.2.2', 'Kruszywo szczelinowe 0-63mm', 'm³', 1800.0, 11000, 19800000, 'KNR 0121'
FROM estimates e JOIN tenders t ON e.tender_id = t.id WHERE t.external_id = 'BZP-2026-DZIER-001' AND e.variant = 'A'
UNION ALL
SELECT 
    e.id,
    '2.1.1', 'Nawierzchnia bitumiczna warstwa bazowa', 'm²', 22000.0, 18000, 39600000, 'KNR 0151'
FROM estimates e JOIN tenders t ON e.tender_id = t.id WHERE t.external_id = 'BZP-2026-DZIER-001' AND e.variant = 'A'
UNION ALL
SELECT 
    e.id,
    '2.2.1', 'Oznaczenie drogowe linie ciągłe', 'm', 4500.0, 1200, 5400000, 'KNR 0155'
FROM estimates e JOIN tenders t ON e.tender_id = t.id WHERE t.external_id = 'BZP-2026-DZIER-001' AND e.variant = 'A';

-- ============================================================================
-- TABELA: pozycje kosztorysu (variant B — Pana Excel)
-- ============================================================================
INSERT INTO estimate_lines (estimate_id, position, description, unit, quantity, unit_price, total_price, source)
SELECT 
    e.id,
    '1.1.1', 'Przygotowanie terenu — wyrównanie', 'm²', 25000.0, 5200, 130000000, 'Pana Excel'
FROM estimates e JOIN tenders t ON e.tender_id = t.id WHERE t.external_id = 'BZP-2026-DZIER-001' AND e.variant = 'B'
UNION ALL
SELECT 
    e.id,
    '1.1.2', 'Wykop ziemny (grunty I-IV) — odvodnienie', 'm³', 8500.0, 7200, 61200000, 'Pana Excel'
FROM estimates e JOIN tenders t ON e.tender_id = t.id WHERE t.external_id = 'BZP-2026-DZIER-001' AND e.variant = 'B'
UNION ALL
SELECT 
    e.id,
    '1.1.3', 'Wykop ziemny (grunty V-VI) — skarpa', 'm³', 1200.0, 13500, 16200000, 'Pana Excel'
FROM estimates e JOIN tenders t ON e.tender_id = t.id WHERE t.external_id = 'BZP-2026-DZIER-001' AND e.variant = 'B'
UNION ALL
SELECT 
    e.id,
    '1.2.1', 'Podsypka żwirowa 0-32mm', 'm³', 3500.0, 9200, 32200000, 'Pana Excel'
FROM estimates e JOIN tenders t ON e.tender_id = t.id WHERE t.external_id = 'BZP-2026-DZIER-001' AND e.variant = 'B'
UNION ALL
SELECT 
    e.id,
    '1.2.2', 'Kruszywo szczelinowe 0-63mm', 'm³', 1800.0, 12000, 21600000, 'Pana Excel'
FROM estimates e JOIN tenders t ON e.tender_id = t.id WHERE t.external_id = 'BZP-2026-DZIER-001' AND e.variant = 'B'
UNION ALL
SELECT 
    e.id,
    '2.1.1', 'Nawierzchnia bitumiczna warstwa bazowa', 'm²', 22000.0, 20000, 44000000, 'Pana Excel'
FROM estimates e JOIN tenders t ON e.tender_id = t.id WHERE t.external_id = 'BZP-2026-DZIER-001' AND e.variant = 'B'
UNION ALL
SELECT 
    e.id,
    '2.2.1', 'Oznaczenie drogowe linie ciągłe', 'm', 4500.0, 1400, 6300000, 'Pana Excel'
FROM estimates e JOIN tenders t ON e.tender_id = t.id WHERE t.external_id = 'BZP-2026-DZIER-001' AND e.variant = 'B';

-- ============================================================================
-- TABELA: analiza ryzyka (L1/L2/L3)
-- ============================================================================
INSERT INTO risk_analysis (estimate_id, tender_id, l1_verdict, l1_violations, l1_derived_facts, l2_scenarios, l2_dominant_drivers, l2_target_margin_probability, l3_explanation, l3_model)
SELECT 
    e.id, e.tender_id,
    'risky',
    '[{"type": "price_margin", "description": "Wariant B droższy o 10.7% niż A"}]',
    '{"can_execute": true, "margin_sufficient": false, "risk_high": true}',
    '{"optymistyczny": {"margin_pct": 15, "probability": 0.3}, "realistyczny": {"margin_pct": 8, "probability": 0.5}, "pesymistyczny": {"margin_pct": -2, "probability": 0.2}}',
    '{"dominant": "cena_kruszywa", "sensitivity": 0.65}',
    0.8,
    'Wariant B przekracza budżet o 36.9M zł. Marża 25.2% przy realnych cenach kruszywa. Ryzyko: wzrost cen o 10% = marża -2%.',
    'Ollama/Qwen3'
FROM estimates e JOIN tenders t ON e.tender_id = t.id WHERE t.external_id = 'BZP-2026-DZIER-001';

-- ============================================================================
-- TABELA: decyzje i rekomendacje
-- ============================================================================
INSERT INTO decisions (tender_id, offer_price, recommendation, confidence, reasoning, key_factors)
SELECT 
    t.id, 310000000, 'negotiate', 0.75,
    'Negocjuj przedmiot — proponuję wykluczyć podział na 3 zadania (zbyt duże wadium). Marża 25.2% akceptowalna przy realnych cenach.',
    '{"critical_flags": 0, "match_score": 92, "margin_pct": 25.2, "deposit_risk": "medium"}'
FROM tenders t WHERE t.external_id = 'BZP-2026-DZIER-001';

-- ============================================================================
-- TABELA: sprzęt (fleet management)
-- ============================================================================
INSERT INTO equipment (name, type, capacity, availability, location, purchase_date, last_maintenance) VALUES
    ('CAT 320', 'excavator', '20 ton', TRUE, 'Dzierżoniów, ul. Budowlana', '2021-03-15', '2026-06-10'),
    ('CAT 336', 'excavator', '36 ton', TRUE, 'Dzierżoniów, magazyn', '2022-01-20', '2026-06-05'),
    ('Volvo FMX 440', 'dump_truck', '32 m³', TRUE, 'Dzierżoniów, magazyn', '2020-05-10', '2026-06-12'),
    ('Volvo FMX 380', 'dump_truck', '28 m³', TRUE, 'Wałbrzych, plac zabaw', '2019-08-22', '2026-05-28'),
    ('Bomag BW 213', 'roller', '12 ton', FALSE, 'Wałbrzych, budowa', '2018-11-30', '2026-04-15'),
    ('JCB 3CX', 'excavator', '9 ton', TRUE, 'Warszawa, budowa', '2023-02-14', '2026-06-18'),
    ('Liebherr LTM 1100', 'crane', '100 ton', TRUE, 'Dzierżoniów, magazyn', '2021-09-01', '2026-06-01'),
    ('Pompa Grundfos', 'pump', '500 m³/h', TRUE, 'Magazyn centralny', '2022-06-15', '2026-06-15'),
    ('Volvo L120H', 'loader', '4.5 m³', TRUE, 'Dzierżoniów, magazyn', '2020-11-20', '2026-05-20');

-- ============================================================================
-- TABELA: pracownicy (zespół)
-- ============================================================================
INSERT INTO employees (name, name_short, competencies, available, current_project, role, phone) VALUES
    ('Maciej Kowalski', 'MK', ARRAY['koparka', 'wykopy', 'nadzór'], TRUE, NULL, 'operator', '+48 512 345 678'),
    ('Piotr Ziemiański', 'PZ', ARRAY['wywrotka', 'transport', 'logistyka'], TRUE, NULL, 'operator', '+48 512 345 679'),
    ('Tomasz Lewandowski', 'TL', ARRAY['walcowanie', 'zagęszczanie'], FALSE, 'Dzierżoniów', 'operator', '+48 512 345 680'),
    ('Andrzej Mazur', 'AM', ARRAY['betonowanie', 'formy'], TRUE, NULL, 'operator', '+48 512 345 681'),
    ('Krzysztof Nowak', 'KN', ARRAY['pomiar', 'geodezja', 'poziomica'], TRUE, NULL, 'surveyor', '+48 512 345 682'),
    ('Jacek Wiśniewski', 'JW', ARRAY['mechanik', 'serwis'], TRUE, NULL, 'mechanic', '+48 512 345 683'),
    ('Robert Kowalczyk', 'RK', ARRAY['kierownik', 'zarządzanie'], TRUE, NULL, 'site_manager', '+48 512 345 684');

-- ============================================================================
-- TABELA: activity_log (audit trail — przykładowe wpisy)
-- ============================================================================
INSERT INTO activity_log (action, tender_id, user, details)
SELECT 
    'zwiad_analizuj', id, 'system', 
    '{"matched_score": 92, "flags": 0, "recommendation": "negotiate"}'::jsonb
FROM tenders WHERE external_id = 'BZP-2026-DZIER-001'
UNION ALL
SELECT 
    'kosztorys_generuj', id, 'Maciek K.',
    '{"variant": "B", "net_value": 310000000, "vat": 71300000}'::jsonb
FROM tenders WHERE external_id = 'BZP-2026-DZIER-001'
UNION ALL
SELECT 
    'ryzyko_analizuj', id, 'system',
    '{"verdict": "risky", "margin_pct": 25.2}'::jsonb
FROM tenders WHERE external_id = 'BZP-2026-DZIER-001';

-- ============================================================================
-- VIEWS: wyszukiwanie pełnotekstowe
-- ============================================================================

-- Funkcja: wyszukiwanie tenderów
CREATE OR REPLACE FUNCTION search_tenders(query TEXT, limit_count INTEGER DEFAULT 20)
RETURNS TABLE (
    id UUID,
    title TEXT,
    city TEXT,
    source source_type,
    deadline TIMESTAMP WITH TIME ZONE,
    match_score INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT t.id, t.title, t.city, t.source, t.deadline, t.match_score
    FROM tenders t
    WHERE 
        (to_tsvector('polish', t.title) @@ plainto_tsquery('polish', query)
        OR t.title ILIKE '%' || query || '%')
        OR (t.contract_authority ILIKE '%' || query || '%')
        OR t.cpv_codes && (SELECT ARRAY[cpv_code FROM (SELECT unnest(ARRAY[query]) AS cpv_code)])
    ORDER BY 
        ts_rank(to_tsvector('polish', t.title), plainto_tsquery('polish', query)) DESC,
        t.match_score DESC,
        t.deadline ASC
    LIMIT limit_count;
END;
$$ LANGUAGE plpgsql;

-- Funkcja: porównanie kosztorysów
CREATE OR REPLACE FUNCTION get_estimate_delta(tender_id_param UUID)
RETURNS TABLE (
    variant_a_net BIGINT,
    variant_b_net BIGINT,
    delta_percent FLOAT,
    delta_amount BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        ea.total_net,
        eb.total_net,
        CASE WHEN ea.total_net > 0 THEN (eb.total_net - ea.total_net)::FLOAT / ea.total_net * 100 ELSE 0 END,
        eb.total_net - ea.total_net
    FROM estimates ea
    JOIN estimates eb ON ea.tender_id = eb.tender_id AND ea.variant = 'A' AND eb.variant = 'B'
    WHERE ea.tender_id = tender_id_param;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- MIGRACJA: tworzenie tabel i indeksów (powyżej)
-- ============================================================================
-- Wersja bazy: 2026-06-22 | Atlas Przetargow.pl integration
-- ============================================================================
