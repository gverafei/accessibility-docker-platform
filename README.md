# Accessibility Docker Platform

Infraestructura experimental contenerizada para la evaluación reproducible de accesibilidad web mediante Axe, Lighthouse y validación semántica opcional con GPT-5.

![Home](docs/images/arquitectura-docker.png)

## 1. Descripción

Este proyecto permite ejecutar experimentos de evaluación de accesibilidad web desde una plataforma desarrollada en Flask. La infraestructura utiliza Docker Compose para ejecutar tres servicios:

- `web`: aplicación Flask con interfaz web.
- `evaluator`: servicio Node.js/Python con Axe, Lighthouse, Chromium y GPT-5.
- `db`: base de datos MySQL 8.

La plataforma permite registrar experimentos, evaluar una o varias URLs, generar reportes, visualizar gráficas y descargar evidencias en CSV y JSON.

## 2. Requisitos

Antes de ejecutar el proyecto se requiere tener instalado:

- Docker
- Docker Compose
- Conexión a Internet

> Docker Compose ya se encuentra incluido en Docker Desktop.

Opcionalmente, para usar la validación semántica:

- API key de OpenAI

## 3. Estructura del proyecto

```text
accessibility-docker-platform/
│
├── docker-compose.yml
├── .env.example
├── README.md
│
├── web/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│
├── evaluator/
│   ├── Dockerfile
│   ├── package.json
│   ├── requirements.txt
│   ├── server.js
│   ├── run_axe.js
│   ├── run_lighthouse.js
│   └── semantic_review.py
│
├── data/
│   └── default_urls.txt
│
└── results/
    ├── raw/
```

## 4. Configuración

Copiar el archivo de ejemplo:

```bash
cp env.example .env
```

Editar `.env` si se desea usar GPT-5:

```env
OPENAI_API_KEY=coloca_aqui_tu_api_key
OPENAI_MODEL=gpt-5
APP_TIMEZONE=America/Mexico_City
```

Si no se configura la API key, la plataforma puede ejecutarse sin validación semántica.

## 5. Ejecución

Construir y levantar los contenedores:

```bash
docker compose up --build
```

Abrir en el navegador:

```text
http://localhost
```

## 6. Reinicio limpio

Si se modifican tablas de MySQL o se requiere borrar todos los experimentos:

```bash
docker compose down -v --remove-orphans
docker compose up --build
```

Este comando elimina los volúmenes, incluida la base de datos.

# Uso de la plataforma

## Paso 1. Abrir la aplicación

Abrir `http://localhost`.

Al iniciar la plataforma se mostrará la página principal.

![Inicio](docs/images/home.png)

---

## Paso 2. Crear un nuevo experimento

Introduzca una o varias URL (una por línea).

Si el cuadro de texto se deja vacío, la plataforma utilizará automáticamente el conjunto de sitios de prueba incluido en el proyecto en el archivo:

```text
data/default_urls.txt
```

![Nuevo experimento](docs/images/new_experiment.png)

## Paso 3. Habilitar el análisis semántico (opcional)

Active la opción de análisis semántico mediante GPT-5.

Esta funcionalidad realiza una inspección adicional enfocada en aspectos semánticos de accesibilidad que normalmente no son detectados por herramientas automáticas tradicionales.

![Análisis semántico](docs/images/semantic_checkbox.png)

## Paso 4. Generar el reporte

Presione el botón:

> **Generar reporte**

Mientras se ejecuta el experimento se mostrará una barra de progreso indicando el estado de procesamiento.

![Progreso](docs/images/progress.png)

## Paso 5. Consultar los resultados

Al finalizar el experimento se mostrará un reporte interactivo con:

- Violaciones detectadas por Axe-Core.
- Puntaje de accesibilidad obtenido por Lighthouse.
- Hallazgos del análisis semántico mediante GPT-5.
- Métricas estructurales del documento HTML.
- Información del entorno experimental.
- Estadísticas descriptivas.
- Gráficas interactivas.

![Reporte](docs/images/report.png)

## Paso 6. Descargar las evidencias

La plataforma permite descargar:

- Dataset consolidado (CSV)
- Resultados de Axe-Core (JSON)
- Resultados de Lighthouse (JSON)
- Resultados del análisis semántico (JSON)

Estos archivos permiten conservar las evidencias originales del experimento y facilitan su reproducción posterior.

![Descargas](docs/images/downloads.png)

## 8. Resultados generados

Cada experimento almacena:

- Versión de Python
- Versión de Node.js
- Versión de Chromium
- Versión de Axe-Core
- Versión de Lighthouse
- Modelo GPT utilizado
- Versión de las imágenes Docker
- URLs evaluadas.
- Resultados de Axe.
- Resultados de Lighthouse.
- Resultados semánticos de GPT-5 (opcional).
- Métricas estructurales del HTML.
- Información del entorno experimental.
- Tiempo de ejecución.
- Evidencias crudas en formato JSON.
- Dataset consolidado en formato CSV.

## 9. Evidencias descargables

Desde el reporte del experimento se pueden descargar:

- CSV consolidado del experimento.
- JSON crudo de Axe.
- JSON crudo de Lighthouse.
- JSON crudo de GPT-5 (cuando aplique).

Estos archivos permiten conservar las evidencias originales del experimento y facilitan su reproducción posterior.

## 10. Servicios Docker

La infraestructura está compuesta por tres servicios:

```text
web        Flask + Jinja2 + Bootstrap 5
evaluator  Node.js + Chromium + Axe + Lighthouse + Python + GPT-5
db         MySQL 8
```

El servicio `web` se publica en el puerto 80 del equipo anfitrión, por lo que la aplicación se abre directamente desde:

```text
http://localhost
```

## 11. Reproducibilidad

La plataforma registra automáticamente el entorno experimental utilizado en cada ejecución:

- Versión de Python.
- Versión de Node.js.
- Versión de Chromium.
- Versión de Axe Playwright.
- Versión de Lighthouse.
- Modelo LLM configurado.
- Tiempo total de ejecución.

Esto permite documentar las condiciones bajo las cuales se ejecutó cada experimento y facilita su reproducción por otros investigadores.

## 12. Publicación de imágenes en Docker Hub

Una vez validada la solución, las imágenes pueden construirse mediante:

```bash
docker build --platform linux/amd64,linux/arm64 -t tuusuario/accessibility-web ./web
docker build --platform linux/amd64,linux/arm64 -t tuusuario/accessibility-evaluator ./evaluator
```

Posteriormente podrán publicarse mediante:

```bash
docker push tuusuario/accessibility-web
docker push tuusuario/accessibility-evaluator
```

Para verificar que tienen soporte de multi-arquitectura:

```bash
docker buildx imagetools inspect tuusuario/accessibility-web
docker buildx imagetools inspect tuusuario/accessibility-evaluator
```

Debe aparecer dos campos Platform con linux/amd64 y linux/arm64

De esta forma, se podrá ejecutar la plataforma descargando únicamente las imágenes desde Docker Hub, sin necesidad de reconstruir el proyecto.

# Licencia

MIT License