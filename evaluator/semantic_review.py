import json
import os
import sys
from bs4 import BeautifulSoup
from openai import OpenAI


ALLOWED_CATEGORIES = [
    "alt_text",
    "link_text",
    "button_label",
    "heading_structure",
    "form_label",
    "language",
    "landmark",
    "semantic_structure"
]


def extract_relevant_html(html: str, max_chars: int = 14000) -> str:
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    relevant_elements = []

    selectors = [
        "html",
        "title",
        "main",
        "nav",
        "header",
        "footer",
        "section",
        "article",
        "h1", "h2", "h3", "h4",
        "img",
        "a",
        "button",
        "input",
        "label",
        "select",
        "textarea",
        "form"
    ]

    seen = set()

    for selector in selectors:
        for element in soup.find_all(selector):
            text = str(element).strip()
            if text and text not in seen:
                seen.add(text)
                relevant_elements.append(text)

    return "\n\n".join(relevant_elements)[:max_chars]


def build_prompt(url: str, html_excerpt: str, axe_summary: dict, lighthouse_score):
    categories = ", ".join(ALLOWED_CATEGORIES)

    return f"""
Eres un evaluador experto en accesibilidad web.

Tu tarea es realizar una revisión semántica complementaria de accesibilidad.
Esta revisión NO sustituye una auditoría experta y NO certifica cumplimiento WCAG.

Debes analizar únicamente problemas semánticos observables en los fragmentos HTML proporcionados.
No repitas hallazgos puramente sintácticos ya detectados por herramientas automáticas, salvo que exista una implicación semántica clara.

URL:
{url}

Resumen Axe:
{json.dumps(axe_summary, ensure_ascii=False)}

Puntaje Lighthouse:
{lighthouse_score}

Fragmentos HTML disponibles:
{html_excerpt}

Categorías permitidas:
{categories}

Reglas estrictas:
1. Devuelve únicamente JSON válido.
2. No uses markdown.
3. No inventes elementos, IDs, atributos, imágenes, enlaces o formularios que no estén en el HTML.
4. No uses la categoría "other".
5. No reportes un problema si no puedes señalar el fragmento HTML exacto.
6. Si una imagen tiene alt="" no la marques como problema, a menos que el HTML o el contexto demuestren claramente que la imagen transmite información.
7. Si el texto de un enlace o botón es ambiguo, debes citar el elemento exacto.
8. Si no hay evidencia suficiente, no lo reportes como hallazgo.
9. Cada hallazgo debe ser accionable y estar sustentado en evidencia.
10. Máximo 5 hallazgos.

Devuelve exactamente esta estructura JSON:

{{
  "semantic_status": "completed",
  "summary": "Resumen breve, específico y no especulativo.",
  "risk_level": "low|medium|high",
  "findings": [
    {{
      "category": "alt_text|link_text|button_label|heading_structure|form_label|language|landmark|semantic_structure",
      "severity": "low|medium|high",
      "selector": "Selector CSS aproximado o elemento HTML identificable.",
      "html_evidence": "Fragmento HTML exacto observado.",
      "description": "Descripción concreta del posible problema semántico.",
      "why_it_matters": "Por qué esto puede afectar a usuarios de tecnologías de asistencia.",
      "recommendation": "Recomendación breve y accionable."
    }}
  ]
}}

Si no encuentras problemas semánticos claros, devuelve:
{{
  "semantic_status": "completed",
  "summary": "No se identificaron problemas semánticos claros con la evidencia HTML disponible.",
  "risk_level": "low",
  "findings": []
}}
"""


def main():
    if len(sys.argv) < 2:
        print(json.dumps({
            "semantic_status": "failed",
            "summary": "No se recibió archivo de entrada.",
            "risk_level": "unknown",
            "findings": []
        }))
        sys.exit(1)

    input_path = sys.argv[1]

    with open(input_path, "r", encoding="utf-8") as file:
        payload = json.load(file)

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    model = os.getenv("OPENAI_MODEL", "gpt-5").strip()

    if not api_key or api_key == "coloca_aqui_tu_api_key":
        print(json.dumps({
            "semantic_status": "skipped",
            "summary": "Validación semántica omitida porque no se configuró OPENAI_API_KEY.",
            "risk_level": "unknown",
            "findings": []
        }, ensure_ascii=False))
        return

    url = payload.get("url", "")
    html = payload.get("html", "")
    axe_summary = payload.get("axe_summary", {})
    lighthouse_score = payload.get("lighthouse_score")

    html_excerpt = extract_relevant_html(html)
    prompt = build_prompt(url, html_excerpt, axe_summary, lighthouse_score)

    client = OpenAI(api_key=api_key)

    try:
        response = client.responses.create(
            model=model,
            input=prompt
        )

        text = response.output_text.strip()
        parsed = json.loads(text)

        parsed["findings"] = [
            item for item in parsed.get("findings", [])
            if item.get("category") in ALLOWED_CATEGORIES
            and item.get("html_evidence")
            and item.get("description")
        ]

        if not parsed["findings"]:
            parsed["risk_level"] = "low"

        print(json.dumps(parsed, ensure_ascii=False))

    except Exception as error:
        print(json.dumps({
            "semantic_status": "failed",
            "summary": f"No fue posible completar la revisión semántica: {str(error)}",
            "risk_level": "unknown",
            "findings": []
        }, ensure_ascii=False))


if __name__ == "__main__":
    main()