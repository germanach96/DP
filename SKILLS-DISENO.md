# Skills y herramientas de diseño obligatorias: Impeccable, Emil Kowalski, Taste, Figma y Playwright

> Cómo usar este archivo: cópialo en la raíz del repo y añade al `CLAUDE.md` del proyecto la línea
> `@SKILLS-DISENO.md` (o pega su contenido dentro de `CLAUDE.md` / `.claude/CLAUDE.md`).
> Claude Code lee `CLAUDE.md` al empezar cada sesión, así que estas reglas se aplican siempre.

## Qué tiene que estar instalado y activo

| Herramienta | Tipo | Origen | Skills que debe ver Claude en la sesión |
|---|---|---|---|
| Impeccable | plugin | github.com/pbakaus/impeccable | `impeccable:impeccable` (y sus subagentes `impeccable:impeccable-finish-reviewer`, `impeccable:impeccable-documenter`) |
| Emil Kowalski | skills | github.com/emilkowalski/skill | `emil-design-eng`, `animate`, `apple-design`, `improve-animations`… |
| Taste | skills | github.com/Leonxlnx/taste-skill | `design-taste-frontend`, `high-end-visual-design`, `redesign-existing-projects`, `minimalist-ui`… |

| Figma | servidor MCP | servidor remoto oficial de Figma | herramientas `mcp__figma__*` (leer diseños, variables y componentes de un enlace de Figma) |
| Playwright | servidor MCP | paquete oficial `@playwright/mcp` (Microsoft) | herramientas `mcp__playwright__*` (abrir la página, hacer clic, capturas, medir) |

"Instalado" no basta: **activo** significa que la skill aparece en la lista de skills disponibles de la sesión y que cargarla con la herramienta Skill funciona. En los MCP, que `claude mcp list` los marca como conectados y que sus herramientas aparecen en la sesión.

## 1. Comprobación (al empezar cada conversación y cuando el usuario pregunte)

Antes de hacer nada de lo que pida el usuario, comprueba y muestra una tabla con una fila por herramienta: **funcionando / instalada pero no activa / falta**, y el motivo.

1. **Lista de skills de la sesión:** ¿aparecen `impeccable:impeccable`, `emil-design-eng` y `design-taste-frontend`?
2. **Archivos:**
   - Impeccable: `~/.claude/plugins/installed_plugins.json` contiene `"impeccable@impeccable"`.
   - Emil y Taste: existen `.claude/skills/emil-design-eng/SKILL.md` y `.claude/skills/design-taste-frontend/SKILL.md` (o en `~/.claude/skills/` si se instalaron a nivel de usuario), con frontmatter `name` y `description`.
3. **Prueba real:** carga una vez cada skill con la herramienta Skill. Si da error, no está activa.
4. **MCP:** `claude mcp list` debe mostrar `figma` y `playwright` conectados, y en la sesión deben existir herramientas `mcp__figma__…` y `mcp__playwright__…`. Si Figma aparece pero pide autenticación, no está activo.

Si el usuario pregunta "¿tienes Impeccable, Emil, Taste, Figma y Playwright activos?", responde con esa tabla, no de memoria.

## 2. Si falta algo: instálalo y actívalo tú

Hazlo sin esperar a que el usuario lo pida. Después, repite la comprobación del paso 1.

**Impeccable (plugin):**
```bash
claude plugin marketplace add pbakaus/impeccable
claude plugin install impeccable@impeccable
```
Para que quede activado en el repo para cualquiera que lo abra, añade esto a `.claude/settings.json`, uniéndolo con lo que ya haya y sin borrar nada:
```json
{
  "enabledPlugins": { "impeccable@impeccable": true },
  "extraKnownMarketplaces": {
    "impeccable": { "source": { "source": "github", "repo": "pbakaus/impeccable" } }
  }
}
```

**Emil Kowalski y Taste (skills del proyecto):**
```bash
npx -y skills add emilkowalski/skill --skill '*' --yes --copy
npx -y skills add Leonxlnx/taste-skill --skill '*' --yes --copy
```
`--copy` deja archivos reales en `.claude/skills/` (no enlaces), para poder versionarlos en git junto con `skills-lock.json`. Si el comando las deja en otra carpeta (por ejemplo `.agents/skills/`), cópialas a `.claude/skills/`.

