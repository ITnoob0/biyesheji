import fs from 'node:fs'
import path from 'node:path'
import { spawn } from 'node:child_process'
import { fileURLToPath } from 'node:url'

const PROTOCOL_VERSION = '2025-06-18'
const EDITOR_URL = 'http://127.0.0.1:3005/'
const EXTENSION_PORT = '4333'
const HTTP_PORT = '3005'
const SCRIPT_DIR = path.dirname(fileURLToPath(import.meta.url))
const WORKSPACE_ROOT = path.resolve(SCRIPT_DIR, '..')
const DEBUG_LOG_PATH = path.join(WORKSPACE_ROOT, '.codex-runtime', 'drawio-bridge', 'drawio-bridge-debug.log')

let inputBuffer = Buffer.alloc(0)
let drawioProcess = null
let loggedRawInputPreview = false
let transportMode = 'unknown'
let editorStatus = {
  state: 'starting',
  message: `Launching draw.io editor at ${EDITOR_URL}`,
}

function appendDebugLog(message) {
  try {
    fs.mkdirSync(path.dirname(DEBUG_LOG_PATH), { recursive: true })
    fs.appendFileSync(DEBUG_LOG_PATH, `[${new Date().toISOString()}] ${message}\n`, 'utf8')
  } catch {
    // ignore logging failures
  }
}

function formatBufferPreview(buffer, limit = 256) {
  const slice = buffer.subarray(0, Math.min(buffer.length, limit))
  const utf8 = slice
    .toString('utf8')
    .replaceAll('\r', '\\r')
    .replaceAll('\n', '\\n')
  const hex = Array.from(slice)
    .map(byte => byte.toString(16).padStart(2, '0'))
    .join(' ')
  return {
    utf8,
    hex,
    truncated: buffer.length > limit,
  }
}

function walkForFile(root, predicate) {
  const stack = [root]

  while (stack.length > 0) {
    const current = stack.pop()
    let entries = []

    try {
      entries = fs.readdirSync(current, { withFileTypes: true })
    } catch {
      continue
    }

    for (const entry of entries) {
      const fullPath = path.join(current, entry.name)

      if (entry.isDirectory()) {
        stack.push(fullPath)
        continue
      }

      if (predicate(fullPath)) {
        return fullPath
      }
    }
  }

  return null
}

function findDrawioEntry() {
  const localRuntimeEntry = path.join(WORKSPACE_ROOT, '.codex-runtime', 'drawio-bridge', 'node_modules', 'drawio-mcp-server', 'build', 'index.js')
  if (fs.existsSync(localRuntimeEntry)) {
    return localRuntimeEntry
  }

  const localAppData = process.env.LOCALAPPDATA
  if (!localAppData) {
    throw new Error('LOCALAPPDATA is not set; cannot locate drawio-mcp-server cache')
  }

  const npmCacheRoot = path.join(localAppData, 'Temp', 'npm-cache', '_npx')
  const suffix = path.join('node_modules', 'drawio-mcp-server', 'build', 'index.js')
  const match = walkForFile(npmCacheRoot, fullPath => fullPath.endsWith(suffix))

  if (!match) {
    throw new Error(`Could not locate drawio-mcp-server build entry under ${npmCacheRoot}`)
  }

  return match
}

function writeStderr(message) {
  appendDebugLog(`stderr: ${message}`)
  process.stderr.write(`${message}\n`)
}

function ensureWorkspacePath(targetPath) {
  const resolvedPath = path.resolve(WORKSPACE_ROOT, targetPath)
  const relativePath = path.relative(WORKSPACE_ROOT, resolvedPath)

  if (relativePath.startsWith('..') || path.isAbsolute(relativePath)) {
    throw new Error(`Path escapes workspace root: ${targetPath}`)
  }

  return resolvedPath
}

function escapeXml(value) {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&apos;')
}

