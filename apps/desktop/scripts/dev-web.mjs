import http from 'node:http'
import { readFile } from 'node:fs/promises'
import { extname, join, normalize, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = fileURLToPath(new URL('.', import.meta.url))
const root = resolve(__dirname, '../../web-ui')
const host = '127.0.0.1'
const port = 1420

const contentTypes = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'application/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8'
}

const server = http.createServer(async (req, res) => {
  const path = req.url === '/' ? '/index.html' : req.url
  const safePath = normalize(path).replace(/^(\.\.[/\\])+/, '')
  const filePath = join(root, safePath)

  try {
    const data = await readFile(filePath)
    res.writeHead(200, { 'Content-Type': contentTypes[extname(filePath)] ?? 'application/octet-stream' })
    res.end(data)
  } catch {
    res.writeHead(404, { 'Content-Type': 'text/plain; charset=utf-8' })
    res.end('Not found')
  }
})

server.listen(port, host, () => {
  console.log(`OSRS Clicker desktop UI dev server on http://${host}:${port}`)
})
