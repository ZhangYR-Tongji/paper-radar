const { app, BrowserWindow, dialog } = require("electron");
const { spawn, spawnSync } = require("node:child_process");
const fs = require("node:fs");
const http = require("node:http");
const net = require("node:net");
const os = require("node:os");
const path = require("node:path");

const BACKEND_PORT = 8000;
const FRONTEND_PORT = 3000;
const CONDA_ENV_NAME = process.env.PAPER_RADAR_CONDA_ENV || "paper-radar";
const STARTUP_TIMEOUT_MS = 60_000;

let mainWindow = null;
let repoRoot = null;
const services = [];

const gotLock = app.requestSingleInstanceLock();
if (!gotLock) {
  app.quit();
} else {
  app.on("second-instance", () => {
    if (!mainWindow) {
      return;
    }
    if (mainWindow.isMinimized()) {
      mainWindow.restore();
    }
    mainWindow.focus();
  });

  app.whenReady().then(startApplication);
}

app.on("before-quit", stopServices);

app.on("window-all-closed", () => {
  app.quit();
});

async function startApplication() {
  try {
    repoRoot = findRepoRoot();
    const logDir = path.join(repoRoot, ".runtime", "logs");
    fs.mkdirSync(logDir, { recursive: true });

    await assertPortFree(BACKEND_PORT, "Backend");
    await assertPortFree(FRONTEND_PORT, "Frontend");

    const runtime = await findRuntime();
    const serviceEnv = createServiceEnv(runtime.envDir);
    const nextCli = path.join(
      repoRoot,
      "frontend",
      "node_modules",
      "next",
      "dist",
      "bin",
      "next",
    );
    if (!fs.existsSync(nextCli)) {
      throw new Error(
        "Next.js CLI was not found. Run npm install in the frontend directory.",
      );
    }

    const backend = startService({
      name: "backend",
      command: runtime.python,
      args: [
        "-m",
        "uvicorn",
        "app.main:app",
        "--host",
        "127.0.0.1",
        "--port",
        String(BACKEND_PORT),
      ],
      cwd: path.join(repoRoot, "backend"),
      env: serviceEnv,
      logPath: path.join(logDir, "backend.log"),
    });
    await waitForHttp(`http://127.0.0.1:${BACKEND_PORT}/api/health`, "Backend", [
      backend,
    ]);

    const frontend = startService({
      name: "frontend",
      command: runtime.node,
      args: [nextCli, "start", "-p", String(FRONTEND_PORT)],
      cwd: path.join(repoRoot, "frontend"),
      env: {
        ...serviceEnv,
        NODE_ENV: "production",
        NEXT_PUBLIC_API_BASE_URL: `http://localhost:${BACKEND_PORT}/api`,
        NEXT_TELEMETRY_DISABLED: "1",
      },
      logPath: path.join(logDir, "frontend.log"),
    });
    await waitForHttp(`http://localhost:${FRONTEND_PORT}`, "Frontend", [
      backend,
      frontend,
    ]);

    createMainWindow();
  } catch (error) {
    stopServices();
    await dialog.showMessageBox({
      type: "error",
      title: "Paper Radar startup failed",
      message: "Paper Radar could not start.",
      detail: formatStartupError(error),
    });
    app.quit();
  }
}

function createMainWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 840,
    minWidth: 1000,
    minHeight: 700,
    show: false,
    title: "Paper Radar",
    icon: path.join(repoRoot, "desktop", "assets", "icon.png"),
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  });

  mainWindow.once("ready-to-show", () => {
    mainWindow.show();
  });

  mainWindow.on("closed", () => {
    mainWindow = null;
  });

  mainWindow.loadURL(`http://localhost:${FRONTEND_PORT}`);
}

function findRepoRoot() {
  const candidates = [
    process.env.PAPER_RADAR_ROOT,
    process.cwd(),
    app.getAppPath(),
    path.dirname(process.execPath),
    __dirname,
  ].filter(Boolean);

  for (const candidate of candidates) {
    const found = walkUpForRepoRoot(candidate);
    if (found) {
      return found;
    }
  }

  throw new Error(
    "Repository root was not found. Set PAPER_RADAR_ROOT to the project directory.",
  );
}

function walkUpForRepoRoot(startPath) {
  let current = fs.existsSync(startPath) && fs.statSync(startPath).isFile()
    ? path.dirname(startPath)
    : startPath;
  for (let depth = 0; depth < 8; depth += 1) {
    if (
      fs.existsSync(path.join(current, "backend", "app", "main.py")) &&
      fs.existsSync(path.join(current, "frontend", "package.json")) &&
      fs.existsSync(path.join(current, "environment.yml"))
    ) {
      return current;
    }
    const parent = path.dirname(current);
    if (parent === current) {
      break;
    }
    current = parent;
  }
  return null;
}

async function findRuntime() {
  const envDir = await findCondaEnvDir();
  const python = path.join(envDir, executableDirName(), executableName("python"));
  const node = path.join(envDir, executableDirName(), executableName("node"));

  if (!fs.existsSync(python) || !fs.existsSync(node)) {
    throw new Error(
      `Conda environment '${CONDA_ENV_NAME}' is missing python.exe or node.exe at ${envDir}.`,
    );
  }

  return { envDir, python, node };
}

