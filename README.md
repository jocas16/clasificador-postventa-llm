# Tipificación inteligente de casos de post-venta con LLM

Proyecto personal de exploración de **LLMs, AI Engineering y automatización inteligente** aplicado a la clasificación y tipificación de casos de post-venta.

El proyecto parte de una problemática común en procesos operativos: información que debe ser leída, interpretada y tipificada manualmente por analistas.

La hipótesis explorada es:

> **Automatizar los casos simples y repetitivos, manteniendo al analista humano en el circuito para los casos ambiguos, críticos o que requieren contexto adicional.**

El objetivo no es reemplazar el criterio humano, sino **reducir tareas repetitivas y concentrar el trabajo de los analistas donde realmente aporta valor**.

---

## 🎯 Objetivo

Construir y evaluar un pipeline end-to-end capaz de recibir un caso de post-venta y generar una tipificación estructurada:

* Categoría
* Subcategoría
* Prioridad
* Justificación
* Confianza

La respuesta del LLM es posteriormente validada contra una **taxonomía controlada**, permitiendo decidir qué casos pueden automatizarse y cuáles deben pasar a revisión humana.

---

## 💡 Problema que explora el proyecto

Un proceso tradicional puede representarse como:

```text
CASO RECIBIDO
     ↓
LECTURA DEL CASO
     ↓
INTERPRETACIÓN
     ↓
TIPIFICACIÓN MANUAL
     ↓
REVISIÓN / GESTIÓN
```

La propuesta explorada es:

```text
CASO RECIBIDO
     ↓
PREPROCESAMIENTO + PII
     ↓
LLM
     ↓
JSON ESTRUCTURADO
     ↓
VALIDACIÓN CONTRA TAXONOMÍA
     ↓
CONFIDENCE / REGLAS
     ↓
 ┌───────────────────────┐
 │                       │
 ▼                       ▼
AUTOMATIZACIÓN       REVISIÓN HUMANA
casos simples        casos ambiguos,
                     críticos o complejos
```

Este enfoque permite implementar un esquema de **Human-in-the-Loop**, donde la IA automatiza lo repetitivo y el analista conserva el control sobre los casos que requieren mayor criterio.

---

# 🏗️ Arquitectura

```text
                    ┌───────────────────┐
                    │   CASOS / INPUT   │
                    └─────────┬─────────┘
                              ↓
                    ┌───────────────────┐
                    │ PREPROCESAMIENTO  │
                    │ Limpieza + PII    │
                    └─────────┬─────────┘
                              ↓
                    ┌───────────────────┐
                    │    TAXONOMÍA      │
                    │ Categorías válidas│
                    └─────────┬─────────┘
                              ↓
                    ┌───────────────────┐
                    │ PROMPT ENGINEERING│
                    │ System + Few-shot │
                    └─────────┬─────────┘
                              ↓
              ┌───────────────┴────────────────┐
              ↓                                ↓
        ┌───────────┐                    ┌────────────┐
        │  OLLAMA   │                    │ API CLOUD  │
        │  Local    │                    │ Groq /     │
        │           │                    │ OpenRouter │
        └─────┬─────┘                    └─────┬──────┘
              └───────────────┬────────────────┘
                              ↓
                    ┌───────────────────┐
                    │ JSON ESTRUCTURADO │
                    └─────────┬─────────┘
                              ↓
                    ┌───────────────────┐
                    │    GUARDRAILS     │
                    │ Parseo + Validación│
                    └─────────┬─────────┘
                              ↓
                    ┌───────────────────┐
                    │    CONFIDENCE     │
                    │   + THRESHOLD     │
                    └─────────┬─────────┘
                              ↓
              ┌───────────────┴────────────────┐
              ↓                                ↓
       ┌───────────────┐                ┌───────────────┐
       │ AUTOMATIZABLE │                │    HUMANO     │
       │ Alta confianza│                │ Baja confianza│
       └───────┬───────┘                └───────┬───────┘
               └───────────────┬────────────────┘
                               ↓
                    ┌───────────────────┐
                    │    EVALUACIÓN     │
                    │ Accuracy / F1 / κ │
                    └─────────┬─────────┘
                              ↓
                    ┌───────────────────┐
                    │    DASHBOARD      │
                    └───────────────────┘
```

