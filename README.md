# csvglow

Generate beautiful, interactive HTML dashboards from CSV/Excel files. One command, zero config.

```bash
csvglow sales.csv
```

Opens a self-contained HTML dashboard in your browser with auto-detected charts, smart multi-column insights, correlations, and a sortable data table. Dark gradient theme. Copy any chart to your clipboard.

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
csvglow data.csv                    # CSV to dashboard, opens in browser
csvglow report.xlsx                 # Excel works too
csvglow data.csv -o dashboard.html  # Custom output path
csvglow data.csv --no-open          # Don't auto-open browser
```

## What it generates

- Smart findings — multi-column narrative analysis that cross-references metrics to surface contradictions, efficiency gaps, and top/underperformers
- Histograms for every numeric column with mean, median, std, quartiles, and outlier counts
- Bar charts for categorical columns
- Cross analysis — automatic categorical x numeric crosstabs with overall mean lines
- Time series line charts with area fill for date columns
- Correlation heatmap between numeric columns
- Scatter plots for highly correlated pairs (|r| > 0.7)
- Sortable, filterable data table (first 1000 rows)
- Copy button on each chart for pasting into slides

Output is a single self-contained HTML file. No server, no CDN, works offline.

## MCP Server

csvglow works as an MCP tool in any MCP-compatible client. Once configured, ask your AI assistant to generate a dashboard from a file path.

Pick your client and add csvglow to its MCP config file:

| Client | Config file location |
|--------|---------------------|
| Cursor | `.cursor/mcp.json` in your project root |
| Windsurf | `~/.windsurf/mcp.json` |

Add this to the config:

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

Uses npx so there's nothing extra to install.

If you already have csvglow installed via pip, use `"command": "csvglow"` with `"args": ["--mcp"]` instead.

## OpenClaw Skill

csvglow is available as an [OpenClaw](https://openclaw.dev) skill. Any OpenClaw-compatible client can discover and use it automatically — no manual config needed.

## Supported formats

- `.csv` / `.tsv` (auto-detected delimiter)
- `.xls`
- `.xlsx` (first sheet only — multi-sheet support coming soon)

## Changelog

### 0.1.0

- Initial release
- Auto-detection of column types (numeric, categorical, datetime, identifier)
- Smart findings: contradiction detection, efficiency analysis, top/underperformer identification across multiple columns
- Histograms with stats sidebar, bar charts, cross-analysis crosstabs, time series, correlation heatmap, scatter plots
- Sortable/filterable data table
- Copy-to-clipboard for all charts
- MCP server mode (`csvglow --mcp`)
- OpenClaw skill support
- Smart sampling for large files (100k+ rows)

## Roadmap

- Multi-sheet Excel support
- Multi-file support with join keys
- Light theme
- Custom color palettes
- PDF export

## License

MIT
