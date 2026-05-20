# E-commerce Data Ingesta

Ingesta masiva de datos desde microservicios hacia AWS S3 con 2 contenedores Docker independientes.

## Estructura

```
.
├── docker-compose.yml          # Orquesta los contenedores activos
├── Dockerfile                  # Imagen base compartida
├── .env.example                # Variables de ejemplo
├── containers/
│   ├── ingest_users/           # Contenedor para usuarios
│   │   ├── ingest_users.py
│   │   └── requirements.txt
│   ├── ingest_orders/          # Contenedor para órdenes (Node.js API)
│   │   ├── ingest_orders.py
│   │   └── requirements.txt
└── README.md
```

## Requisitos

- Docker & Docker Compose
- AWS Credentials configuradas
- Microservicios ejecutándose en red compartida

## Instalación

### 1. Configurar variables de entorno

```bash
cp .env.example .env
# Editar .env con tus credenciales AWS
```

### 2. Iniciar contenedores

```bash
docker-compose up --build
```

Esto iniciará:
- `ingest_users`: pull desde Users Service (Python/FastAPI) usando el superadmin `rafael@superadmin.com`
- `ingest_orders`: pull desde Orders Service (Node.js) usando el mismo login admin

`ingest_products` queda deshabilitado por ahora porque productos se carga manualmente desde el frontend.

## Salida esperada

Archivos en S3:
```
s3://ecommerce-athena-results-12345/
├── ingesta/
│   ├── users/
│   │   └── users_20260503_142530.csv
│   └── orders/
│       └── orders_20260503_142532.csv
```

## Logs

Ver logs de cada contenedor:

```bash
docker-compose logs -f ingest_users
docker-compose logs -f ingest_orders
```

## Integración con Athena

Una vez los archivos están en S3:

1. Crear catálogo Glue apuntando a `s3://bucket/ingesta/users/`
2. Crear tablas externas en Athena
3. Ejecutar consultas SQL

Ejemplo:
```sql
SELECT COUNT(*) FROM users WHERE email LIKE '%@example.com';
SELECT AVG(total) FROM orders GROUP BY estado;
```

## Auth for Ingesta

The ingestion containers authenticate against the users service with the superadmin account:

- email: `rafael@superadmin.com`
- password: `admin123`

This token is then used to read protected endpoints for `users` and `orders`.