---

# 🧠 Componentes principales

## Taxonomía controlada

La taxonomía se mantiene en:

```text
config/taxonomy.yaml
```

Esto permite separar las reglas del negocio del código de aplicación.

La taxonomía contiene:

* Categorías
* Subcategorías
* Prioridad sugerida
* Descripciones
* Señales asociadas
* Versión de taxonomía

Ejemplo conceptual:

```yaml
Transferencias:
  Transferencia duplicada:
    prioridad: ALTA

  Transferencia no acreditada:
    prioridad: ALTA

  Transferencia con datos errados:
    prioridad: MEDIA
```

Una de las ideas centrales del proyecto es:

> **El LLM no debe tener libertad para inventar nuevas etiquetas.**

---

## 🔐 Preprocesamiento y PII

Antes de enviar información al modelo se realiza:

* Validación de columnas
* Limpieza
* Validación de longitud
* Eliminación de duplicados
* Enmascaramiento de información sensible

Se consideran datos como:

* Tarjetas
* Cuentas
* DNI
* Correos electrónicos
* Teléfonos

Esto permite explorar un enfoque donde la información sensible innecesaria no se envía directamente al proveedor del modelo.

---

## 📝 Prompt Engineering

El proyecto utiliza un prompt estructurado con:

* System prompt
* Taxonomía disponible
* Reglas de prioridad
* Few-shot examples
* Instrucciones de formato
* Reglas para casos ambiguos

El modelo recibe ejemplos de:

```text
USER → caso
ASSISTANT → clasificación esperada
```

Esto permite orientar el comportamiento del modelo sin necesidad de fine-tuning.

---

## 📦 Structured Output

El LLM debe devolver una estructura JSON similar a:

```json
{
  "categoria": "Transferencias",
  "subcategoria": "Transferencia duplicada",
  "prioridad": "ALTA",
  "justificacion": "El cliente reporta que la transferencia fue realizada dos veces.",
  "confianza": 0.95
}
```

La salida posteriormente es parseada y validada.

Esto permite pasar de:

```text
Lenguaje natural
        ↓
LLM
        ↓
Datos estructurados
        ↓
Pipeline tradicional
```

---

# 🛡️ Guardrails

El proyecto incorpora controles para evitar que una respuesta del LLM sea aceptada automáticamente sin validación.

Entre ellos:

* Parseo defensivo del JSON
* Validación de campos
* Validación de categorías
* Validación de subcategorías
* Validación de prioridades
* Canonización contra la taxonomía
* Reintentos
* Fallback ante respuestas inválidas

Si el modelo genera una clasificación que no existe en la taxonomía:

```text
Otros
└── No clasificable
```

y el caso puede ser enviado a revisión humana.

---

# 🎚️ Confidence y Human-in-the-Loop

Cada clasificación incluye un valor de confianza entre `0` y `1`.

Se utiliza un umbral configurable:

```text
CONFIDENCE_THRESHOLD = 0.70
```

Conceptualmente:

```text
                 CONFIDENCIA
                     │
          ┌──────────┴──────────┐
          │                     │
        >= 0.70                < 0.70
          │                     │
          ▼                     ▼
   AUTOMATIZABLE          REVISIÓN HUMANA
```

El objetivo no es asumir que:

> "confianza alta = modelo perfecto"

sino utilizar la confianza como una señal para decidir **qué casos pueden pasar automáticamente y cuáles necesitan intervención humana**.

---

# 🧪 Experimentación con modelos

Una parte importante del proyecto fue comparar diferentes alternativas de ejecución.

Se evaluaron:

* Baseline basado en reglas (`mock`)
* Modelo local mediante Ollama
* API de Groq
* API de OpenRouter

### Resultados de la experimentación

| Alternativa                | Latencia promedio |     P95 | Categoría | Subcategoría | Prioridad | Confianza |
| -------------------------- | ----------------: | ------: | --------: | -----------: | --------: | --------: |
| Mock                       |                 — |       — |       80% |          80% |       90% |     0.736 |
| Ollama / Qwen 2.5 3B       |            ~9.7 s |       — |       90% |          90% |       60% |     0.765 |
| Groq / GPT-OSS 120B        |           ~1.22 s | ~1.63 s |  **100%** |     **100%** |       70% | **0.888** |
| OpenRouter / Llama 3.3 70B |           ~1.93 s | ~3.06 s |  **100%** |     **100%** |       80% |     0.820 |

