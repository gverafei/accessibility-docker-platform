import csv
import json
import os
from datetime import datetime
from io import StringIO

import requests
from flask import (
    Blueprint,
    Response,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)

from database import get_connection

import math
from statistics import mean, median, stdev

experiments_bp = Blueprint("experiments", __name__)


def now_local():
    timezone = current_app.config["APP_TIMEZONE"]
    return datetime.now(timezone).replace(tzinfo=None)


@experiments_bp.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@experiments_bp.route("/experiments", methods=["GET"])
def experiments():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT id, title, urls, include_semantic, status, created_at, completed_at
        FROM experiments
        ORDER BY created_at DESC
    """)

    experiments_data = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template("experiments.html", experiments=experiments_data)

def safe_mean(values):
    values = [v for v in values if v is not None]
    return round(mean(values), 2) if values else 0


def safe_median(values):
    values = [v for v in values if v is not None]
    return round(median(values), 2) if values else 0


def safe_stdev(values):
    values = [v for v in values if v is not None]
    return round(stdev(values), 2) if len(values) > 1 else 0


def pearson_correlation(x_values, y_values):
    pairs = [
        (x, y) for x, y in zip(x_values, y_values)
        if x is not None and y is not None
    ]

    if len(pairs) < 2:
        return None

    x = [p[0] for p in pairs]
    y = [p[1] for p in pairs]

    x_mean = mean(x)
    y_mean = mean(y)

    numerator = sum((xi - x_mean) * (yi - y_mean) for xi, yi in pairs)
    denominator_x = math.sqrt(sum((xi - x_mean) ** 2 for xi in x))
    denominator_y = math.sqrt(sum((yi - y_mean) ** 2 for yi in y))

    if denominator_x == 0 or denominator_y == 0:
        return None

    return round(numerator / (denominator_x * denominator_y), 3)


def rank_values(values):
    sorted_values = sorted((value, index) for index, value in enumerate(values))
    ranks = [0] * len(values)

    i = 0
    while i < len(sorted_values):
        j = i
        while j < len(sorted_values) and sorted_values[j][0] == sorted_values[i][0]:
            j += 1

        average_rank = (i + j + 1) / 2

        for k in range(i, j):
            ranks[sorted_values[k][1]] = average_rank

        i = j

    return ranks


def spearman_correlation(x_values, y_values):
    pairs = [
        (x, y) for x, y in zip(x_values, y_values)
        if x is not None and y is not None
    ]

    if len(pairs) < 2:
        return None

    x = [p[0] for p in pairs]
    y = [p[1] for p in pairs]

    return pearson_correlation(rank_values(x), rank_values(y))


def interpret_correlation(value):
    if value is None:
        return "Correlación no calculable"

    abs_value = abs(value)

    if abs_value >= 0.7:
        strength = "fuerte"
    elif abs_value >= 0.4:
        strength = "moderada"
    elif abs_value >= 0.2:
        strength = "débil"
    else:
        strength = "muy débil"

    direction = "positiva" if value > 0 else "negativa"
    return f"Correlación {direction} {strength}"


def build_experiment_analysis(results):
    total_urls = len(results)

    axe_values = [item.get("axe_violations") or 0 for item in results]
    lighthouse_values = [item.get("lighthouse_score") for item in results]
    dom_values = [item.get("dom_nodes") or 0 for item in results]
    image_values = [item.get("images") or 0 for item in results]
    execution_values = [item.get("execution_seconds") or 0 for item in results]
    gpt_findings_values = [
        len(item.get("semantic_findings") or [])
        for item in results
    ]

    total_axe = sum(axe_values)
    total_critical = sum(item.get("axe_critical") or 0 for item in results)
    total_serious = sum(item.get("axe_serious") or 0 for item in results)
    total_moderate = sum(item.get("axe_moderate") or 0 for item in results)
    total_minor = sum(item.get("axe_minor") or 0 for item in results)

    total_gpt_findings = sum(gpt_findings_values)

    correlations = {
        "axe_lighthouse": {
            "pearson": pearson_correlation(axe_values, lighthouse_values),
            "spearman": spearman_correlation(axe_values, lighthouse_values),
        },
        "dom_axe": {
            "pearson": pearson_correlation(dom_values, axe_values),
            "spearman": spearman_correlation(dom_values, axe_values),
        },
        "images_axe": {
            "pearson": pearson_correlation(image_values, axe_values),
            "spearman": spearman_correlation(image_values, axe_values),
        },
        "gpt_axe": {
            "pearson": pearson_correlation(gpt_findings_values, axe_values),
            "spearman": spearman_correlation(gpt_findings_values, axe_values),
        },
        "time_dom": {
            "pearson": pearson_correlation(execution_values, dom_values),
            "spearman": spearman_correlation(execution_values, dom_values),
        }
    }

    semantic_category_counts = {}

    for item in results:
        for finding in item.get("semantic_findings", []):
            category = finding.get("category")
            if category:
                semantic_category_counts[category] = semantic_category_counts.get(category, 0) + 1

    top_semantic_categories = sorted(
        semantic_category_counts.items(),
        key=lambda item: item[1],
        reverse=True
    )[:3]

    summary = (
        f"Se evaluaron {total_urls} URL(s). "
        f"Axe detectó {total_axe} violación(es) en total, "
        f"mientras que Lighthouse obtuvo un puntaje promedio de "
        f"{safe_mean(lighthouse_values)} sobre 100. "
        f"El análisis semántico registró {total_gpt_findings} hallazgo(s). "
        f"La relación spearman entre violaciones Axe y puntaje Lighthouse presenta "
        f"{interpret_correlation(correlations['axe_lighthouse']['spearman']).lower()}. "
        f"La relación spearman entre complejidad del DOM y violaciones Axe presenta "
        f"{interpret_correlation(correlations['dom_axe']['spearman']).lower()}. "
        f"La relación spearman entre cantidad de imágenes y violaciones Axe presenta "
        f"{interpret_correlation(correlations['images_axe']['spearman']).lower()}. "
        f"La relación spearman entre tiempo de ejecución y complejidad DOM presenta "
        f"{interpret_correlation(correlations['time_dom']['spearman']).lower()}. "
        
    )

    return {
        "summary": summary,
        "general": {
            "total_urls": total_urls,
            "total_axe": total_axe,
            "total_gpt_findings": total_gpt_findings,
            "lighthouse_mean": safe_mean(lighthouse_values),
            "lighthouse_median": safe_median(lighthouse_values),
            "dom_mean": safe_mean(dom_values),
            "execution_mean": safe_mean(execution_values),
            "execution_stdev": safe_stdev(execution_values),
        },
        "severity": {
            "critical": total_critical,
            "serious": total_serious,
            "moderate": total_moderate,
            "minor": total_minor,
        },
        "correlations": correlations,
        "top_semantic_categories": top_semantic_categories,
    }

@experiments_bp.route("/experiments/<int:experiment_id>", methods=["GET"])
def experiment_report(experiment_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT id, title, urls, include_semantic, status, created_at, completed_at
        FROM experiments
        WHERE id = %s
    """, (experiment_id,))
    experiment = cursor.fetchone()

    if not experiment:
        cursor.close()
        conn.close()
        flash("El experimento solicitado no existe.", "danger")
        return redirect(url_for("experiments.experiments"))

    cursor.execute("""
        SELECT *
        FROM experiment_results
        WHERE experiment_id = %s
        ORDER BY id ASC
    """, (experiment_id,))
    results = cursor.fetchall()

    cursor.execute("""
        SELECT *
        FROM experiment_environment
        WHERE experiment_id = %s
        ORDER BY id DESC
        LIMIT 1
    """, (experiment_id,))
    environment = cursor.fetchone()

    for item in results:
        findings = item.get("semantic_findings")
        if isinstance(findings, str):
            try:
                item["semantic_findings"] = json.loads(findings)
            except Exception:
                item["semantic_findings"] = []
        elif findings is None:
            item["semantic_findings"] = []

    cursor.close()
    conn.close()

    chart_labels = [item["url"] for item in results]
    axe_values = [item["axe_violations"] or 0 for item in results]
    lighthouse_values = [item["lighthouse_score"] or 0 for item in results]

    severity_totals = {
        "critical": sum(item["axe_critical"] or 0 for item in results),
        "serious": sum(item["axe_serious"] or 0 for item in results),
        "moderate": sum(item["axe_moderate"] or 0 for item in results),
        "minor": sum(item["axe_minor"] or 0 for item in results),
    }

    semantic_counts = {
        "low": sum(1 for item in results if item.get("semantic_risk_level") == "low"),
        "medium": sum(1 for item in results if item.get("semantic_risk_level") == "medium"),
        "high": sum(1 for item in results if item.get("semantic_risk_level") == "high"),
    }

    semantic_category_counts = {}

    for item in results:
        for finding in item.get("semantic_findings", []):
            category = finding.get("category", "unknown")
            semantic_category_counts[category] = semantic_category_counts.get(category, 0) + 1

    semantic_category_labels = list(semantic_category_counts.keys())
    semantic_category_values = list(semantic_category_counts.values())

    execution_values = [round(item["execution_seconds"] or 0, 2) for item in results]
    image_values = [item["images"] or 0 for item in results]
    dom_values = [item["dom_nodes"] or 0 for item in results]

    dom_values = [item["dom_nodes"] or 0 for item in results]
    image_values = [item["images"] or 0 for item in results]

    analysis = build_experiment_analysis(results)

    return render_template(
        "report.html",
        experiment=experiment,
        results=results,
        environment=environment,
        analysis=analysis,
        chart_labels=chart_labels,
        axe_values=axe_values,
        lighthouse_values=lighthouse_values,
        severity_totals=severity_totals,
        semantic_counts=semantic_counts,
        semantic_category_labels=semantic_category_labels,
        semantic_category_values=semantic_category_values,
        execution_values=execution_values,
        dom_values=dom_values,
        image_values=image_values
    )


