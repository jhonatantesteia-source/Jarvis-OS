const { app, BrowserWindow } = require("electron");
const path = require("node:path");
const isDev = !app.isPackaged;
function createWindow() {
  const win = new BrowserWindow({
    width: 1440, height: 900, minWidth: 1100, minHeight: 700,
    backgroundColor: "#05070a",
    webPreferences: { preload: path.join(__dirname, "preload.cjs"), contextIsolation: true, nodeIntegration: false }
  });
  if (isDev) win.loadURL("http://127.0.0.1:5173");
  else win.loadFile(path.join(__dirname, "../renderer/dist/index.html"));
}
app.whenReady().then(() => { createWindow(); app.on("activate", () => { if (!BrowserWindow.getAllWindows().length) createWindow(); }); });
app.on("window-all-closed", () => { if (process.platform !== "darwin") app.quit(); });
