import { readFileSync, writeFileSync } from "node:fs";
import openapiTS, { astToString } from "openapi-typescript";

const spec = readFileSync(new URL("../../openapi.json", import.meta.url), "utf8");
const ast = await openapiTS(spec);
writeFileSync(new URL("../src/api-schema.d.ts", import.meta.url), astToString(ast));
console.log("wrote src/api-schema.d.ts");
