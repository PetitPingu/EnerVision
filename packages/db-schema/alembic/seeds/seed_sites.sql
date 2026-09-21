-- Crée les 7 sites de démo (voir docs/archi_database.md, table SITES).
--
-- Idempotent (ON CONFLICT sur site_id, la clé primaire) : peut être
-- rejoué sans risque à chaque apply Terraform.
--
-- Usage :
--   psql "$DATABASE_URL" -f seeds/seed_sites.sql
INSERT INTO enervision.sites (site_id, site_name, site_type, location, capacity_kw, status)
VALUES
    ('SITE001', 'Bureau Paris La Défense', 'office', 'Paris, France', 200, 'active'),
    ('SITE002', 'Usine Lyon Vénissieux', 'factory', 'Lyon, France', 1000, 'active'),
    ('SITE003', 'Data Center Marseille', 'datacenter', 'Marseille, France', 800, 'active'),
    ('SITE004', 'Centre Commercial Lille', 'retail', 'Lille, France', 400, 'active'),
    ('SITE005', 'Hôpital Toulouse Purpan', 'hospital', 'Toulouse, France', 600, 'active'),
    ('SITE006', 'Bureau Bordeaux Centre', 'office', 'Bordeaux, France', 180, 'active'),
    ('SITE007', 'Usine Nantes Rezé', 'factory', 'Nantes, France', 950, 'active')
ON CONFLICT (site_id) DO NOTHING;