### Resultados adicionales

**Groq / GPT-OSS 120B**

* Tokens totales: `11,870`
* Revisión humana: `10%`
* Errores de LLM: `0%`
* Confidence promedio: `0.888`

**OpenRouter / Llama 3.3 70B**

* Tokens totales: `10,218`
* Revisión humana: `10%`
* Errores de LLM: `0%`
* Confidence promedio: `0.820`

> **Importante:** esta comparación se realizó sobre un conjunto pequeño de 10 casos dummy y tiene carácter exploratorio. Los resultados no representan desempeño productivo ni permiten concluir que un modelo sea definitivamente superior.

---

# 📊 Evaluación

El proyecto evalúa diferentes dimensiones de la clasificación.

## Accuracy

Proporción de predicciones correctas.

## F1 Score

Se utiliza especialmente para observar el comportamiento cuando las clases están desbalanceadas.

Se considera particularmente importante analizar las clases minoritarias y críticas.

## Cohen's Kappa

Permite medir el acuerdo entre las predicciones y las etiquetas reales considerando el acuerdo esperado por azar.

## Matriz de confusión

Permite identificar qué categorías o subcategorías se confunden entre sí.

## Calibración

Se analiza si la confianza declarada por el modelo tiene relación con su probabilidad real de acertar.

Por ejemplo:

```text
Confianza declarada ≈ 0.90
            ↓
¿Realmente acierta aproximadamente 90%?
```

Si existe una diferencia importante, el threshold de automatización puede no ser confiable.

## Curva de automatización

Permite estudiar el trade-off entre:

```text
Más automatización
       ↕
Más revisión humana
       ↕
Costo de errores
```

La decisión del threshold debería depender del costo real de equivocarse y del costo de la revisión manual.

---

# 🧪 Baseline basado en reglas

Antes de utilizar un LLM se implementó un baseline `mock` basado en reglas.

Sobre 1,000 casos dummy:

| Nivel        | Accuracy | F1 macro |     κ |
| ------------ | -------: | -------: | ----: |
| Categoría    |    0.755 |    0.757 | 0.719 |
| Subcategoría |    0.721 |    0.719 | 0.706 |
| Prioridad    |    0.851 |    0.826 | 0.753 |

Con un threshold de `0.70`, aproximadamente el `75%` de los casos fueron considerados automatizables en este baseline.

Este baseline cumple una función importante:

> **Si una solución basada en LLM no aporta suficiente valor frente a una solución mucho más simple, su costo y complejidad deben cuestionarse.**

---

# 📈 Dashboard

El proyecto incluye un dashboard desarrollado con Streamlit.

Permite explorar:

* Volumen de casos
* Distribución por categoría
* Distribución por prioridad
* Distribución por canal
* Accuracy
* F1
* Cohen's Kappa
* Errores frecuentes
* Confianza
* Curva de automatización
* Cola de revisión humana
* Detalle de las predicciones

Flujo:

```text
Pipeline
   ↓
casos_clasificados_latest.csv
   ↓
Streamlit Dashboard
   ↓
Monitoreo / análisis / revisión
```

El dashboard busca representar cómo podría evolucionar el prototipo hacia una herramienta operacional para un equipo de calidad.

---

# 📁 Estructura del proyecto

```text
clasificador_postventa/
│
├── config/
│   └── taxonomy.yaml
│
├── data/
│   ├── raw/
│   └── processed/
│
├── notebooks/
│
├── outputs/
│
├── scripts/
│   ├── generar_dummy.py
│   └── run_pipeline.py
│
├── src/
│   ├── config.py
│   ├── schemas.py
│   ├── preprocessing.py
│   ├── prompts.py
│   ├── classifier.py
│   ├── evaluation.py
│   ├── pipeline.py
│   │
│   └── llm/
│       ├── base.py
│       ├── mock_client.py
│       ├── ollama_client.py
│       ├── openai_compat_client.py
│       └── factory.py
│
├── tests/
│
├── app_dashboard.py
├── .env.example
├── requirements.txt
└── README.md
```

