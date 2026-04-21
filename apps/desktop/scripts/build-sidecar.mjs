import { chmodSync, copyFileSync, existsSync, mkdirSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { execSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'

const __dirname = dirname(fileURLToPath(import.meta.url))
const desktopRoot = resolve(__dirname, '..')
const repoRoot = resolve(desktopRoot, '../..')
const binariesDir = resolve(desktopRoot, 'src-tauri', 'binaries')

mkdirSync(binariesDir, { recursive: true })

const targetTriple = resolveTargetTriple(process.platform, process.arch)
const sourceBinary = resolve(repoRoot, '.build', 'release', process.platform === 'win32' ? 'osrs-clicker-service.exe' : 'osrs-clicker-service')
const targetBinary = resolve(
  binariesDir,
  process.platform === 'win32'
    ? `osrs-clicker-service-${targetTriple}.exe`
    : `osrs-clicker-service-${targetTriple}`
)

console.log(`Building Swift sidecar for ${targetTriple}...`)
execSync('swift build -c release --product osrs-clicker-service', {
  cwd: repoRoot,
  stdio: 'inherit'
})

if (!existsSync(sourceBinary)) {
  throw new Error(`Missing built sidecar at ${sourceBinary}`)
}

copyFileSync(sourceBinary, targetBinary)
if (process.platform !== 'win32') {
  chmodSync(targetBinary, 0o755)
}

console.log(`Sidecar ready at ${targetBinary}`)

function resolveTargetTriple(platform, arch) {
  if (platform === 'darwin' && arch === 'arm64') return 'aarch64-apple-darwin'
  if (platform === 'darwin' && arch === 'x64') return 'x86_64-apple-darwin'
  if (platform === 'linux' && arch === 'x64') return 'x86_64-unknown-linux-gnu'
  if (platform === 'linux' && arch === 'arm64') return 'aarch64-unknown-linux-gnu'
  if (platform === 'win32' && arch === 'x64') return 'x86_64-pc-windows-msvc'
  throw new Error(`Unsupported host platform for sidecar packaging: ${platform}/${arch}`)
}