function buildToolList() {
  return [
    {
      name: 'drawio_open_editor',
      description: 'Return the local draw.io editor URL started by the bridge.',
      annotations: {
        title: 'Open draw.io editor URL',
        readOnlyHint: true,
        destructiveHint: false,
        idempotentHint: true,
        openWorldHint: false,
      },
      inputSchema: {
        type: 'object',
        properties: {},
        additionalProperties: false,
      },
    },
    {
      name: 'drawio_get_status',
      description: 'Return the current draw.io editor and bridge runtime status.',
      annotations: {
        title: 'Get draw.io bridge status',
        readOnlyHint: true,
        destructiveHint: false,
        idempotentHint: true,
        openWorldHint: false,
      },
      inputSchema: {
        type: 'object',
        properties: {},
        additionalProperties: false,
      },
    },
    {
      name: 'drawio_create_diagram_file',
      description:
        'Create a minimal .drawio file inside the current workspace so it can be opened in the local draw.io editor.',
      annotations: {
        title: 'Create draw.io diagram file',
        readOnlyHint: false,
        destructiveHint: false,
        idempotentHint: false,
        openWorldHint: false,
      },
      inputSchema: {
        type: 'object',
        properties: {
          outputPath: {
            type: 'string',
            description: 'Workspace-relative output path for the .drawio file, e.g. Paper/figures/system-architecture.drawio',
          },
          title: {
            type: 'string',
            description: 'Diagram title shown in the starter shape.',
          },
          pageName: {
            type: 'string',
            description: 'Optional draw.io page name. Defaults to Page-1.',
          },
          overwrite: {
            type: 'boolean',
            description: 'Whether to overwrite an existing file. Defaults to false.',
          },
        },
        required: ['outputPath', 'title'],
        additionalProperties: false,
      },
    },
  ]
}

function buildDiagramXml(title, pageName) {
  const escapedTitle = escapeXml(title)
  const escapedPageName = escapeXml(pageName)

  return `<?xml version="1.0" encoding="UTF-8"?>
<mxfile host="app.diagrams.net" modified="2026-04-18T00:00:00.000Z" agent="Codex Drawio Bridge" version="29.6.10">
  <diagram id="page-1" name="${escapedPageName}">
    <mxGraphModel dx="1200" dy="900" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="1169" pageHeight="827" math="0" shadow="0">
      <root>
        <mxCell id="0" />
        <mxCell id="1" parent="0" />
        <mxCell id="title" value="${escapedTitle}" style="rounded=1;whiteSpace=wrap;html=1;fontSize=20;fontStyle=1;strokeColor=#1f2937;fillColor=#e0f2fe;" vertex="1" parent="1">
          <mxGeometry x="180" y="120" width="320" height="100" as="geometry" />
        </mxCell>
        <mxCell id="hint" value="Open this file in draw.io and continue editing." style="rounded=1;whiteSpace=wrap;html=1;fontSize=14;strokeColor=#94a3b8;fillColor=#f8fafc;" vertex="1" parent="1">
          <mxGeometry x="180" y="260" width="320" height="70" as="geometry" />
        </mxCell>
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>
`
}

function sendMessage(payload) {
  const json = JSON.stringify(payload)
  appendDebugLog(`send: ${json.slice(0, 300)}`)

  if (transportMode === 'line-json') {
    process.stdout.write(`${json}\n`)
    return
  }

  const header = `Content-Length: ${Buffer.byteLength(json, 'utf8')}\r\n\r\n`
  process.stdout.write(header)
  process.stdout.write(json)
}

function sendResult(id, result) {
  sendMessage({
    jsonrpc: '2.0',
    id,
    result,
  })
}

function sendError(id, code, message) {
  sendMessage({
    jsonrpc: '2.0',
    id,
    error: {
      code,
      message,
    },
  })
}

function buildResources() {
  return [
    {
      uri: 'drawio://editor',
      name: 'Draw.io Editor',
      description: 'Local draw.io editor URL started by the compatibility MCP bridge.',
      mimeType: 'text/plain',
    },
    {
      uri: 'drawio://status',
      name: 'Draw.io Status',
      description: 'Current local draw.io bridge and editor status.',
      mimeType: 'application/json',
    },
  ]
}

function buildStatusPayload() {
  return {
    editorUrl: EDITOR_URL,
    extensionPort: Number(EXTENSION_PORT),
    httpPort: Number(HTTP_PORT),
    workspaceRoot: WORKSPACE_ROOT,
    ...editorStatus,
  }
}

function buildToolTextResult(text) {
  return {
    content: [
      {
        type: 'text',
        text,
      },
    ],
  }
}

