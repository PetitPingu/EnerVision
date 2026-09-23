# Migrations Alembic appliquées une seule fois avant core_api et recommendation
# (aligné sur docker-compose service migrate). Leur propre "alembic upgrade head"
# au démarrage reste un no-op sûr une fois le schéma à head.
#
# terraform_data + docker run --rm bloque jusqu'à la fin de la migration, contrairement
# à depends_on sur un docker_container (création seulement, pas fin de job).

resource "terraform_data" "db_migrate" {
  input = {
    schema_hash = local.db_schema_source_hash
    image       = local.app_images.core_api
  }

  depends_on = [
    docker_container.database,
    docker_image.core_api,
  ]

  provisioner "local-exec" {
    command = "docker run --rm --network ${docker_network.app_network.name} -e DATABASE_URL=\"${local.database_url}\" ${local.app_images.core_api} sh -c \"sh /packages/db-schema/wait-for-postgres.sh && alembic -c /packages/db-schema/alembic.ini upgrade head\""
  }
}
