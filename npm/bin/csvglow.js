#!/usr/bin/env node

const { execFileSync, execSync } = require("child_process");
const args = process.argv.slice(2);

function tryRun(cmd, cmdArgs) {
  try {
    execFileSync(cmd, cmdArgs, { stdio: "inherit" });
    return true;
  } catch {
    return false;
  }
}

// Try running csvglow directly
if (tryRun("csvglow", args)) {
  process.exit(0);
}

// Not found — try pip install (with mcp dependency included)
console.log("csvglow not found. Installing via pip...");
try {
  execSync("pip install csvglow", { stdio: "inherit" });
} catch {
  try {
    execSync("pip3 install csvglow", { stdio: "inherit" });
  } catch {
    console.error("Failed to install csvglow. Please install Python 3.9+ and pip.");
    process.exit(1);
  }
}

// Retry
if (!tryRun("csvglow", args)) {
  console.error("csvglow installed but could not be found on PATH.");
  process.exit(1);
}
