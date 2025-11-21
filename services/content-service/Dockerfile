FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements
COPY requirements.txt .

# Instalar dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código de la aplicación
COPY . .

# Dar permisos de ejecución al script de inicio
RUN chmod +x start.sh

# Exponer puerto
EXPOSE 8000

# Comando por defecto - ejecutar migraciones y luego iniciar
CMD ["./start.sh"]
