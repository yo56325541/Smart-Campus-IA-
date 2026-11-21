-- ==============================================================================
-- SmartCampus AI – Script d'initialisation PostgreSQL (Développement & Local)
-- ==============================================================================
-- Exécution (une seule fois en superutilisateur 'postgres') :
--   psql -U postgres -h 127.0.0.1 -p 5433 -f db/setup.sql
--
-- IMPORTANT (SÉCURITÉ PRODUCTION) :
-- En production, ne JAMAIS utiliser le mot de passe par défaut ci-dessous.
-- Spécifiez un mot de passe fort et configurez des droits stricts sans CREATEDB.
-- ==============================================================================

-- 1. Création idempotente du rôle applicatif
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'smartcampus') THEN
        CREATE ROLE smartcampus LOGIN PASSWORD 'smartcampus' CREATEDB;
    ELSE
        ALTER ROLE smartcampus WITH LOGIN PASSWORD 'smartcampus' CREATEDB;
    END IF;
END
$$;

-- 2. Création des bases de données de développement et de test
-- Note: Sous PostgreSQL, CREATE DATABASE ne peut pas s'exécuter dans un bloc transactionnel.
SELECT 'CREATE DATABASE smartcampus OWNER smartcampus ENCODING ''UTF8'''
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'smartcampus')\gexec

SELECT 'CREATE DATABASE smartcampus_test OWNER smartcampus ENCODING ''UTF8'''
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'smartcampus_test')\gexec

-- 3. Configuration des privilèges et extensions sur la base de développement
\connect smartcampus
GRANT ALL PRIVILEGES ON DATABASE smartcampus TO smartcampus;
CREATE EXTENSION IF NOT EXISTS pgcrypto;
-- CREATE EXTENSION IF NOT EXISTS vector; -- Activer quand pgvector sera requis pour le RAG

-- 4. Configuration des privilèges et extensions sur la base de test
\connect smartcampus_test
GRANT ALL PRIVILEGES ON DATABASE smartcampus_test TO smartcampus;
CREATE EXTENSION IF NOT EXISTS pgcrypto;
