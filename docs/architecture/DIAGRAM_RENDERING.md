# Diagram Rendering Setup

## Overview

All architecture diagrams in this documentation use [Mermaid](https://mermaid.js.org/), a markdown-compatible diagramming language that renders directly in GitHub and many documentation platforms.

## Recommended Rendering Options

### Option 1: GitHub Native Rendering (Recommended)

GitHub natively renders Mermaid diagrams in markdown files. No additional setup required.

**Advantages**:

- Zero configuration
- Always up-to-date with latest Mermaid version
- Works in PRs, issues, and wiki

**Usage**:

````markdown
````mermaid
graph TD
    A[Start] --> B[Process]
    B --> C[End]
\```
````
````

### Option 2: MkDocs with mermaid2 Plugin

For local preview and offline documentation browsing.

**Installation**:

```bash
pip install mkdocs mkdocs-mermaid2-plugin
```

**Configuration** (`mkdocs.yml`):

```yaml
site_name: Architecture Documentation
plugins:
  - search
  - mermaid2

markdown_extensions:
  - pymdownx.superfences:
      custom_fences:
        - name: mermaid
          class: mermaid
          format: !!python/name:mermaid2.fence_mermaid
```

**Local Preview**:

```bash
mkdocs serve
```

Browse to `http://127.0.0.1:8000`

### Option 3: VS Code with Mermaid Extension

For diagram editing and live preview in the editor.

**Extension**: [Markdown Preview Mermaid Support](https://marketplace.visualstudio.com/items?itemName=bierner.markdown-mermaid)

**Installation**:

1. Open VS Code
2. Press `Ctrl+Shift+X` (Cmd+Shift+X on Mac)
3. Search for "Markdown Preview Mermaid"
4. Install the extension

**Usage**:

- Open any `.md` file with Mermaid diagrams
- Press `Ctrl+Shift+V` (Cmd+Shift+V on Mac) for side-by-side preview
- Diagrams render automatically in the preview pane

## Diagram Types Used

The architecture documentation uses these Mermaid diagram types:

- **Flowchart** (`graph TD`): System component relationships, data flows
- **Sequence Diagram** (`sequenceDiagram`): Request/response flows, authentication flows
- **Class Diagram** (`classDiagram`): Domain models, bounded contexts
- **Entity Relationship** (`erDiagram`): Database schema, data relationships
- **State Diagram** (`stateDiagram-v2`): Entity lifecycle states
- **C4 Context** (`C4Context`): System context and container diagrams

## Best Practices

1. **Keep diagrams simple**: Max 10-15 nodes per diagram
2. **Use consistent naming**: Match code/domain terminology
3. **Add descriptions**: Use notes and labels for clarity
4. **Version control**: Diagrams are text, easy to diff and merge
5. **Test rendering**: Preview in GitHub before committing

## Resources

- [Mermaid Official Documentation](https://mermaid.js.org/)
- [Mermaid Live Editor](https://mermaid.live/) - Online playground
- [GitHub Mermaid Support](https://github.blog/2022-02-14-include-diagrams-markdown-files-mermaid/)