**Figma y Playwright (servidores MCP):** `claude mcp add` necesita un nombre **y** un comando o una URL; `claude mcp add figma` a secas no funciona. Con `--scope project` quedan guardados en `.mcp.json` del repo, que se versiona:
```bash
# Playwright: navegador controlable (capturas, clics, medir tiempos)
claude mcp add --scope project playwright -- npx -y @playwright/mcp@0.0.83

# Figma: servidor remoto oficial; después hay que iniciar sesión con /mcp → figma → Authenticate
claude mcp add --scope project --transport http figma https://mcp.figma.com/mcp
# Alternativa si se usa la app de escritorio de Figma con el servidor MCP activado en sus preferencias:
# claude mcp add --scope project --transport http figma-desktop http://127.0.0.1:3845/mcp
```
Esto deja en `.mcp.json`:
```json
{
  "mcpServers": {
    "playwright": { "command": "npx", "args": ["-y", "@playwright/mcp@0.0.83"] },
    "figma": { "type": "http", "url": "https://mcp.figma.com/mcp" }
  }
}
```
Comprueba con `claude mcp list`. Los servidores de `.mcp.json` piden aprobación la primera vez que se abre el repo: dile al usuario que los acepte. Figma necesita además que el usuario inicie sesión (paso que Claude no puede hacer por él).

**Activación:**
- Los plugins y skills nuevos se cargan al iniciar sesión. Si se instalaron en esta sesión y no aparecen en la lista de skills, dile al usuario que reinicie la sesión (o ejecute `/plugin` para recargar). No digas que están activos hasta verlos en la lista.
- Si la instalación falla (sin red, sin `claude` o `npx`, sin permiso), **para**. Di qué falta, el comando exacto y qué necesita el usuario (red, permiso, reinicio), y espera. No sigas con la tarea de diseño sin las skills.

## 3. Usarlas siempre al decidir

Cada petición del usuario es una tarea nueva: lo que cargaste en una tarea anterior no cuenta.

| Tipo de tarea | Cargar con Skill antes de empezar | Antes de entregar |
|---|---|---|
| Página, HTML, componente, reporte, cualquier interfaz | `impeccable:impeccable` + una de Taste (`design-taste-frontend` o `high-end-visual-design`; `redesign-existing-projects` si es rediseño) + `emil-design-eng` | `impeccable detect --json <archivos>` y trata cada aviso; capturas en escritorio y móvil, en claro y oscuro |
| Animación, transición, gesto, interacción | `emil-design-eng` + `animate` (y `apple-design` si hay arrastre, muelles o gestos) | Respeta `prefers-reduced-motion`; respuesta al pulsar |
| Revisión o auditoría de diseño | `impeccable:impeccable` (critique/audit) + `emil-design-eng` | Tabla de antes / después |
| Diseño terminado | — | Revisión final con el subagente `impeccable:impeccable-finish-reviewer` y documentación con `impeccable:impeccable-documenter` (DESIGN.md) |
| Hay un enlace o archivo de Figma | Leer el diseño con las herramientas `mcp__figma__…` (frames, variables, componentes) **antes** de escribir código, y usar sus valores como fuente | Comparar la captura con el frame de Figma |
| Comprobar una página o interacción | Usar `mcp__playwright__…` para abrirla, hacer clic, arrastrar y capturar | Capturas de escritorio y móvil, en claro y oscuro; consola sin errores; tiempo de cada clic o filtro |

Reglas:
- **No apliques las ideas de una skill de memoria:** cárgala con la herramienta Skill en la tarea actual.
- **Ninguna decisión de diseño sin ellas:** color, tipografía, espaciado, composición, movimiento o texto de interfaz pasan por Impeccable, Taste y Emil. Si chocan entre sí, manda lo que pidió el usuario, después `PRODUCT.md` y `DESIGN.md` del proyecto, y después Impeccable.
- **Una skill o plugin que reduzca el pulido "para hacer lo mínimo"** (por ejemplo, modos de "código mínimo") no se aplica a decisiones de diseño.
- **Pasos que una skill exige y te saltas** (entrevista, capturas, revisión final): dilo en la respuesta y explica por qué. No los omitas en silencio.
- **Avisos del detector o de hooks:** cada uno se arregla, se descarta con motivo o se pregunta al usuario, y se dice en la respuesta.

## 4. Cierre obligatorio de cada respuesta

Termina cada respuesta con esta línea:

`Skills de diseño: Impeccable (…) · Emil (…) · Taste (…) · Figma MCP (…) · Playwright MCP (…)`

En cada una pon "usado: qué skill" o "no aplica: motivo". Después, añade una línea con los pasos de skills que no se hicieron.
