#!/bin/bash

echo "Loading environment variables..."
source .env

echo "Creating network..."
docker network create hydra-net

echo "Creating data volume..."
docker volume create hydra-data

echo "Starting the Hydra DB container..."
docker run -d --name hydra-db --network hydra-net --volume hydra-data:/var/lib/postgresql/data \
    -e PGDATA=/var/lib/postgresql/data \
    -e POSTGRES_DB=hydra_db \
    -e POSTGRES_USER=hydra_user \
    -e POSTGRES_PASSWORD="${HYDRA_DB_PASSWORD}" \
    postgres:9.6

echo "Running SQL migrations..."
docker run -it --rm --network hydra-net "${HYDRA_IMAGE}" migrate sql --yes \
    "postgres://hydra_user:${HYDRA_DB_PASSWORD}@hydra-db:5432/hydra_db?sslmode=disable"

echo "Deleting the Hydra DB container..."
docker rm -f hydra-db

echo "Done."
