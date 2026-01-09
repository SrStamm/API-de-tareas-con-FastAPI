# 🗂️ API de Tareas con FastAPI

> Proyecto personal de backend enfocado en el diseño de APIs escalables, sistemas colaborativos y comunicación en tiempo real, desarrollado como parte de mi portfolio profesional.

Una API REST para gestionar tareas y usuarios en proyectos dentro de grupos.
Permite crear, asignar y completar tareas, con autenticación y control de permisos.
Incluye un sistema de chat por proyecto, comentarios en tareas asignadas, control de estado y vencimiento.
Además de contar con notificaciones al asignarse una tarea, actualizar una tarea asignada, mencionar en un comentario, entre otras.

- **Status:** En desarrollo activo / MVP estable
- **Deploy:** Servidor en EC2 + RDS (Postgres)
- **Frontend Deploy:** https://front-task-api-vanilla.vercel.app/dashboard/tasks
- **Username:** test
- **Password:** test123

> El frontend es un cliente de demostración.
> El foco principal del proyecto es el diseño y la arquitectura del backend.

---

## 🚀 Características


### Autenticación y Seguridad
- Registro, login, logout y refresh de usuarios con JWT
- Roles y permisos por grupo y proyecto

### Gestión de Grupos y Proyectos
- Crear, editar y eliminar grupos
- Gestión de usuarios dentro de grupos
- Crear y administrar proyectos dentro de grupos

### Gestión de Tareas
- Crear, editar, eliminar y asignar tareas
- Comentarios en tareas
- Control de estado y fechas de vencimiento

### Comunicación en Tiempo Real
- Notificaciones en tiempo real vía WebSockets
- Chat por proyecto (WebSocket + Redis Pub/Sub)
- Notificaciones pendientes procesadas con Celery

---

## 🛠 Tecnologías

- Python 3.12
- FastAPI
- SQLModel
- PostgreSQL
- Redis (cache y pub/sub)
- Docker & Docker Compose
- Celery (almacenar / enviar notificaciones pendientes)

---

## 🧱 Arquitectura

La aplicación sigue una **arquitectura modular en capas**, separando responsabilidades para mejorar mantenibilidad y testabilidad:

- **Routers**: definición de endpoints HTTP y WebSocket
- **Services**: lógica de negocio
- **Repositories**: acceso a datos y persistencia
- **Models**: entidades y esquemas (SQLModel / Pydantic)
- **Background Tasks**: procesamiento asíncrono con Celery
- **Real-time Layer**: WebSockets + Redis Pub/Sub

Esta separación permite escalar funcionalidades, testear la lógica de negocio de forma aislada y desacoplar la API de infraestructuras externas.

```
Client (React)
   ↓
FastAPI (Routers)
   ↓
Services
   ↓
Repositories
   ↓
PostgreSQL

WebSockets → Redis Pub/Sub
Celery → Redis → Notifications
```

---

## 🔐 Seguridad

- Autenticación basada en JWT (access y refresh tokens)
- Autorización por roles y permisos
- Endpoints protegidos
- Variables sensibles gestionadas mediante variables de entorno
- Separación de permisos a nivel grupo y proyecto

---

## 🧪 Testing

- Tests automatizados con **Pytest**
- Cobertura amplia de la lógica de negocio y endpoints críticos
- Uso de fixtures y entorno de testing desacoplado
- Integrado en pipeline de **CI con GitHub Actions**

---

## 🔁 CI / Automatización

- Pipeline de **GitHub Actions** configurado para ejecutar tests automáticamente en cada push y pull request.
- Validación continua del estado del proyecto mediante testing automatizado.
- Workflow generado y ajustado con apoyo de herramientas de IA.

---

## ☁️ Deploy

- Backend preparado para despliegue en entornos cloud (Docker)
- Configuración desacoplada mediante variables de entorno
- Usado como backend real para frontend externo (no público)

---

## 🔧 Instalación (modo local)

1. Clona el repositorio:
```bash
git clone <url-del-repo>
cd backend
```

2. Crear un entorno virtual:

```bash
python -m venv env
source env/bin/activate  # En Linux/Mac
env\Scripts\activate     # En Windows
```

3. Instala dependencias (sin testing):

```bash
# Sin las dependencias de testing 
pip install -r requirements.txt

# Con las dependencias del testing
pip install -r requirements-test.txt
```

4. Ejecuta la APP:

```bash
uvicorn main:app --reload
```

# Instalación (con Docker)

1. Ejecuta el siguiente comando:

```bash
docker-compose up --build
```
La api estará disponible en `http://localhost:8000`

## Variables de entorno:

Crea un archivo `.env` en la raíz con las siguientes variables:

```bash
# PostgreSQL
POSTGRES_USER=usuario
POSTGRES_PASSWORD=contraseña
POSTGRES_DB=nombre_base
DATABASE_URL=postgresql+psycopg2://usuario:contraseña@task-db:5432/nombre_base

# Redis
REDIS_PASSWORD=clave_redis

# Seguridad
SECRET_KEY=clave_secreta
ALGORITHM=HS256

# Tokens
ACCESS_TOKEN_DURATION=30
REFRESH_TOKEN_DURATION=60
```

## Documentación de la API

- Swagger UI: [`http://localhost:8000/docs']
- Redoc: [`http://localhost:8000/redoc']

### Licencia
Este proyecto está bajo la licencia MIT.
