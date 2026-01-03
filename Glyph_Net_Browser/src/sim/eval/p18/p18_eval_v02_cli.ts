import fs from "node:fs";
import { runP18EvalV02 } from "./p18_eval_v02";

const out = process.argv[2]; // optional path
const r = runP18EvalV02();
const json = JSON.stringify(r, null, 2) + "\n";

if (out) {
  fs.mkdirSync(require("node:path").dirname(out), { recursive: true });
  fs.writeFileSync(out, json, "utf-8");
} else {
  process.stdout.write(json);
}
