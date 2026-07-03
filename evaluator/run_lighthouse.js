const lighthouse = require("lighthouse").default;
const chromeLauncher = require("chrome-launcher");

async function runLighthouse(url) {
  const chrome = await chromeLauncher.launch({
    chromePath: "/usr/bin/chromium",
    chromeFlags: [
      "--headless",
      "--no-sandbox",
      "--disable-gpu",
      "--disable-dev-shm-usage"
    ]
  });

  try {
    const options = {
      logLevel: "error",
      output: "json",
      onlyCategories: ["accessibility"],
      port: chrome.port
    };

    const runnerResult = await lighthouse(url, options);
    const lhr = runnerResult.lhr;

    const accessibilityScore =
      lhr.categories.accessibility.score !== null
        ? Math.round(lhr.categories.accessibility.score * 100)
        : null;

    return {
      summary: {
        accessibility_score: accessibilityScore
      },
      raw: lhr
    };

  } finally {
    await chrome.kill();
  }
}

module.exports = { runLighthouse };