const express = require("express");
const fs = require("fs");
const path = require("path");
const { spawnSync, execSync } = require("child_process");

const { runAxe } = require("./run_axe");
const { runLighthouse } = require("./run_lighthouse");

const app = express();
app.use(express.json({ limit: "20mb" }));

const RESULTS_DIR = "/results/raw";

function ensureDir(dirPath) {
  if (!fs.existsSync(dirPath)) {
    fs.mkdirSync(dirPath, { recursive: true });
  }
}

function safeFileName(url) {
  return url
    .replace(/^https?:\/\//, "")
    .replace(/[^a-zA-Z0-9]/g, "_")
    .replace(/_+/g, "_")
    .slice(0, 80);
}

function getCommandOutput(command) {
  try {
    return execSync(command, { encoding: "utf-8" }).trim();
  } catch {
    return "unknown";
  }
}

function getPackageVersion(packageName) {
  try {
    const output = execSync(`npm list ${packageName} --depth=0 --json`, {
      encoding: "utf-8"
    });
    const parsed = JSON.parse(output);
    return parsed.dependencies?.[packageName]?.version || "unknown";
  } catch {
    return "unknown";
  }
}

function getEnvironmentMetadata(executionSeconds) {
  return {
    docker_web_image: process.env.DOCKER_WEB_IMAGE || "local-build",
    docker_evaluator_image: process.env.DOCKER_EVALUATOR_IMAGE || "local-build",
    python_version: getCommandOutput("python3 --version"),
    node_version: getCommandOutput("node --version"),
    chromium_version: getCommandOutput("chromium --version"),
    axe_version: getPackageVersion("@axe-core/playwright"),
    lighthouse_version: getPackageVersion("lighthouse"),
    openai_model: process.env.OPENAI_MODEL || "not-configured",
    execution_seconds: executionSeconds
  };
}

function runSemanticReview(inputPath) {
  const result = spawnSync("python3", ["/evaluator/semantic_review.py", inputPath], {
    encoding: "utf-8",
    timeout: 120000,
    env: process.env
  });

  if (result.error) {
    return {
      semantic_status: "failed",
      summary: result.error.message,
      risk_level: "unknown",
      findings: []
    };
  }

  try {
    return JSON.parse(result.stdout);
  } catch {
    return {
      semantic_status: "failed",
      summary: "La respuesta del módulo semántico no fue JSON válido.",
      risk_level: "unknown",
      findings: [],
      raw_output: result.stdout,
      stderr: result.stderr
    };
  }
}

app.get("/health", (req, res) => {
  res.json({
    status: "ok",
    service: "accessibility-evaluator"
  });
});

app.post("/evaluate", async (req, res) => {
  const experimentStart = Date.now();
  const { experiment_id, urls, include_semantic } = req.body;

  if (!experiment_id || !Array.isArray(urls) || urls.length === 0) {
    return res.status(400).json({
      error: "experiment_id y urls son requeridos"
    });
  }

  ensureDir(RESULTS_DIR);

  const experimentDir = path.join(RESULTS_DIR, `experiment_${experiment_id}`);
  ensureDir(experimentDir);

  const results = [];

  for (const url of urls) {
    const itemStart = Date.now();
    const fileBase = safeFileName(url);

    try {
      const axeResult = await runAxe(url);
      const lighthouseResult = await runLighthouse(url);

      const axePath = path.join(experimentDir, `${fileBase}_axe.json`);
      const lighthousePath = path.join(experimentDir, `${fileBase}_lighthouse.json`);

      fs.writeFileSync(axePath, JSON.stringify(axeResult.raw, null, 2), "utf-8");
      fs.writeFileSync(lighthousePath, JSON.stringify(lighthouseResult.raw, null, 2), "utf-8");

      let semanticResult = {
        semantic_status: "skipped",
        summary: "Validación semántica no solicitada para este experimento.",
        risk_level: "unknown",
        findings: []
      };

      let semanticPath = null;

      if (include_semantic === true) {
        const semanticInputPath = path.join(experimentDir, `${fileBase}_semantic_input.json`);
        semanticPath = path.join(experimentDir, `${fileBase}_semantic.json`);

        const semanticInput = {
          url,
          html: axeResult.html,
          axe_summary: axeResult.summary,
          lighthouse_score: lighthouseResult.summary.accessibility_score
        };

        fs.writeFileSync(semanticInputPath, JSON.stringify(semanticInput, null, 2), "utf-8");

        semanticResult = runSemanticReview(semanticInputPath);

        fs.writeFileSync(semanticPath, JSON.stringify(semanticResult, null, 2), "utf-8");
      }

      const executionSeconds = (Date.now() - itemStart) / 1000;

      results.push({
        url,
        status: "completed",
        execution_seconds: executionSeconds,
        html_metrics: axeResult.html_metrics,
        axe: {
          violations: axeResult.summary.violations,
          critical: axeResult.summary.critical,
          serious: axeResult.summary.serious,
          moderate: axeResult.summary.moderate,
          minor: axeResult.summary.minor,
          raw_path: axePath
        },
        lighthouse: {
          accessibility_score: lighthouseResult.summary.accessibility_score,
          raw_path: lighthousePath
        },
        semantic: {
          status: semanticResult.semantic_status,
          summary: semanticResult.summary,
          risk_level: semanticResult.risk_level,
          findings: semanticResult.findings || [],
          raw_path: semanticPath
        }
      });

    } catch (error) {
      results.push({
        url,
        status: "failed",
        error: error.message,
        execution_seconds: (Date.now() - itemStart) / 1000
      });
    }
  }

  const totalExecutionSeconds = (Date.now() - experimentStart) / 1000;

  res.json({
    experiment_id,
    status: "completed",
    environment: getEnvironmentMetadata(totalExecutionSeconds),
    results
  });
});

app.listen(3000, "0.0.0.0", () => {
  console.log("Evaluator service running on port 3000");
});