const { chromium } = require("playwright");
const AxeBuilder = require("@axe-core/playwright").default;

async function extractHtmlMetrics(page) {
  return await page.evaluate(() => {
    const getLang = () => document.documentElement.getAttribute("lang") || "";

    return {
      html_size: document.documentElement.outerHTML.length,
      dom_nodes: document.querySelectorAll("*").length,
      images: document.querySelectorAll("img").length,
      images_without_alt: document.querySelectorAll("img:not([alt])").length,
      links: document.querySelectorAll("a").length,
      buttons: document.querySelectorAll("button").length,
      forms: document.querySelectorAll("form").length,
      inputs: document.querySelectorAll("input, select, textarea").length,
      headings: document.querySelectorAll("h1, h2, h3, h4, h5, h6").length,
      h1_count: document.querySelectorAll("h1").length,
      language_declared: getLang(),
      has_main_landmark: document.querySelector("main, [role='main']") !== null,
      has_nav_landmark: document.querySelector("nav, [role='navigation']") !== null,
      has_header_landmark: document.querySelector("header, [role='banner']") !== null,
      has_footer_landmark: document.querySelector("footer, [role='contentinfo']") !== null
    };
  });
}

async function runAxe(url) {
  const browser = await chromium.launch({
    headless: true,
    executablePath: "/usr/bin/chromium",
    args: ["--no-sandbox", "--disable-dev-shm-usage"]
  });

  const context = await browser.newContext();
  const page = await context.newPage();

  try {
    await page.goto(url, {
      waitUntil: "networkidle",
      timeout: 60000
    });

    const html = await page.content();
    const htmlMetrics = await extractHtmlMetrics(page);
    const results = await new AxeBuilder({ page }).analyze();

    const summary = {
      violations: results.violations.length,
      critical: results.violations.filter(v => v.impact === "critical").length,
      serious: results.violations.filter(v => v.impact === "serious").length,
      moderate: results.violations.filter(v => v.impact === "moderate").length,
      minor: results.violations.filter(v => v.impact === "minor").length
    };

    return {
      summary,
      html,
      html_metrics: htmlMetrics,
      raw: results
    };

  } finally {
    await context.close();
    await browser.close();
  }
}

module.exports = { runAxe };