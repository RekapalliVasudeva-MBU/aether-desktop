import { app, BrowserWindow, ipcMain } from 'electron';
import path from 'path';
import { spawn, ChildProcess } from 'child_process';
import http from 'http';

let mainWindow: BrowserWindow | null = null;
let pythonProcess: ChildProcess | null = null;
const BACKEND_PORT = 8732;

function checkBackendHealth(): Promise<boolean> {
  return new Promise((resolve) => {
    const req = http.get(`http://127.0.0.1:${BACKEND_PORT}/api/health`, (res) => {
      resolve(res.statusCode === 200);
    });
    req.on('error', () => resolve(false));
    req.setTimeout(1000, () => {
      req.destroy();
      resolve(false);
    });
  });
}

async function waitForBackend(maxAttempts = 40): Promise<boolean> {
  for (let i = 0; i < maxAttempts; i++) {
    const healthy = await checkBackendHealth();
    if (healthy) return true;
    await new Promise((r) => setTimeout(r, 500));
  }
  return false;
}

function startPythonBackend() {
  const isDev = !app.isPackaged;
  const projectRoot = isDev ? path.join(__dirname, '..') : path.join(process.resourcesPath, 'engine');
  const scriptPath = path.join(projectRoot, 'desktop_app.py');

  console.log('[Electron] Starting Python Backend from:', scriptPath);
  
  pythonProcess = spawn('python', [scriptPath, '--headless'], {
    cwd: projectRoot,
    env: { ...process.env, AETHER_PORT: String(BACKEND_PORT), AETHER_HEADLESS: '1' },
    stdio: 'inherit',
  });

  pythonProcess.on('error', (err) => {
    console.error('[Electron] Failed to start Python backend:', err);
  });

  pythonProcess.on('exit', (code, signal) => {
    console.log(`[Electron] Python backend exited with code ${code} / signal ${signal}`);
  });
}

async function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 840,
    minWidth: 960,
    minHeight: 640,
    title: 'Aether Desktop OS',
    icon: path.join(__dirname, '../desktop_ui/logo.ico'),
    backgroundColor: '#0b0b12',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true,
    },
    autoHideMenuBar: true,
  });

  // Start Python backend
  startPythonBackend();

  // Wait until backend responds
  const isReady = await waitForBackend();
  if (isReady) {
    console.log('[Electron] Backend ready, loading interface...');
    mainWindow.loadURL(`http://127.0.0.1:${BACKEND_PORT}/ui/`);
  } else {
    console.warn('[Electron] Backend health check timed out, loading local file...');
    mainWindow.loadFile(path.join(__dirname, '../desktop_ui/index.html'));
  }

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

// Window control IPC handlers
ipcMain.on('window-minimize', () => {
  if (mainWindow) mainWindow.minimize();
});

ipcMain.on('window-maximize', () => {
  if (mainWindow) {
    if (mainWindow.isMaximized()) mainWindow.unmaximize();
    else mainWindow.maximize();
  }
});

ipcMain.on('window-close', () => {
  if (mainWindow) mainWindow.close();
});

app.whenReady().then(createWindow);

app.on('window-all-closed', () => {
  if (pythonProcess) {
    try {
      pythonProcess.kill();
    } catch (e) {}
  }
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('quit', () => {
  if (pythonProcess) {
    try {
      pythonProcess.kill();
    } catch (e) {}
  }
});