### Responsabilidad de los principales módulos

| Archivo            | Responsabilidad                             |
| ------------------ | ------------------------------------------- |
| `taxonomy.yaml`    | Taxonomía y reglas del negocio              |
| `config.py`        | Configuración y variables de entorno        |
| `schemas.py`       | Contratos de datos                          |
| `preprocessing.py` | Limpieza y PII                              |
| `prompts.py`       | Prompt engineering                          |
| `classifier.py`    | Inferencia, parseo, guardrails y reintentos |
| `llm/`             | Abstracción de proveedores                  |
| `evaluation.py`    | Métricas y análisis                         |
| `pipeline.py`      | Orquestación end-to-end                     |
| `run_pipeline.py`  | Ejecución desde CLI                         |
| `app_dashboard.py` | Visualización y análisis                    |

---

# 🚀 Uso rápido

Instalar dependencias:

```bash
pip install -r requirements.txt
```

Crear archivo de configuración:

```bash
cp .env.example .env
```

Generar datos dummy:

```bash
python scripts/generar_dummy.py --n 1000
```

Ejecutar baseline:

```bash
python scripts/run_pipeline.py \
    --datos data/raw/casos_postventa.csv \
    --provider mock
```

Ejecutar con Ollama:

```bash
ollama serve
ollama pull qwen2.5:3b

python scripts/run_pipeline.py \
    --datos data/raw/casos_postventa.csv \
    --provider ollama \
    --workers 2
```

Ejecutar dashboard:

```bash
streamlit run app_dashboard.py
```

---

# 📄 Formato de entrada

El pipeline espera como mínimo:

```text
id_caso
fecha
canal
texto_caso
```

Opcionalmente, para evaluación:

```text
categoria_real
subcategoria_real
prioridad_real
```

Ejemplo:

```csv
id_caso,fecha,canal,texto_caso
CASO_00001,2026-09-01,Web,"Realicé una transferencia y el dinero no llegó"
CASO_00002,2026-09-01,App,"Me cobraron dos veces la misma operación"
```

---

# 🔌 Proveedores

El diseño utiliza una interfaz común para poder cambiar el proveedor sin modificar la lógica principal del pipeline.

```text
                 BaseLLMClient
                       │
        ┌──────────────┼──────────────┐
        ↓              ↓              ↓
      Mock          Ollama       OpenAI-compatible
                                      │
                              ┌───────┴───────┐
                              ↓               ↓
                            Groq         OpenRouter
```

Esto permite separar:

```text
Lógica del negocio
       ≠
Proveedor del modelo
```

---

# 🔐 Consideraciones de seguridad

El proyecto explora prácticas relevantes para escenarios donde puede existir información sensible:

* Enmascaramiento de PII antes de la inferencia.
* Separación de configuración mediante variables de entorno.
* No almacenar API keys directamente en el código.
* Posibilidad de utilizar modelos locales.
* Validación de las respuestas del modelo.
* Trazabilidad de la predicción.
* Versionado de taxonomía, modelo y configuración.

En un entorno productivo sería necesario complementar estas medidas con las políticas de seguridad, privacidad, arquitectura y cumplimiento correspondientes a la organización.

---

# 🏭 Del prototipo a producción

El siguiente paso para llevar este enfoque a un entorno real sería trabajar con datos históricos reales y un proceso de validación controlado.

### 1. Dataset real

Construir un dataset representativo de casos históricos tipificados por analistas.

Idealmente:

```text
Caso
   +
Tipificación real
   +
Analista
   +
Fecha
   +
Canal
   +
Observaciones
```

### 2. Calidad del etiquetado

Una posible estrategia es solicitar que dos analistas independientes tipifiquen una muestra de casos y medir su nivel de acuerdo.

Esto permite conocer el **techo humano de la tarea** antes de evaluar el modelo.

### 3. Human-in-the-loop

Los casos de baja confianza, críticos o ambiguos se derivan al analista.

Las correcciones realizadas por los analistas pueden convertirse posteriormente en nuevos datos de evaluación o ejemplos para mejorar el sistema.

### 4. Versionado

Registrar en cada predicción:

```text
taxonomy_version
model
prompt_version
provider
confidence
timestamp
```

Esto permite reproducibilidad y auditoría.

### 5. Monitoreo

En producción sería importante monitorear:

* Distribución de categorías
* Drift
* % de revisión humana
* % automatizado
* Latencia P95
* Tasa de errores
* Tasa de `Otros`
* Confidence
* Costo por caso
* Calidad por categoría

---

# ⚠️ Limitaciones actuales

Este proyecto es una **exploración personal / prototipo técnico** y no una implementación productiva.

Entre sus principales limitaciones:

* Los resultados comparativos de LLM se obtuvieron sobre un conjunto pequeño de casos.
* Los datos utilizados para la experimentación son dummy.
* La taxonomía es demostrativa.
* No se ha validado todavía el comportamiento con una muestra representativa de casos reales.
* La confidence generada por un LLM no debe interpretarse automáticamente como una probabilidad calibrada.
* Los resultados de un proveedor pueden cambiar según modelo, disponibilidad, configuración y límites de la API.
* Para un escenario real se requiere una evaluación más amplia de costo, seguridad, privacidad, latencia y calidad.

---

# 🧠 Principales aprendizajes

Este proyecto permitió explorar el desarrollo de una solución LLM más allá de simplemente realizar consultas a un modelo.

### 1. Los LLM necesitan restricciones

Un modelo generativo debe estar acompañado de:

```text
Taxonomía
+
Prompt
+
Structured Output
+
Validación
+
Guardrails
```

### 2. La taxonomía es parte fundamental de la solución

La calidad del modelo no puede separarse de la calidad de las categorías que se le pide identificar.

### 3. Confidence permite introducir supervisión humana

No todos los casos deben automatizarse.

El objetivo puede ser:

```text
LLM
 ↓
¿Es suficientemente confiable?
 ↓
Sí → Automatizar
No → Analista
```

### 4. Un baseline es fundamental

Antes de justificar la complejidad de un LLM es necesario comparar contra una alternativa sencilla.

### 5. Evaluar un LLM es más que medir Accuracy

También importan:

```text
Accuracy
F1
Kappa
Calibración
Latencia
P95
Tokens
Costo
% Automatización
% Revisión humana
```

### 6. El modelo es solo una pieza del sistema

Una solución LLM real requiere combinar:

```text
Datos
+
Reglas de negocio
+
LLM
+
Validación
+
Evaluación
+
Monitoreo
+
Humano
```

---

# 🔭 Posibles siguientes pasos

Como evolución del proyecto:

* Incorporar casos reales anonimizados.
* Construir una taxonomía empresarial.
* Evaluar varios cientos o miles de casos.
* Medir acuerdo entre analistas.
* Analizar errores por categoría.
* Calibrar el threshold de confianza.
* Incorporar costos reales por proveedor.
* Evaluar modelos adicionales.
* Explorar structured outputs más estrictos.
* Incorporar observabilidad.
* Implementar un mecanismo de feedback de los analistas.
* Evaluar RAG cuando la clasificación requiera consultar políticas, procedimientos o documentación.
* Analizar cuándo conviene utilizar prompting, RAG, fine-tuning o reglas determinísticas.

---

# 📌 Conclusión

Este proyecto nació como una exploración personal para entender **cómo llevar los LLM desde una prueba aislada hacia un flujo de automatización medible, controlado y orientado a procesos reales**.

La principal idea explorada es:

> **No automatizar por automatizar. Automatizar aquello que puede hacerse de forma confiable y utilizar el criterio humano donde realmente aporta valor.**

El caso de tipificación de post-venta es un escenario de referencia, pero el mismo enfoque puede extenderse a otras tareas repetitivas de clasificación, priorización y procesamiento de información estructurada o semiestructurada.

---

## 👨‍💻 Autor

Proyecto personal desarrollado como parte de mi exploración en:

* Large Language Models (LLMs)
* AI Engineering
* Prompt Engineering
* Machine Learning
* NLP
* Human-in-the-Loop
* Evaluación de modelos
* Automatización inteligente

**Stack principal:**

```text
Python
LLMs
Ollama
Groq
OpenRouter
Pandas
Scikit-learn
PyYAML
Streamlit
Pydantic
```
