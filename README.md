# csvglow

Generate beautiful, interactive HTML dashboards from CSV/Excel files. One command, zero config.

```bash
csvglow sales.csv
```

Opens a self-contained HTML dashboard in your browser with auto-detected charts, correlations, statistics, and a sortable data table. Dark gradient theme. Copy any chart to your clipboard for slide decks.

## Install

```bash
pip install csvglow
```

Or via npx (no install needed):

```bash
npx csvglow data.csv
```

## Usage

```bash
csvglow data.csv                    # CSV → dashboard, opens in browser
csvglow report.xlsx                 # Excel works too
csvglow data.csv -o dashboard.html  # Custom output path
csvglow data.csv --no-open          # Don't auto-open browser
```

## What it generates

- **Smart insights** — multi-column narrative analysis (e.g. "Gadget Y has the highest discount yet lowest revenue — consider discontinuing")
- **Summary stats** — row count, column count, data types, missing values
- **Histograms** — for every numeric column, with mean/median/std/quartiles sidebar
- **Bar charts** — top values for categorical columns
- **Cross analysis** — automatic categorical × numeric crosstabs with overall mean lines
- **Time series** — line charts with area fill for date columns
- **Correlation heatmap** — auto-detected correlations between numeric columns
- **Scatter plots** — auto-generated for highly correlated pairs (|r| > 0.7)
- **Outlier detection** — IQR-based, highlighted per column
- **Data table** — sortable, filterable preview (first 1000 rows)
- **Copy button** — each chart has a one-click copy for pasting into slides

Output is a single self-contained HTML file. No server, no CDN, works offline.

## MCP Server

csvglow works as an MCP tool in Claude Desktop, Cursor, Claude Code, Windsurf, or any MCP-compatible client. Once configured, just ask your AI assistant:

> "Generate a dashboard from /path/to/sales.csv"

### Setup

Pick your client and add csvglow to its MCP config file:

| Client | Config file location |
|--------|---------------------|
| Claude Desktop | `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) |
| Cursor | `.cursor/mcp.json` in your project root |
| Windsurf | `~/.windsurf/mcp.json` |

Open that file and add csvglow to the `mcpServers` section:

```json
{
  "mcpServers": {
    "csvglow": {
      "command": "npx",
      "args": ["-y", "csvglow", "--mcp"]
    }
  }
}
```

This uses npx so there's nothing to install — it downloads and runs automatically.

If you already have csvglow installed via pip, use this instead:

```json
{
  "mcpServers": {
    "csvglow": {
      "command": "csvglow",
      "args": ["--mcp"]
    }
  }
}
```

**Claude Code** — run this in your terminal instead of editing a config file:

```bash
claude mcp add csvglow -- npx -y csvglow --mcp
```

## OpenClaw Skill

csvglow is available as an [OpenClaw](https://openclaw.dev) skill. Any OpenClaw-compatible client can discover and use it automatically — no manual config needed.

## Supported formats

- `.csv` / `.tsv` (auto-detected delimiter)
- `.xls`
- `.xlsx` (first sheet only — multi-sheet support coming soon)

## Roadmap

-  Multi-sheet Excel support — analyze all sheets in a workbook, with per-tab sections or auto-merge when columns match
-  Multi-file support — `csvglow sales.csv marketing.csv --join date` to correlate data across multiple files with auto-detected or explicit join keys
-  Light theme
-  Custom color palettes
-  PDF export

## License

MIT
