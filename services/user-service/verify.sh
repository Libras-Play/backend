#!/bin/bash
# Verificación rápida del User Service

echo "🔍 Verificando User Service..."
echo ""

# 1. Verificar sintaxis Python
echo "1️⃣  Verificando sintaxis de archivos Python..."
python -m py_compile app/main.py && echo "   ✅ app/main.py OK" || echo "   ❌ app/main.py FAIL"
python -m py_compile app/config.py && echo "   ✅ app/config.py OK" || echo "   ❌ app/config.py FAIL"
python -m py_compile app/schemas.py && echo "   ✅ app/schemas.py OK" || echo "   ❌ app/schemas.py FAIL"
python -m py_compile app/dynamo.py && echo "   ✅ app/dynamo.py OK" || echo "   ❌ app/dynamo.py FAIL"
python -m py_compile app/aws_client.py && echo "   ✅ app/aws_client.py OK" || echo "   ❌ app/aws_client.py FAIL"
python -m py_compile app/logic/gamification.py && echo "   ✅ app/logic/gamification.py OK" || echo "   ❌ gamification.py FAIL"
echo ""

# 2. Verificar que la app se puede importar
echo "2️⃣  Verificando que la app se puede importar..."
python -c "from app.main import app; print('   ✅ App importada correctamente')" || echo "   ❌ Error al importar app"
echo ""

# 3. Ejecutar tests
echo "3️⃣  Ejecutando tests..."
python -m pytest tests/test_user_service.py -v --tb=no -q
echo ""

# 4. Verificar archivos clave
echo "4️⃣  Verificando archivos clave..."
test -f app/main.py && echo "   ✅ app/main.py existe" || echo "   ❌ app/main.py falta"
test -f app/config.py && echo "   ✅ app/config.py existe" || echo "   ❌ app/config.py falta"
test -f app/schemas.py && echo "   ✅ app/schemas.py existe" || echo "   ❌ app/schemas.py falta"
test -f app/dynamo.py && echo "   ✅ app/dynamo.py existe" || echo "   ❌ app/dynamo.py falta"
test -f infra/dynamodb.tf && echo "   ✅ infra/dynamodb.tf existe" || echo "   ❌ dynamodb.tf falta"
test -f scripts/create_tables_local.py && echo "   ✅ create_tables_local.py existe" || echo "   ❌ script falta"
test -f scripts/seed_demo_users.py && echo "   ✅ seed_demo_users.py existe" || echo "   ❌ script falta"
test -f tests/test_user_service.py && echo "   ✅ test_user_service.py existe" || echo "   ❌ tests faltan"
echo ""

# 5. Contar líneas de código
echo "5️⃣  Estadísticas de código..."
echo "   📊 Líneas de código:"
wc -l app/main.py app/config.py app/schemas.py app/dynamo.py app/aws_client.py app/logic/gamification.py 2>/dev/null | tail -1
echo ""

echo "✅ Verificación completa!"
echo ""
echo "📝 Próximos pasos:"
echo "   1. cd ../../localstack && docker-compose up -d"
echo "   2. python scripts/create_tables_local.py"
echo "   3. python scripts/seed_demo_users.py"
echo "   4. uvicorn app.main:app --reload --port 8001"
echo "   5. curl http://localhost:8001/health"