async function findCondaEnvDir() {
  const candidates = runtimeEnvCandidates();
  for (const candidate of candidates) {
    if (isValidCondaEnv(candidate)) {
      return candidate;
    }
  }

  const condaCommand = findCondaCommand();
  if (condaCommand) {
    const envDir = await readEnvDirFromConda(condaCommand);
    if (envDir && isValidCondaEnv(envDir)) {
      return envDir;
    }
  }

  throw new Error(
    `Conda environment '${CONDA_ENV_NAME}' was not found. Create it with: conda env create -f environment.yml`,
  );
}

function runtimeEnvCandidates() {
  const candidates = [];
  const home = os.homedir();
  const condaExe = process.env.CONDA_EXE;

  pushIfPresent(candidates, process.env.PAPER_RADAR_CONDA_ENV_DIR);
  if (path.basename(process.env.CONDA_PREFIX || "") === CONDA_ENV_NAME) {
    pushIfPresent(candidates, process.env.CONDA_PREFIX);
  }
  if (condaExe) {
    const condaRoot = path.dirname(path.dirname(condaExe));
    pushIfPresent(candidates, path.join(condaRoot, "envs", CONDA_ENV_NAME));
  }

  for (const root of condaRootCandidates(home)) {
    pushIfPresent(candidates, path.join(root, "envs", CONDA_ENV_NAME));
  }

  return [...new Set(candidates)];
}

function pushIfPresent(list, value) {
  if (value) {
    list.push(path.resolve(value));
  }
}

function isValidCondaEnv(envDir) {
  return (
    fs.existsSync(path.join(envDir, executableDirName(), executableName("python"))) &&
    fs.existsSync(path.join(envDir, executableDirName(), executableName("node")))
  );
}

function findCondaCommand() {
  const home = os.homedir();
  const candidates = [
    process.env.CONDA_EXE,
    ...condaCommandCandidates(home),
  ].filter(Boolean);

  for (const candidate of candidates) {
    if (candidate === "conda" || fs.existsSync(candidate)) {
      return candidate;
    }
  }

  const locator = process.platform === "win32" ? "where" : "which";
  const whereResult = spawnSync(locator, ["conda"], {
    encoding: "utf8",
    windowsHide: true,
  });
  if (whereResult.status === 0) {
    const first = whereResult.stdout.split(/\r?\n/).find(Boolean);
    if (first) {
      return first.trim();
    }
  }
  return null;
}

function condaRootCandidates(home) {
  if (process.platform === "win32") {
    return [
      "D:\\miniconda",
      "D:\\Miniconda3",
      "D:\\anaconda3",
      "D:\\Anaconda3",
      path.join(home, "miniconda3"),
      path.join(home, "Miniconda3"),
      path.join(home, "anaconda3"),
      path.join(home, "Anaconda3"),
      "C:\\ProgramData\\miniconda3",
      "C:\\ProgramData\\Miniconda3",
      "C:\\ProgramData\\anaconda3",
      "C:\\ProgramData\\Anaconda3",
    ];
  }

  return [
    "/opt/miniconda3",
    "/opt/Miniconda3",
    "/opt/anaconda3",
    "/opt/Anaconda3",
    "/opt/miniforge3",
    "/opt/Miniforge3",
    "/usr/local/miniconda3",
    "/usr/local/anaconda3",
    "/usr/local/miniforge3",
    "/opt/homebrew/Caskroom/miniconda/base",
    "/opt/homebrew/Caskroom/miniforge/base",
    "/opt/homebrew/anaconda3",
    path.join(home, "miniconda3"),
    path.join(home, "Miniconda3"),
    path.join(home, "anaconda3"),
    path.join(home, "Anaconda3"),
    path.join(home, "miniforge3"),
    path.join(home, "Miniforge3"),
  ];
}

function condaCommandCandidates(home) {
  if (process.platform === "win32") {
    return [
      "D:\\miniconda\\Scripts\\conda.exe",
      "D:\\miniconda\\condabin\\conda.bat",
      "D:\\Miniconda3\\Scripts\\conda.exe",
      "D:\\Miniconda3\\condabin\\conda.bat",
    ];
  }

  return [
    "/opt/homebrew/bin/conda",
    "/usr/local/bin/conda",
    "/opt/miniconda3/bin/conda",
    "/opt/anaconda3/bin/conda",
    "/opt/miniforge3/bin/conda",
    path.join(home, "miniconda3", "bin", "conda"),
    path.join(home, "anaconda3", "bin", "conda"),
    path.join(home, "miniforge3", "bin", "conda"),
  ];
}