@experiments_bp.route("/run", methods=["POST"])
def run_experiment():
    title = request.form.get("title", "").strip()
    urls_text = request.form.get("urls", "").strip()
    include_semantic = request.form.get("include_semantic") == "on"

    if not title:
        title = f"Experimento {now_local().strftime('%Y-%m-%d %H:%M:%S')}"

    if not urls_text:
        try:
            with open("/data/default_urls.txt", "r", encoding="utf-8") as file:
                urls = [line.strip() for line in file.readlines() if line.strip()]
        except FileNotFoundError:
            urls = []
    else:
        urls = [line.strip() for line in urls_text.splitlines() if line.strip()]

    if not urls:
        flash("No se proporcionaron URLs y no se encontró un dataset interno válido.", "danger")
        return redirect(url_for("experiments.index"))

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO experiments (title, urls, include_semantic, status, created_at)
        VALUES (%s, %s, %s, %s, %s)
    """, (
        title,
        "\n".join(urls),
        include_semantic,
        "running",
        now_local()
    ))

    experiment_id = cursor.lastrowid
    conn.commit()

    try:
        response = requests.post(
            f"{current_app.config['EVALUATOR_URL']}/evaluate",
            json={
                "experiment_id": experiment_id,
                "urls": urls,
                "include_semantic": include_semantic
            },
            timeout=900
        )

        response.raise_for_status()
        payload = response.json()

        environment = payload.get("environment", {})

        cursor.execute("""
            INSERT INTO experiment_environment (
                experiment_id,
                docker_web_image,
                docker_evaluator_image,
                python_version,
                node_version,
                chromium_version,
                axe_version,
                lighthouse_version,
                openai_model,
                execution_seconds,
                created_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            experiment_id,
            environment.get("docker_web_image"),
            environment.get("docker_evaluator_image"),
            environment.get("python_version"),
            environment.get("node_version"),
            environment.get("chromium_version"),
            environment.get("axe_version"),
            environment.get("lighthouse_version"),
            environment.get("openai_model"),
            environment.get("execution_seconds"),
            now_local()
        ))

        for item in payload.get("results", []):
            if item.get("status") == "completed":
                semantic = item.get("semantic", {})
                metrics = item.get("html_metrics", {})

                cursor.execute("""
                    INSERT INTO experiment_results (
                        experiment_id, url, status,
                        axe_violations, axe_critical, axe_serious,
                        axe_moderate, axe_minor,
                        lighthouse_score,
                        semantic_status, semantic_risk_level, semantic_summary, semantic_findings,
                        html_size, dom_nodes, images, images_without_alt, links, buttons,
                        forms, inputs, headings, h1_count, language_declared,
                        has_main_landmark, has_nav_landmark, has_header_landmark, has_footer_landmark,
                        execution_seconds,
                        axe_raw_path, lighthouse_raw_path, semantic_raw_path,
                        created_at
                    )
                    VALUES (
                        %s, %s, %s,
                        %s, %s, %s, %s, %s,
                        %s,
                        %s, %s, %s, CAST(%s AS JSON),
                        %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s,
                        %s, %s, %s, %s,
                        %s,
                        %s, %s, %s,
                        %s
                    )
                """, (
                    experiment_id,
                    item.get("url"),
                    "completed",
                    item.get("axe", {}).get("violations", 0),
                    item.get("axe", {}).get("critical", 0),
                    item.get("axe", {}).get("serious", 0),
                    item.get("axe", {}).get("moderate", 0),
                    item.get("axe", {}).get("minor", 0),
                    item.get("lighthouse", {}).get("accessibility_score"),
                    semantic.get("status"),
                    semantic.get("risk_level"),
                    semantic.get("summary"),
                    json.dumps(semantic.get("findings", []), ensure_ascii=False),
                    metrics.get("html_size", 0),
                    metrics.get("dom_nodes", 0),
                    metrics.get("images", 0),
                    metrics.get("images_without_alt", 0),
                    metrics.get("links", 0),
                    metrics.get("buttons", 0),
                    metrics.get("forms", 0),
                    metrics.get("inputs", 0),
                    metrics.get("headings", 0),
                    metrics.get("h1_count", 0),
                    metrics.get("language_declared"),
                    metrics.get("has_main_landmark", False),
                    metrics.get("has_nav_landmark", False),
                    metrics.get("has_header_landmark", False),
                    metrics.get("has_footer_landmark", False),
                    item.get("execution_seconds"),
                    item.get("axe", {}).get("raw_path"),
                    item.get("lighthouse", {}).get("raw_path"),
                    semantic.get("raw_path"),
                    now_local()
                ))
            else:
                cursor.execute("""
                    INSERT INTO experiment_results (
                        experiment_id, url, status, error_message, execution_seconds, created_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    experiment_id,
                    item.get("url"),
                    "failed",
                    item.get("error"),
                    item.get("execution_seconds"),
                    now_local()
                ))

        cursor.execute("""
            UPDATE experiments
            SET status = %s, completed_at = %s
            WHERE id = %s
        """, ("completed", now_local(), experiment_id))

        conn.commit()
        flash("Experimento ejecutado correctamente.", "success")

    except Exception as error:
        cursor.execute("""
            UPDATE experiments
            SET status = %s, completed_at = %s
            WHERE id = %s
        """, ("failed", now_local(), experiment_id))

        conn.commit()
        flash(f"No fue posible ejecutar el experimento: {error}", "danger")

    finally:
        cursor.close()
        conn.close()

    return redirect(url_for("experiments.experiment_report", experiment_id=experiment_id))


@experiments_bp.route("/experiments/<int:experiment_id>/csv", methods=["GET"])
def download_experiment_csv(experiment_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT *
        FROM experiment_results
        WHERE experiment_id = %s
        ORDER BY id ASC
    """, (experiment_id,))
    results = cursor.fetchall()

    cursor.close()
    conn.close()

    output = StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "experiment_id",
        "url",
        "status",
        "axe_violations",
        "axe_critical",
        "axe_serious",
        "axe_moderate",
        "axe_minor",
        "lighthouse_score",
        "semantic_status",
        "semantic_risk_level",
        "semantic_summary",
        "html_size",
        "dom_nodes",
        "images",
        "images_without_alt",
        "links",
        "buttons",
        "forms",
        "inputs",
        "headings",
        "h1_count",
        "language_declared",
        "has_main_landmark",
        "has_nav_landmark",
        "has_header_landmark",
        "has_footer_landmark",
        "execution_seconds"
    ])

    for item in results:
        writer.writerow([
            experiment_id,
            item.get("url"),
            item.get("status"),
            item.get("axe_violations"),
            item.get("axe_critical"),
            item.get("axe_serious"),
            item.get("axe_moderate"),
            item.get("axe_minor"),
            item.get("lighthouse_score"),
            item.get("semantic_status"),
            item.get("semantic_risk_level"),
            item.get("semantic_summary"),
            item.get("html_size"),
            item.get("dom_nodes"),
            item.get("images"),
            item.get("images_without_alt"),
            item.get("links"),
            item.get("buttons"),
            item.get("forms"),
            item.get("inputs"),
            item.get("headings"),
            item.get("h1_count"),
            item.get("language_declared"),
            item.get("has_main_landmark"),
            item.get("has_nav_landmark"),
            item.get("has_header_landmark"),
            item.get("has_footer_landmark"),
            item.get("execution_seconds")
        ])

    csv_content = output.getvalue()
    output.close()

    filename = f"experiment_{experiment_id}_results.csv"

    return Response(
        csv_content,
        mimetype="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )


@experiments_bp.route("/experiments/<int:experiment_id>/raw/<int:result_id>/<tool>", methods=["GET"])
def download_raw_result(experiment_id, result_id, tool):
    allowed_tools = {
        "axe": "axe_raw_path",
        "lighthouse": "lighthouse_raw_path",
        "semantic": "semantic_raw_path"
    }

    if tool not in allowed_tools:
        flash("Herramienta no válida para descarga.", "danger")
        return redirect(url_for("experiments.experiment_report", experiment_id=experiment_id))

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT id, experiment_id, url,
               axe_raw_path, lighthouse_raw_path, semantic_raw_path
        FROM experiment_results
        WHERE id = %s AND experiment_id = %s
    """, (result_id, experiment_id))

    result = cursor.fetchone()

    cursor.close()
    conn.close()

    if not result:
        flash("No se encontró el resultado solicitado.", "danger")
        return redirect(url_for("experiments.experiment_report", experiment_id=experiment_id))

    file_path = result.get(allowed_tools[tool])

    if not file_path or not os.path.exists(file_path):
        flash("El archivo solicitado no existe o no fue generado.", "warning")
        return redirect(url_for("experiments.experiment_report", experiment_id=experiment_id))

    filename = f"experiment_{experiment_id}_result_{result_id}_{tool}.json"

    return send_file(
        file_path,
        as_attachment=True,
        download_name=filename,
        mimetype="application/json"
    )