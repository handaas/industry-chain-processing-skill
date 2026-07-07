# Report Output

Use this reference when the user asks for 展示、报告、HTML、静态页面、材料、交付、Markdown, or a shareable deliverable.

## Default display modes

- Chat/table: default for fast iteration.
- HTML: use for shareable visual reports. Produce a standalone local file with embedded CSS.
- Markdown: use for wiki, knowledge base, PRD, or later manual editing.
- JSON: use for system integration or further processing.

## Workflow

1. Build or collect a structured result object with these fields when available:
   - `title`
   - `summary`
   - `industry_map`
   - `priority_segments`
   - `search_strategy`
   - `candidates`
   - `decisions`
   - `next_actions`
2. Save the result JSON to a temporary or requested path.
3. Run `scripts/render_report.py`:

```bash
python scripts/render_report.py --input result.json --output report.html
python scripts/render_report.py --input result.json --output report.md
```

4. Return the report path and a concise summary.

## Quality bar

- The report should be readable without Codex context.
- Keep implementation details out of the main report unless the user asks.
- Include assumptions and evidence gaps.
- For real enterprise data, avoid printing secrets or raw signed requests.
