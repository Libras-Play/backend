#!/bin/bash
set -e

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

AWS_REGION="us-east-1"
CLUSTER="libras-play-dev-cluster"
ALB_DNS="libras-play-dev-alb-1450968088.us-east-1.elb.amazonaws.com"

echo -e "${BLUE}╔══════════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║           SMOKE TEST - LIBRAS PLAY PRODUCTION                           ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════════════════╝${NC}"

# 1. Verificar estado de servicios ECS
echo -e "\n${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}📊 1. Verificando estado de servicios ECS...${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

services=("libras-play-dev-content-service" "libras-play-dev-user-service" "libras-play-dev-ml-service")

for service in "${services[@]}"; do
    echo -e "${BLUE}Servicio: ${service}${NC}"
    
    status=$(aws ecs describe-services \
        --cluster $CLUSTER \
        --services $service \
        --region $AWS_REGION \
        --query 'services[0].[status,runningCount,desiredCount,deployments[0].rolloutState]' \
        --output text)
    
    read -r svc_status running desired rollout <<< "$status"
    
    if [ "$running" == "$desired" ] && [ "$rollout" == "COMPLETED" ]; then
        echo -e "  Status: ${GREEN}✅ $svc_status${NC}"
        echo -e "  Tasks: ${GREEN}$running/$desired RUNNING${NC}"
        echo -e "  Rollout: ${GREEN}$rollout${NC}\n"
    else
        echo -e "  Status: ${YELLOW}⚠️  $svc_status${NC}"
        echo -e "  Tasks: ${YELLOW}$running/$desired RUNNING${NC}"
        echo -e "  Rollout: ${YELLOW}$rollout${NC}\n"
    fi
done

