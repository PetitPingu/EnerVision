-- Crée le compte admin par défaut (voir docs/seq_auth_token.md pour le
-- flux de login/JWT côté core_api).
--
-- Identifiants : admin@enervision.com / changeme1234 (role=admin) — à
-- changer après le premier login en environnement réel.
--
-- Idempotent (ON CONFLICT sur l'email, contraint UNIQUE) : peut être
-- rejoué sans risque à chaque apply Terraform.
--
-- Usage :
--   psql "$DATABASE_URL" -f seeds/seed_admin_user.sql
--
-- Hash bcrypt de "changeme1234" (généré avec la même méthode que
-- apps/core_api/infrastructure/auth.py:hash_password, cf. bcrypt.hashpw).
INSERT INTO enervision.users (id, email, password_hash, role)
VALUES (
    gen_random_uuid(),
    'admin@enervision.com',
    '$2b$12$oYr9lCRSSKObKYkFuCYtEubIDcOnTGQeDXQkECPGGPedv19N.y4fa',
    'admin'
)
ON CONFLICT (email) DO NOTHING;