function readEnvDirFromConda(condaCommand) {
  return new Promise((resolve) => {
    const isBatch = /\.(bat|cmd)$/i.test(condaCommand);
    const command = isBatch ? "cmd.exe" : condaCommand;
    const args = isBatch
      ? ["/d", "/s", "/c", `"${condaCommand}" env list --json`]
      : ["env", "list", "--json"];
    const child = spawn(command, args, {
      windowsHide: true,
      stdio: ["ignore", "pipe", "ignore"],
    });

    let output = "";
    child.stdout.on("data", (chunk) => {
      output += chunk.toString();
    });
    child.on("error", () => resolve(null));
    child.on("close", (code) => {
      if (code !== 0) {
        resolve(null);
        return;
      }
      try {
        const data = JSON.parse(output);
        const envDir = (data.envs || []).find(
          (item) => path.basename(item) === CONDA_ENV_NAME,
        );
        resolve(envDir || null);
      } catch {
        resolve(null);
      }
    });
  });
}

function createServiceEnv(envDir) {
  const entries =
    process.platform === "win32"
      ? [
          envDir,
          path.join(envDir, "Scripts"),
          path.join(envDir, "Library", "bin"),
          process.env.PATH || "",
        ]
      : [path.join(envDir, "bin"), process.env.PATH || ""];
  return {
    ...process.env,
    CONDA_DEFAULT_ENV: CONDA_ENV_NAME,
    CONDA_PREFIX: envDir,
    PATH: entries.join(path.delimiter),
  };
}

async function assertPortFree(port, label) {
  const inUse =
    (await isPortOpen("127.0.0.1", port)) || (await isPortOpen("::1", port));
  if (inUse) {
    throw new Error(
      `${label} port ${port} is already in use. Close the existing service and start Paper Radar again.`,
    );
  }
}

function isPortOpen(host, port) {
  return new Promise((resolve) => {
    const socket = net.createConnection({ host, port });
    socket.setTimeout(500);
    socket.once("connect", () => {
      socket.destroy();
      resolve(true);
    });
    socket.once("timeout", () => {
      socket.destroy();
      resolve(false);
    });
    socket.once("error", () => {
      resolve(false);
    });
  });
}

function startService({ name, command, args, cwd, env, logPath }) {
  const logStream = fs.createWriteStream(logPath, { flags: "a" });
  logStream.write(
    `\n[${new Date().toISOString()}] Starting ${name}: ${command} ${args.join(
      " ",
    )}\n`,
  );

  const child = spawn(command, args, {
    cwd,
    env,
    detached: process.platform !== "win32",
    windowsHide: true,
    stdio: ["ignore", "pipe", "pipe"],
  });

  const service = {
    name,
    child,
    exit: null,
    error: null,
    logPath,
    logStream,
  };
  services.push(service);

  child.stdout.on("data", (chunk) => logStream.write(chunk));
  child.stderr.on("data", (chunk) => logStream.write(chunk));
  child.on("error", (error) => {
    service.error = error;
    logStream.write(`[${new Date().toISOString()}] ${name} error: ${error}\n`);
  });
  child.on("exit", (code, signal) => {
    service.exit = { code, signal };
    logStream.write(
      `[${new Date().toISOString()}] ${name} exited: code=${code} signal=${signal}\n`,
    );
    logStream.end();
  });

  return service;
}

async function waitForHttp(url, label, watchedServices) {
  const deadline = Date.now() + STARTUP_TIMEOUT_MS;
  while (Date.now() < deadline) {
    for (const service of watchedServices) {
      if (service.error) {
        throw new Error(`${service.name} failed to start: ${service.error.message}`);
      }
      if (service.exit) {
        throw new Error(
          `${service.name} exited before startup completed. Check ${service.logPath}.`,
        );
      }
    }
    if (await httpOk(url)) {
      return;
    }
    await delay(500);
  }
  throw new Error(`${label} did not become ready within 60 seconds. Check logs.`);
}

function httpOk(urlString) {
  return new Promise((resolve) => {
    const request = http.get(urlString, { timeout: 2000 }, (response) => {
      response.resume();
      resolve(response.statusCode >= 200 && response.statusCode < 500);
    });
    request.on("timeout", () => {
      request.destroy();
      resolve(false);
    });
    request.on("error", () => resolve(false));
  });
}

function delay(ms) {
  return new Promise((resolve) => {
    setTimeout(resolve, ms);
  });
}

function stopServices() {
  for (const service of services.splice(0).reverse()) {
    if (!service.child || service.child.killed || service.exit) {
      continue;
    }
    if (process.platform === "win32") {
      spawnSync("taskkill", ["/pid", String(service.child.pid), "/t", "/f"], {
        windowsHide: true,
        stdio: "ignore",
      });
    } else {
      try {
        process.kill(-service.child.pid, "SIGTERM");
      } catch {
        service.child.kill("SIGTERM");
      }
    }
  }
}

function executableDirName() {
  return process.platform === "win32" ? "" : "bin";
}

function executableName(baseName) {
  return process.platform === "win32" ? `${baseName}.exe` : baseName;
}

function formatStartupError(error) {
  const lines = [error && error.message ? error.message : String(error)];
  if (repoRoot) {
    lines.push("");
    lines.push(`Logs: ${path.join(repoRoot, ".runtime", "logs")}`);
  }
  return lines.join("\n");
}