function handleToolCall(id, params) {
  const toolName = params?.name
  const args = params?.arguments ?? {}

  switch (toolName) {
    case 'drawio_open_editor':
      sendResult(
        id,
        buildToolTextResult(
          `Draw.io editor is available at ${EDITOR_URL}\nCurrent state: ${editorStatus.state}\n${editorStatus.message}`,
        ),
      )
      return

    case 'drawio_get_status':
      sendResult(id, buildToolTextResult(JSON.stringify(buildStatusPayload(), null, 2)))
      return

    case 'drawio_create_diagram_file': {
      try {
        const outputPath = args.outputPath
        const title = args.title
        const pageName = args.pageName || 'Page-1'
        const overwrite = args.overwrite === true

        if (typeof outputPath !== 'string' || !outputPath.endsWith('.drawio')) {
          sendError(id, -32602, 'outputPath must be a workspace-relative path ending with .drawio')
          return
        }

        if (typeof title !== 'string' || title.trim().length === 0) {
          sendError(id, -32602, 'title must be a non-empty string')
          return
        }

        const absolutePath = ensureWorkspacePath(outputPath)
        if (!overwrite && fs.existsSync(absolutePath)) {
          sendError(id, -32003, `File already exists: ${absolutePath}`)
          return
        }

        fs.mkdirSync(path.dirname(absolutePath), { recursive: true })
        fs.writeFileSync(absolutePath, buildDiagramXml(title.trim(), String(pageName)), 'utf8')

        sendResult(
          id,
          buildToolTextResult(
            `Created draw.io file at ${absolutePath}\nOpen ${EDITOR_URL} and load the file to continue editing.`,
          ),
        )
      } catch (error) {
        sendError(id, -32004, error instanceof Error ? error.message : String(error))
      }
      return
    }

    default:
      sendError(id, -32601, `Unknown tool: ${toolName}`)
  }
}

function handleRequest(message) {
  const { id, method, params } = message
  appendDebugLog(`request: method=${method} id=${id ?? 'null'}`)

  switch (method) {
    case 'initialize':
      transportMode = transportMode === 'unknown' ? 'line-json' : transportMode
      sendResult(id, {
        protocolVersion:
          typeof params?.protocolVersion === 'string' && params.protocolVersion.trim().length > 0
            ? params.protocolVersion
            : PROTOCOL_VERSION,
        capabilities: {
          resources: {
            subscribe: false,
            listChanged: false,
          },
          tools: {
            listChanged: false,
          },
        },
        serverInfo: {
          name: 'drawio-compat-bridge',
          version: '0.2.0',
        },
      })
      return

    case 'notifications/initialized':
      return

    case 'ping':
      sendResult(id, {})
      return

    case 'resources/list':
      sendResult(id, {
        resources: buildResources(),
      })
      return

    case 'tools/list':
      sendResult(id, {
        tools: buildToolList(),
      })
      return

    case 'tools/call':
      handleToolCall(id, params)
      return

    case 'resources/templates/list':
      sendResult(id, {
        resourceTemplates: [],
      })
      return

    case 'resources/read':
      if (params?.uri === 'drawio://editor') {
        sendResult(id, {
          contents: [
            {
              uri: 'drawio://editor',
              mimeType: 'text/plain',
              text: `${EDITOR_URL}\nOpen this address in a browser to use the local draw.io editor started by the bridge.`,
            },
          ],
        })
        return
      }

      if (params?.uri === 'drawio://status') {
        sendResult(id, {
          contents: [
            {
              uri: 'drawio://status',
              mimeType: 'application/json',
              text: JSON.stringify(
                {
                  ...buildStatusPayload(),
                },
                null,
                2,
              ),
            },
          ],
        })
        return
      }

      sendError(id, -32002, `Unknown resource URI: ${params?.uri ?? 'undefined'}`)
      return

    default:
      sendError(id, -32601, `Method not found: ${method}`)
  }
}

function tryProcessLineDelimitedInput() {
  while (true) {
    const newlineIndex = inputBuffer.indexOf(Buffer.from('\n'))
    if (newlineIndex === -1) {
      return false
    }

    const lineBuffer = inputBuffer.subarray(0, newlineIndex)
    inputBuffer = inputBuffer.subarray(newlineIndex + 1)

    const lineText = lineBuffer.toString('utf8').trim()
    if (!lineText) {
      continue
    }

    try {
      const message = JSON.parse(lineText)
      transportMode = 'line-json'
      handleRequest(message)
      return true
    } catch (error) {
      writeStderr(`drawio bridge: failed to parse line-delimited request: ${error instanceof Error ? error.message : String(error)}`)
      continue
    }
  }
}

