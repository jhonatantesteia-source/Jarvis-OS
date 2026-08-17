const { app, BrowserWindow } = require("electron");
const path = require("node:path");
const isDev = !app.isPackaged;
app.disableHardwareAcceleration();
app.commandLine.appendSwitch("disable-gpu");
app.commandLine.appendSwitch("disable-gpu-compositing");
function createWindow() {
  const win = new BrowserWindow({
    width: 1440, height: 900, minWidth: 1100, minHeight: 700,
    backgroundColor: "#05070a",
    webPreferences: { preload: path.join(__dirname, "preload.cjs"), contextIsolation: true, nodeIntegration: false }
  });
  win.webContents.on("did-fail-load", (_event, errorCode, errorDescription, validatedURL) => {
    console.error("[jarvis] falha ao carregar:", errorCode, errorDescription, validatedURL);
  });
  win.webContents.on("render-process-gone", (_event, details) => {
    console.error("[jarvis] processo de renderização morreu:", details.reason, details);
  });
  win.webContents.on("did-finish-load", () => {
    console.log("[jarvis] página carregada com sucesso");
  });
  if (isDev) {
    win.loadURL("http://127.0.0.1:5173");
    win.webContents.openDevTools({ mode: "detach" });
  } else {
    win.loadFile(path.join(__dirname, "../renderer/dist/index.html"));
  }
}
app.whenReady().then(() => { createWindow(); app.on("activate", () => { if (!BrowserWindow.getAllWindows().length) createWindow(); }); });
app.on("window-all-closed", () => { if (process.platform !== "darwin") app.quit(); });
