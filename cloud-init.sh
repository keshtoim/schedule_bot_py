#!/bin/bash
# Первичная настройка сервера под бота. Вставляется в поле «Cloud-init» при
# создании сервера (Ubuntu 24.04). Ставит swap + Docker и клонирует проект.
# .env не трогает — там секреты, заполняется вручную после.
#
# Лог выполнения: /var/log/cloud-init-output.log
set -eux

REPO=https://github.com/keshtoim/schedule_bot_py.git
DIR=/opt/schedule_bot_py

# --- swap 2 ГБ: чтобы 1 ГБ RAM хватало на сборку образа и разбор xlsx ---
if ! swapon --show | grep -q '/swapfile'; then
  fallocate -l 2G /swapfile
  chmod 600 /swapfile
  mkswap /swapfile
  swapon /swapfile
  echo '/swapfile none swap sw 0 0' >>/etc/fstab
  echo 'vm.swappiness=10' >/etc/sysctl.d/99-swap.conf
  sysctl -p /etc/sysctl.d/99-swap.conf
fi

# --- Docker + compose ---
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y git curl
curl -fsSL https://get.docker.com | sh
systemctl enable --now docker

# --- проект ---
git clone "$REPO" "$DIR"
cd "$DIR"
cp .env.example .env

cat <<'MSG'

=========================================================
  Docker и проект установлены. Осталось:

    cd /opt/schedule_bot_py
    nano .env          # BOT_TOKEN, COLLEGE_PAGE_URL, OWNER_CHAT_ID
    docker compose up -d --build
    docker compose logs -f

  Потом: напиши боту /id и впиши число в OWNER_CHAT_ID,
  затем  docker compose up -d
=========================================================
MSG
