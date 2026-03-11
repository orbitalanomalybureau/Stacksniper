import { build, context } from "esbuild";
import { execSync } from "child_process";

// Build Tailwind CSS first
execSync("npx tailwindcss -i ./src/styles/globals.css -o ./public/styles.css --minify");

const config = {
  entryPoints: ["src/index.jsx"],
  bundle: true,
  outfile: "public/bundle.js",
  loader: { ".jsx": "jsx", ".js": "jsx" },
  jsx: "automatic",
  jsxImportSource: "react",
  define: {
    "process.env.NODE_ENV": JSON.stringify(
      process.env.NODE_ENV || "development"
    ),
    "process.env.REACT_APP_API_URL": JSON.stringify(
      process.env.REACT_APP_API_URL || "http://localhost:8000"
    ),
  },
  minify: process.env.NODE_ENV === "production",
  sourcemap: process.env.NODE_ENV !== "production",
  target: ["es2020"],
};

if (process.argv.includes("--watch")) {
  const ctx = await context(config);
  await ctx.watch();
  console.log("Watching for changes...");
} else {
  await build(config);
  console.log("Build complete.");
}
