-- Init du Postgres de PARITÉ PROD (docker-compose.dev.yml).
--
-- La prod fait tourner l'app avec un rôle DÉDIÉ et NON-superuser (`cybervault`,
-- rolsuper=false, vérifié en direct sur RDS). En local, un Postgres natif tourne
-- en `postgres` (superuser) : une migration qui exigerait un privilège superuser
-- (CREATE EXTENSION non whitelistée, ALTER SYSTEM, etc.) passerait chez toi et
-- casserait en prod. On recrée donc ici le même garde-fou de privilèges.
--
-- Ce script s'exécute une seule fois, à l'initialisation du volume, APRÈS que
-- l'entrypoint a créé la base POSTGRES_DB (=cybervault) en owner postgres.

-- Rôle applicatif identique à la prod : login, NON-superuser.
CREATE ROLE cybervault WITH LOGIN PASSWORD 'password' NOSUPERUSER NOCREATEROLE NOCREATEDB;

-- Il possède la base et le schéma public -> il peut créer les tables (les
-- migrations tournent sous ce rôle), mais reste NON-superuser.
ALTER DATABASE cybervault OWNER TO cybervault;
GRANT ALL PRIVILEGES ON DATABASE cybervault TO cybervault;

\connect cybervault
ALTER SCHEMA public OWNER TO cybervault;
GRANT ALL ON SCHEMA public TO cybervault;
