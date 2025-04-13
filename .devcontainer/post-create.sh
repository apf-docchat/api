#!/usr/bin/env bash

# Wait for Docker daemon to start
while ! docker info > /dev/null 2>&1; do
    echo "Waiting for Docker daemon to start..."
    sleep 10
done

# Pause for a bit more for good measure (MySQL loading fails otherwise)
echo "Waiting for Docker daemon to start..."
sleep 10

# Setting up Docker data dirs
echo "Setting up directories..."
mkdir -p $HOME/mounted_data/{redis,mongodb,mysql}

# Install Redis
echo "Installing Redis..."
docker run -q -d --restart=unless-stopped --name redis \
--user 1000:1000 \
-v $HOME/mounted_data/redis:/data \
-p 127.0.0.1:6379:6379 \
redis:7-alpine

# Install MongoDB
echo "Installing MongoDB..."
docker run -q -d --restart=unless-stopped --name mongodb \
--user 1000:1000 \
-v $HOME/mounted_data/mongodb:/data/db \
-v $(pwd)/.devcontainer/mongo-initdb.d:/docker-entrypoint-initdb.d:ro \
-e MONGO_INITDB_ROOT_USERNAME=root \
-e MONGO_INITDB_ROOT_PASSWORD=root \
-p 127.0.0.1:27017:27017 \
mongo:7

# Install MySQL
echo "Installing MySQL..."
docker run -q -d --restart=unless-stopped --name mysql \
--user 1000:1000 \
-v $HOME/mounted_data/mysql:/var/lib/mysql \
-v $(pwd)/.devcontainer/mysql-initdb.d:/docker-entrypoint-initdb.d:ro \
-e MYSQL_ROOT_PASSWORD=root \
-e MYSQL_DATABASE=app \
-e MYSQL_USER=app_user \
-e MYSQL_PASSWORD=app_user \
-p 127.0.0.1:3306:3306 \
mysql:8

# Install bashup/dotenv
sudo curl -sL https://raw.githubusercontent.com/bashup/dotenv/master/dotenv -o /usr/local/bin/dotenv
sudo chmod +x /usr/local/bin/dotenv

# Create .env
if [ ! -f .env ]; then
  echo  "Creating .env..."
  cp .env.example .env
fi

# Update values in .env
dotenv -f .env set FLASK_SECRET_KEY=$(openssl rand -hex 32)
dotenv -f .env set FLASK_DEBUG=1
dotenv -f .env set APP_LOG_LEVEL=debug

workspace_dir="$(dirname "$PWD")"

# Create app data dirs
echo "Creating app data directories..."
mkdir -p "$workspace_dir/data/datasource-uploaded/org3"

# Checkout pw-vectorizer
git clone https://github.com/processwiz/pw-vectoriser.git "$workspace_dir/pw-vectoriser"

echo "Done!"
