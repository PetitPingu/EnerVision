-- Crée un compte "lecture seule" restreint à SITE001 uniquement (voir
-- apps/core_api/presentation/api.py:_permitted_site_ids pour comment ce
-- rôle est filtré, par opposition à admin qui voit tout sans ligne dans
-- user_sites).
--
-- Identifiants : viewer@enervision.com / changeme1234 (role=viewer) — à
-- changer après le premier login en environnement réel.
--
-- Idempotent : peut être rejoué sans risque à chaque apply Terraform.
-- Nécessite que seed_sites.sql ait déjà été appliqué (FK sur site_id).
--
-- Usage :
--   psql "$DATABASE_URL" -f seeds/seed_viewer_user.sql
--
-- Hash bcrypt de "changeme1234" (généré avec la même méthode que
-- apps/core_api/infrastructure/auth.py:hash_password, cf. bcrypt.hashpw).
INSERT INTO enervision.users (id, email, password_hash, role)
VALUES (
    gen_random_uuid(),
    'viewer@enervision.com',
    '$2b$12$azjyZMnUOyhsxNsPBUOTYO117a4WArQI.Aj1wa5EJsApcOOGCOFci',
    'viewer'
)
ON CONFLICT (email) DO NOTHING;

INSERT INTO enervision.user_sites (user_id, site_id)
SELECT id, 'SITE001' FROM enervision.users WHERE email = 'viewer@enervision.com'
ON CONFLICT (user_id, site_id) DO NOTHING;
