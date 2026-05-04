# E-commerce Data Ingesta

Ingesta masiva de datos desde microservicios hacia AWS S3 con 3 contenedores Docker independientes.

## Estructura

```
.
├── docker-compose.yml          # Orquesta los 3 contenedores
├── Dockerfile                  # Imagen base compartida
├── .env.example                # Variables de ejemplo
├── containers/
│   ├── ingest_users/           # Contenedor para usuarios
│   │   ├── ingest_users.py
│   │   └── requirements.txt
│   ├── ingest_products/        # Contenedor para productos (Java API)
│   │   ├── ingest_products.py
│   │   └── requirements.txt
│   ├── ingest_orders/          # Contenedor para órdenes (Node.js API)
│   │   ├── ingest_orders.py
│   │   └── requirements.txt
└── README.md
```

## Características

- **3 contenedores independientes**: cada uno extrae datos de su microservicio
- **Pull 100%**: obtiene el total de registros desde APIs REST
- **CSV Output**: genera archivos CSV para Athena
- **S3 Upload**: carga automáticamente a `s3://bucket/ingesta/{users,products,orders}/`
- **Timestamp**: archivos nombrados con fecha/hora para histórico

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
- `ingest_users`: pull desde Users Service (Python/FastAPI)
- `ingest_products`: pull desde Products Service (Java)
- `ingest_orders`: pull desde Orders Service (Node.js)

## Salida esperada

Archivos en S3:
```
s3://ecommerce-athena-results-12345/
├── ingesta/
│   ├── users/
│   │   └── users_20260503_142530.csv
│   ├── products/
│   │   └── products_20260503_142531.csv
│   └── orders/
│       └── orders_20260503_142532.csv
```

## Logs

Ver logs de cada contenedor:

```bash
docker-compose logs -f ingest_users
docker-compose logs -f ingest_products
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

## Próximos pasos

- Aumentar volumen a 20,000 registros (semilla en BD)
- Crear vistas en Athena
- Implementar scheduler (cron/Lambda) para ingesta automática