function processInput() {
  while (true) {
    const trimmedPrefix = inputBuffer.toString('utf8', 0, Math.min(inputBuffer.length, 32)).trimStart()
    if (trimmedPrefix.startsWith('{') || trimmedPrefix.startsWith('[')) {
      const processedLine = tryProcessLineDelimitedInput()
      if (processedLine) {
        continue
      }
    }

    const crlfHeaderEnd = inputBuffer.indexOf(Buffer.from('\r\n\r\n'))
    const lfHeaderEnd = inputBuffer.indexOf(Buffer.from('\n\n'))
    const headerEnd =
      crlfHeaderEnd === -1
        ? lfHeaderEnd
        : lfHeaderEnd === -1
          ? crlfHeaderEnd
          : Math.min(crlfHeaderEnd, lfHeaderEnd)

    if (headerEnd === -1) {
      if (!loggedRawInputPreview && inputBuffer.length > 0) {
        const preview = formatBufferPreview(inputBuffer)
        appendDebugLog(
          `stdin preview utf8=${preview.utf8}${preview.truncated ? '...[truncated]' : ''} hex=${preview.hex}${preview.truncated ? ' ...[truncated]' : ''}`,
        )
        loggedRawInputPreview = true
      }
      return
    }

    const separatorLength =
      inputBuffer.subarray(headerEnd, headerEnd + 4).equals(Buffer.from('\r\n\r\n')) ? 4 : 2

    const headerText = inputBuffer.subarray(0, headerEnd).toString('utf8')
    const contentLengthLine = headerText
      .split(/\r?\n/)
      .find(line => line.toLowerCase().startsWith('content-length:'))

    if (!contentLengthLine) {
      writeStderr('drawio bridge: missing Content-Length header')
      inputBuffer = inputBuffer.subarray(headerEnd + separatorLength)
      continue
    }

    const contentLength = Number(contentLengthLine.split(':')[1]?.trim())
    if (!Number.isFinite(contentLength) || contentLength < 0) {
      writeStderr(`drawio bridge: invalid Content-Length header: ${contentLengthLine}`)
      inputBuffer = inputBuffer.subarray(headerEnd + separatorLength)
      continue
    }

    const bodyStart = headerEnd + separatorLength
    const messageEnd = bodyStart + contentLength

    if (inputBuffer.length < messageEnd) {
      return
    }

    const bodyText = inputBuffer.subarray(bodyStart, messageEnd).toString('utf8')
    inputBuffer = inputBuffer.subarray(messageEnd)
    transportMode = 'content-length'

    try {
      handleRequest(JSON.parse(bodyText))
    } catch (error) {
      writeStderr(`drawio bridge: failed to parse or handle request: ${error instanceof Error ? error.message : String(error)}`)
    }
  }
}

function startDrawioEditor() {
  try {
    const drawioEntry = findDrawioEntry()
    drawioProcess = spawn(
      process.execPath,
      [drawioEntry, '--editor', '--transport', 'http', '--extension-port', EXTENSION_PORT, '--http-port', HTTP_PORT],
      {
        stdio: ['ignore', 'pipe', 'pipe'],
        env: process.env,
      },
    )

    drawioProcess.stdout.on('data', chunk => {
      const text = chunk.toString('utf8').trim()
      if (text) {
        writeStderr(`drawio editor stdout: ${text}`)
      }
    })

    drawioProcess.stderr.on('data', chunk => {
      const text = chunk.toString('utf8').trim()
      if (text) {
        writeStderr(`drawio editor stderr: ${text}`)
      }
    })

    drawioProcess.on('spawn', () => {
      editorStatus = {
        state: 'running',
        message: `draw.io editor is available at ${EDITOR_URL}`,
      }
    })

    drawioProcess.on('exit', (code, signal) => {
      editorStatus = {
        state: 'stopped',
        message: `draw.io editor exited with code ${code ?? 'null'} and signal ${signal ?? 'null'}`,
      }
    })
  } catch (error) {
    editorStatus = {
      state: 'error',
      message: error instanceof Error ? error.message : String(error),
    }
    writeStderr(`drawio bridge: failed to start editor: ${editorStatus.message}`)
  }
}

process.stdin.on('data', chunk => {
  appendDebugLog(`stdin chunk bytes=${chunk.length}`)
  inputBuffer = Buffer.concat([inputBuffer, chunk])
  processInput()
})

process.stdin.on('end', () => {
  if (drawioProcess && !drawioProcess.killed) {
    drawioProcess.kill('SIGTERM')
  }
})

process.on('SIGINT', () => {
  if (drawioProcess && !drawioProcess.killed) {
    drawioProcess.kill('SIGINT')
  }
  process.exit(0)
})

process.on('SIGTERM', () => {
  if (drawioProcess && !drawioProcess.killed) {
    drawioProcess.kill('SIGTERM')
  }
  process.exit(0)
})

startDrawioEditor()
appendDebugLog(`bridge started cwd=${process.cwd()} argv=${JSON.stringify(process.argv)}`)
