#!/bin/bash

# Параметры VM
FOLDER_ID="b1gutjnjpk65slujeu1t"            # ID каталога
ZONE="ru-central1-a"                        # Зона доступности
VM_NAME="yk-hse-bot-2"                      # Имя VM
SUBNET_ID=e9bj2i1qrd4fvlqjq8ct              # ID подсети
SERVICE_ACCOUNT_ID="ajeoqjp8ojffpl7gmolk"   # ID сервисного аккаунта (с правами на чтение образов из Container Registry)
PLATFORM_ID="standard-v3"                   # Платформа
CORES=2                                     # Количество ядер
MEMORY=4GB                                  # Объем памяти в ГБ
DISK_SIZE=30                                # Размер диска в ГБ
DOCKER_COMPOSE_PATH="./.docker-compose.cloud.yml"
SSH_KEY_PATH=~/.ssh/id_ed25519.pub

# Парсинг аргументов
RESET=false
STOP=false
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --reset) RESET=true ;;
        --stop) STOP=true ;;
        *) echo "Unknown parameter: $1"; exit 1 ;;
    esac
    shift
done

# Проверка наличия VM с таким же именем
if yc compute instance get ${VM_NAME} > /dev/null 2>&1; then
    # Получение статуса VM
    STATUS=$(yc compute instance get ${VM_NAME} --format=json | jq -r '.status')
    if [ "$STOP" = true ]; then
        if [ "$STATUS" = "RUNNING" ]; then
            echo "Stopping VM ${VM_NAME}..."
            yc compute instance stop ${VM_NAME} --async
            echo "VM ${VM_NAME} is stopping."
            exit 0
        else
            echo "VM ${VM_NAME} is not running. Current status: $STATUS"
            exit 0
        fi
    fi
    if [ "$STATUS" = "RUNNING" ] && [ "$RESET" = false ]; then
        echo "VM ${VM_NAME} is already running. No action needed."
        # Получение внешнего IP
        EXTERNAL_IP=$(yc compute instance get ${VM_NAME} --format=json | jq -r '.network_interfaces[0].primary_v4_address.one_to_one_nat.address')
        echo "VM external IP: ${EXTERNAL_IP}"
        exit 0
    else
        echo "VM ${VM_NAME} is in status: $STATUS. Deleting..."
        yc compute instance delete ${VM_NAME} --async
        # Ожидание удаления
        while true; do
            STATUS=$(yc compute instance get ${VM_NAME} --format=json 2>/dev/null | jq -r '.status')
            if [ -z "$STATUS" ]; then
                echo "VM ${VM_NAME} successfully deleted."
                break
            elif [ "$STATUS" = "DELETING" ]; then
                echo "Waiting for VM ${VM_NAME} to be deleted..."
                sleep 15
            else
                echo "Error deleting VM ${VM_NAME}. Status: $STATUS"
                exit 1
            fi
        done
    fi
fi

# Создание VM с Container Solution
yc compute instance create-with-container \
  --name ${VM_NAME} \
  --zone ${ZONE} \
  --cores ${CORES} \
  --memory ${MEMORY} \
  --ssh-key ${SSH_KEY_PATH} \
  --platform-id ${PLATFORM_ID} \
  --create-boot-disk size=${DISK_SIZE} \
  --network-interface subnet-id=${SUBNET_ID},nat-ip-version=ipv4 \
  --service-account-id ${SERVICE_ACCOUNT_ID} \
  --docker-compose-file ${DOCKER_COMPOSE_PATH}
#   --preemptible


# Проверка статуса создания
echo "Waiting for VM creation..."
while true; do
    STATUS=$(yc compute instance get ${VM_NAME} --format=json | jq -r '.status')
    if [ "$STATUS" = "RUNNING" ]; then
        echo "VM successfully created and running"
        break
    elif [ "$STATUS" = "ERROR" ]; then
        echo "Error creating VM"
        exit 1
    fi
    sleep 5
done

# Получение внешнего IP
EXTERNAL_IP=$(yc compute instance get ${VM_NAME} --format=json | jq -r '.network_interfaces[0].primary_v4_address.one_to_one_nat.address')
echo "VM external IP: ${EXTERNAL_IP}"
