# Driving Colab from Claude Code (Colab MCP)

Google's open-source Colab MCP server (https://github.com/googlecolab/colab-mcp) lets a local agent add cells to a Colab notebook, run them and read the output.

## Setup
1. Install `uv`: `pip install uv` (or `curl -LsSf https://astral.sh/uv/install.sh | sh`).
2. Register the server with Claude Code:
   ```
   claude mcp add colab-mcp --scope user -- uvx git+https://github.com/googlecolab/colab-mcp
   ```
   Or in an `mcp.json`:
   ```json
   { "mcpServers": { "colab-mcp": { "command": "uvx", "args": ["git+https://github.com/googlecolab/colab-mcp"], "timeout": 30000 } } }
   ```
3. Restart Claude Code. The agent calls `open_colab_browser_connection`, which opens Colab in your browser. Click Connect in the notebook.
4. In Colab: Runtime > Change runtime type > GPU. Add the secrets listed in the README.

## Other clients (already configured on this Mac)
```
codex mcp add colab-mcp -- uvx git+https://github.com/googlecolab/colab-mcp
grok mcp add --scope user colab-mcp uvx -- git+https://github.com/googlecolab/colab-mcp
# Cursor / cursor-agent: ~/.cursor/mcp.json
{"mcpServers":{"colab-mcp":{"command":"uvx","args":["git+https://github.com/googlecolab/colab-mcp"],"timeout":30000}}}
```
The server needs clients that support `notifications/tools/list_changed`. Claude Code is confirmed; if another
client shows no Colab tools after connecting, use Claude Code to drive Colab.

## Notes
- The client must run locally and support `notifications/tools/list_changed` (Claude Code does).
- The server connects to a notebook session in your browser, so keep that Colab tab open.
- Runtime restarts may need a manual click in the Colab UI.
- Tools: `add_code_cell`, `add_text_cell`, `update_cell`, `move_cell`, `delete_cell`, `get_cells`, `run_code_cell`, `open_colab_browser_connection`.
- Colab sessions time out. Keep data and checkpoints on Drive (the notebook already does this) and use `--resume`.

## Suggested instruction for the agent
Paste the prompt in [CLAUDE_PROMPT.md](CLAUDE_PROMPT.md) after the connection is established.
