# CLI I/O Contract

This page defines the input/output contract for MTHDS methods when invoked as CLI commands. It specifies what a method writes to stdout, what it reads from stdin, and how errors propagate through pipe chains.

## Stuffs on the Wire

A stuff — one named value in a working memory, whether a method input or a pipe's result — crosses every boundary on this page in one shape:

```json
{
  "concept": "legal.ContractAnalysis",
  "content": { "clauses": ["..."], "overall_risk": "high" }
}
```

`concept` names the concept by its **crate key**, the string the [library crate](./library-crate.md#1-merge) keys it under: the domain-qualified reference `<domain>.<Code>` for a concept the method's own package declares (`legal.ContractAnalysis`) or a native concept (`native.Text`), and the address-prefixed `<package_address>::<domain>.<Code>` for a concept a dependency contributes (`github.com/mthds/scoring-lib::scoring.ScoreResult`). Two packages may declare the same domain and code, so a dependency's concept is never named by the bare `<domain>.<Code>`, and the prefix is the package address, never the alias one consumer happens to give it. `content` is the value, shaped as the concept's structure dictates. The same string names the concept wherever a stuff travels: an entry of `--inputs`, a stuff read from stdin, every entry of `working_memory.root` in the `--with-memory` envelope, every stuff of a runner's `pipe_output` over the [HTTP protocol](./protocol.md#executing-a-method), and any file a runtime writes from a working memory.

The reference is the whole of what a stuff says about its concept. The concept's definition — its description, its structure, what it refines, and anything an implementation attaches to it, such as the name of a runtime class — belongs to the library the method loads and never travels beside a stuff. A consumer that needs the definition resolves the reference against that library, or reads it from the [pipe I/O contracts](./pipe-io-contracts.md) a validating runtime reports. A runtime MUST emit `concept` as this string and MUST NOT emit an object in its place.

On input, a runtime MUST accept the crate key. As a convenience for a caller typing inputs by hand, it MAY also accept a package-qualified reference (`alias->domain.Code`) or a bare concept code and resolve either against the method's library — how it resolves an ambiguous bare code is implementation-defined — and it MAY accept a bare value in place of the stuff (a string, a number, an object or a list) and shape it against the input's declared concept. What it emits is always a stuff, its `concept` the crate key.

An implementation MAY carry fields of its own beside `concept` and `content` — an identifier for the stuff, for instance. A consumer ignores fields it does not know and never needs them to read the value.

## Output Modes

A method's CLI produces structured JSON on stdout. Two output modes are defined: **compact** (default) and **full** (opt-in via `--with-memory`).

### Compact Output (Default)

The concept's rendered JSON is emitted directly — no envelope, no metadata:

```json
{
  "clauses": [
    { "title": "Non-Compete", "risk_level": "high" },
    { "title": "Termination", "risk_level": "medium" }
  ],
  "overall_risk": "high"
}
```

This is the structured content of the method's main output concept. Standard JSON tools work directly:

```bash
mthds-agent pipelex run method extract-terms | jq '.clauses[] | select(.risk_level == "high")'

# Or using the installed CLI shim:
extract-terms | jq '.clauses[] | select(.risk_level == "high")'
```

A completed method always has a main output. If the declared output resolves as absent (for example, an optional `?` output produced no value), the CLI emits an explicit absence document rather than an empty or missing result.

### Full Output (`--with-memory`)

When `--with-memory` is passed, the output includes the main stuff renderings and the full working memory:

```json
{
  "main_stuff": {
    "json": "<concept as JSON string>",
    "markdown": "<concept as Markdown string>",
    "html": "<concept as HTML string>"
  },
  "working_memory": {
    "root": {
      "contract_text": {
        "concept": "native.Text",
        "content": { "text": "The parties agree..." }
      },
      "extracted_terms": {
        "concept": "legal.ContractAnalysis",
        "content": { "clauses": ["..."], "overall_risk": "high" }
      },
      "main_stuff": {
        "concept": "legal.ContractAnalysis",
        "content": { "clauses": ["..."], "overall_risk": "high" }
      }
    },
    "aliases": {
      "main_stuff": "extracted_terms"
    }
  }
}
```

Every entry of `root` is a stuff in the [wire form](#stuffs-on-the-wire): its `concept` is the concept's crate key, never the concept's definition. The full output preserves all intermediate results and aliases from the pipeline's working memory. This is required when piping output to another method, because the downstream method may need intermediate stuffs for multi-input binding.

### Side Effects

Regardless of output mode, the runtime may write side-effect files to disk:

- **Output JSON** (`live_run.json` / `dry_run.json`) — the full execution result saved alongside the bundle.
- **Graph HTML** (`live_run.html` / `dry_run.html`) — execution graph visualizations (generated by default, disabled with `--no-graph`).

These files are not included in stdout output. Their paths appear in runtime logs on stderr.

## Input Acceptance

A method accepts inputs through three sources, resolved in priority order:

### 1. `--inputs` Flag (Highest Priority)

The `--inputs` / `-i` flag accepts a file path or inline JSON string. If the value starts with `{`, it is parsed as inline JSON; otherwise it is treated as a file path.

```bash
# Inline JSON
mthds-agent pipelex run method my_method --inputs '{"text": {"concept": "native.Text", "content": {"text": "hello"}}}'

# File path
mthds-agent pipelex run method my_method --inputs data.json
```

When a method is installed as a CLI shim (see [CLI Reference](../cli/index.md)), the same commands are available as:

```bash
my_method --inputs '{"text": {"concept": "native.Text", "content": {"text": "hello"}}}'
my_method --inputs data.json
```

When `--inputs` is provided, stdin is ignored entirely. This allows overriding piped data for debugging.

### 2. stdin (Fallback)

When `--inputs` is not provided and stdin is not a TTY (i.e., data is being piped), JSON is read from stdin:

```bash
echo '{"text": {"concept": "native.Text", "content": {"text": "hello"}}}' | mthds-agent pipelex run method my_method
```

When stdin is a TTY (interactive terminal), no stdin reading occurs and the method runs without inputs.

### 3. Auto-detected `inputs.json`

In directory mode, `inputs.json` in the target directory is auto-detected and used as a fallback when no explicit inputs are provided.

## Envelope Detection

When JSON arrives via stdin, the runtime distinguishes between two formats based on the presence of a `working_memory` key at the top level:

### Flat Inputs

No `working_memory` key present. The JSON is treated as direct input bindings — the same format as `--inputs`, each binding a stuff in the [wire form](#stuffs-on-the-wire):

```json
{
  "document": {
    "concept": "native.Document",
    "content": { "url": "/path/to/file.pdf" }
  }
}
```

### Full Envelope

A `working_memory` key is present. This indicates the JSON came from an upstream method's `--with-memory` output. The runtime extracts named stuffs from `working_memory.root` and converts them to input bindings.

The input resolution rules when receiving a full envelope:

1. **Name matching**: Each stuff name in the upstream working memory's `root` is matched against the downstream method's declared input names. Matching entries are bound automatically.

2. **Single-input shortcut**: If the downstream method declares exactly one input, it auto-binds to the upstream's `main_stuff` content. This is the common case for simple chains:

    ```bash
    extract-terms --with-memory | assess-risk
    ```

3. **Error on failure**: If the downstream method's declared inputs cannot be satisfied from the upstream's working memory, a clear error is raised listing what was available upstream vs. what was expected downstream.

## Error Propagation

Errors are emitted as structured JSON on **stderr** with a non-zero exit code:

```json
{
  "error": true,
  "error_type": "PipelineExecutionError",
  "message": "Pipe 'assess_risk' failed: missing required input 'analysis'",
  "hint": "Check 'pipe_stack' to identify which pipe failed",
  "error_domain": "runtime",
  "retryable": false
}
```

In a Unix pipe chain, errors stop execution at the failing step. Use `set -o pipefail` in shell scripts to ensure mid-chain failures propagate:

```bash
set -o pipefail
extract-terms --with-memory \
  | assess-risk --with-memory \
  | generate-report
```

## Examples

### Simple Chain (Single Input)

```bash
# Extract terms, then assess risk, then generate report
extract-terms --inputs '{"document": {"concept": "native.Document", "content": {"url": "contract.pdf"}}}' --with-memory \
  | assess-risk --with-memory \
  | generate-report
```

Each intermediate step uses `--with-memory` to pass the full envelope. The final step omits it to produce compact output.

### Compact Output with jq

```bash
# Extract just the high-risk clauses
extract-terms --inputs data.json \
  | jq '.clauses[] | select(.risk_level == "high")'
```

### Override Piped Input

```bash
# The --inputs flag overrides whatever comes from stdin
echo '{"text": {"concept": "native.Text", "content": {"text": "from stdin"}}}' \
  | mthds-agent pipelex run method my_method --inputs '{"text": {"concept": "native.Text", "content": {"text": "from the flag"}}}'
```

The `--inputs` flag always wins — the stdin data is ignored.
