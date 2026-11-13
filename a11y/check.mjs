// Read HTML on stdin, run axe-core in jsdom, print the violations as JSON.
// Page scripts are not run (no network); colour contrast is skipped because jsdom has no layout.
import axe from "axe-core";
import { JSDOM } from "jsdom";

let html = "";
for await (const chunk of process.stdin) html += chunk;

const dom = new JSDOM(html, { runScripts: "outside-only" });
dom.window.eval(axe.source);
const result = await dom.window.axe.run(dom.window.document, {
  rules: { "color-contrast": { enabled: false } },
  resultTypes: ["violations"],
});
process.stdout.write(JSON.stringify(result.violations.map((v) => ({
  id: v.id, impact: v.impact, help: v.help, nodes: v.nodes.length,
}))));
