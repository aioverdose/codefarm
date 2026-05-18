# Local Agent App Factory

A standalone Next.js shell for running CodeFarm local autonomous agents in the background.

## Run locally during development

```powershell
cd G:\codefarm\product-app
npm install
npm run dev
```

The app opens at:

`http://127.0.0.1:3000`

The app starts/proxies the local CodeFarm service at:

`http://127.0.0.1:8765`

## Downloadable bundle behavior

The packaged ZIP contains:

- `app/` - Next.js product UI
- `runtime/codefarm/` - local sandboxed agent runtime
- `start-local.bat` - Windows launcher

Generated apps stay inside:

`runtime\codefarm\projects\<project-id>\app`

Exports are downloaded as ZIPs through the app UI.

## Security posture

- The browser talks only to the Next.js API routes.
- Next.js proxies to `127.0.0.1:8765` only.
- Project IDs and organism IDs are sanitized.
- Generated files are kept under the CodeFarm runtime project sandbox.
- CodeFarm function catalog is hidden behind `CODEFARM_FUNCTIONS_TOKEN` and is not linked in the UI.