# 2. Verificar ALB Health Checks
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}🏥 2. Verificando Health Checks del ALB...${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

target_groups=$(aws elbv2 describe-target-groups \
    --region $AWS_REGION \
    --query "TargetGroups[?contains(TargetGroupName, 'libras-play-dev')].TargetGroupArn" \
    --output text)

for tg in $target_groups; do
    tg_name=$(aws elbv2 describe-target-groups \
        --target-group-arns $tg \
        --region $AWS_REGION \
        --query 'TargetGroups[0].TargetGroupName' \
        --output text)
    
    echo -e "${BLUE}Target Group: ${tg_name}${NC}"
    
    health=$(aws elbv2 describe-target-health \
        --target-group-arn $tg \
        --region $AWS_REGION \
        --query 'TargetHealthDescriptions[*].[Target.Id,TargetHealth.State,TargetHealth.Reason]' \
        --output text)
    
    if [ -z "$health" ]; then
        echo -e "  ${YELLOW}⚠️  No hay targets registrados${NC}\n"
    else
        while IFS=$'\t' read -r target state reason; do
            if [ "$state" == "healthy" ]; then
                echo -e "  Target: ${target} - ${GREEN}✅ HEALTHY${NC}"
            else
                echo -e "  Target: ${target} - ${RED}❌ ${state}${NC} (${reason})"
            fi
        done <<< "$health"
        echo ""
    fi
done

# 3. Test HTTP Endpoints
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}🌐 3. Probando endpoints HTTP...${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

endpoints=(
    "http://${ALB_DNS}/content/health|Content Service Health"
    "http://${ALB_DNS}/user/health|User Service Health"
    "http://${ALB_DNS}/ml/health|ML Service Health"
)

for endpoint in "${endpoints[@]}"; do
    IFS='|' read -r url name <<< "$endpoint"
    echo -e "${BLUE}Testing: ${name}${NC}"
    echo -e "  URL: ${url}"
    
    response=$(curl -s -o /dev/null -w "%{http_code}" -m 10 "$url" 2>/dev/null || echo "TIMEOUT")
    
    if [ "$response" == "200" ]; then
        echo -e "  ${GREEN}✅ Status: 200 OK${NC}\n"
    elif [ "$response" == "TIMEOUT" ]; then
        echo -e "  ${RED}❌ TIMEOUT (servicio no responde)${NC}\n"
    else
        echo -e "  ${RED}❌ Status: ${response}${NC}\n"
    fi
done

# 4. Verificar CloudWatch Logs (últimos 5 minutos)
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}📝 4. Verificando CloudWatch Logs (últimos 5 min)...${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

log_groups=(
    "/ecs/libras-play-dev/content-service"
    "/ecs/libras-play-dev/user-service"
    "/ecs/libras-play-dev/ml-service"
)

START_TIME=$(($(date +%s) - 300))000  # Últimos 5 minutos
END_TIME=$(date +%s)000

for log_group in "${log_groups[@]}"; do
    service_name=$(echo $log_group | sed 's|/ecs/libras-play-dev/||')
    echo -e "${BLUE}Service: ${service_name}${NC}"
    
    # Buscar errores
    errors=$(aws logs filter-log-events \
        --log-group-name "$log_group" \
        --start-time $START_TIME \
        --end-time $END_TIME \
        --filter-pattern "ERROR" \
        --region $AWS_REGION \
        --query 'events[*].message' \
        --output text 2>/dev/null || echo "")
    
    if [ -z "$errors" ]; then
        echo -e "  ${GREEN}✅ No hay errores en los últimos 5 minutos${NC}\n"
    else
        error_count=$(echo "$errors" | wc -l)
        echo -e "  ${RED}❌ Encontrados ${error_count} errores:${NC}"
        echo "$errors" | head -3
        echo -e "\n"
    fi
done

# 5. Verificar métricas de CloudWatch
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}📊 5. Métricas de servicios ECS...${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

for service in "${services[@]}"; do
    service_short=$(echo $service | sed 's/libras-play-dev-//')
    echo -e "${BLUE}Service: ${service_short}${NC}"
    
    # CPU Utilization (promedio últimos 5 min)
    cpu=$(aws cloudwatch get-metric-statistics \
        --namespace AWS/ECS \
        --metric-name CPUUtilization \
        --dimensions Name=ServiceName,Value=$service Name=ClusterName,Value=$CLUSTER \
        --start-time $(date -u -d '5 minutes ago' +%Y-%m-%dT%H:%M:%S) \
        --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
        --period 300 \
        --statistics Average \
        --region $AWS_REGION \
        --query 'Datapoints[0].Average' \
        --output text 2>/dev/null || echo "N/A")
    
    # Memory Utilization
    mem=$(aws cloudwatch get-metric-statistics \
        --namespace AWS/ECS \
        --metric-name MemoryUtilization \
        --dimensions Name=ServiceName,Value=$service Name=ClusterName,Value=$CLUSTER \
        --start-time $(date -u -d '5 minutes ago' +%Y-%m-%dT%H:%M:%S) \
        --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
        --period 300 \
        --statistics Average \
        --region $AWS_REGION \
        --query 'Datapoints[0].Average' \
        --output text 2>/dev/null || echo "N/A")
    
    if [ "$cpu" != "None" ] && [ "$cpu" != "N/A" ]; then
        cpu_rounded=$(printf "%.1f" $cpu)
        echo -e "  CPU: ${GREEN}${cpu_rounded}%${NC}"
    else
        echo -e "  CPU: ${YELLOW}N/A (sin datos)${NC}"
    fi
    
    if [ "$mem" != "None" ] && [ "$mem" != "N/A" ]; then
        mem_rounded=$(printf "%.1f" $mem)
        echo -e "  Memory: ${GREEN}${mem_rounded}%${NC}\n"
    else
        echo -e "  Memory: ${YELLOW}N/A (sin datos)${NC}\n"
    fi
done

# Resumen final
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ SMOKE TEST COMPLETADO${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

echo -e "\n${YELLOW}📌 Próximos pasos:${NC}"
echo -e "  1. Importa la colección Postman: ${BLUE}tests/smoke-test-production.postman_collection.json${NC}"
echo -e "  2. Ejecuta los tests de API manualmente"
echo -e "  3. Verifica los logs en CloudWatch Console"
echo -e "\n${YELLOW}🔗 URLs útiles:${NC}"
echo -e "  ALB: ${BLUE}http://${ALB_DNS}${NC}"
echo -e "  CloudWatch: ${BLUE}https://console.aws.amazon.com/cloudwatch/home?region=${AWS_REGION}#logsV2:log-groups${NC}"
echo -e "  ECS: ${BLUE}https://console.aws.amazon.com/ecs/v2/clusters/${CLUSTER}/services?region=${AWS_REGION}${NC}"
