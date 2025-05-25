# -- Etapa 1: Construcción (builder)
FROM python:3.12-alpine AS builder

# Se establece el directorio de trabajo
WORKDIR /app

# Se copia solo el archivo de requisitos primero
COPY requeriments.txt .

# Instala las dependencias.
RUN pip install --no-cache-dir -r requeriments.txt

# Copia el resto del código fuente.
COPY . .

# -- Etapa 2: Ejecución
FROM python:3.12-alpine AS production

# Establece el directorio de trabajo para la aplicación final.
WORKDIR /backend

# Copia los paquetes instalados y el código de la etapa 'builder'.
# Copia el directorio completo donde pip instala los ejecutables
COPY --from=builder /usr/local/bin/ /usr/local/bin/
# Copia el directorio donde pip instala las librerías
COPY --from=builder /usr/local/lib/python3.12/site-packages/ /usr/local/lib/python3.12/site-packages/
# Copia el código de aplicación
COPY --from=builder /app /backend

# Expone el puerto de la aplicación
EXPOSE 8000

# Comando para iniciar la aplicación.
CMD ["uvicorn", "main:app", "--port", "8000"]