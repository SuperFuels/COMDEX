const fs = require("fs");
const path = require("path");
const { app, BrowserWindow, nativeImage } = require("electron");

const projectRoot = path.resolve(__dirname, "..");
const sourcePath = process.env.TESSARIS_LOGO_SOURCE;

if (!sourcePath) {
  throw new Error("Set TESSARIS_LOGO_SOURCE to the transparent Tessaris wordmark PNG.");
}

const iconsetPath = path.join(projectRoot, "assets", "icon.iconset");
const masterPath = path.join(projectRoot, "assets", "icon.png");

const iconSizes = [
  [16, "icon_16x16.png"],
  [32, "icon_16x16@2x.png"],
  [32, "icon_32x32.png"],
  [64, "icon_32x32@2x.png"],
  [128, "icon_128x128.png"],
  [256, "icon_128x128@2x.png"],
  [256, "icon_256x256.png"],
  [512, "icon_256x256@2x.png"],
  [512, "icon_512x512.png"],
  [1024, "icon_512x512@2x.png"],
];

app.whenReady().then(async () => {
  const source = nativeImage.createFromPath(sourcePath);
  if (source.isEmpty()) {
    throw new Error(`Could not read logo source: ${sourcePath}`);
  }

  // The source is a transparent horizontal wordmark. This crop isolates the
  // blue tesseract and keeps enough clear space for a balanced macOS Dock icon.
  const iconOnly = source.crop({ x: 125, y: 125, width: 445, height: 445 });
  const mark = iconOnly.resize({ width: 800, height: 800, quality: "best" });
  const markDataUrl = mark.toDataURL();

  // Render through Chromium's canvas so the rounded tile, transparent corners
  // and raster mark composite identically at every icon size.
  const renderer = new BrowserWindow({ show: false, webPreferences: { offscreen: true } });
  await renderer.loadURL("data:text/html,<canvas id='icon' width='1024' height='1024'></canvas>");
  const masterDataUrl = await renderer.webContents.executeJavaScript(`
    new Promise((resolve, reject) => {
      const canvas = document.getElementById("icon");
      const context = canvas.getContext("2d");
      const image = new Image();
      image.onload = () => {
        context.clearRect(0, 0, 1024, 1024);
        context.beginPath();
        context.roundRect(34, 34, 956, 956, 220);
        context.fillStyle = "#FFFFFF";
        context.fill();
        context.lineWidth = 12;
        context.strokeStyle = "#BFD1FF";
        context.stroke();
        // The mark carries more visual weight at its lower-right, so place it
        // slightly up and left for optical (rather than purely geometric) centring.
        context.drawImage(image, 94, 94, 800, 800);
        resolve(canvas.toDataURL("image/png"));
      };
      image.onerror = reject;
      image.src = ${JSON.stringify(markDataUrl)};
    })
  `);
  renderer.destroy();
  const master = nativeImage.createFromDataURL(masterDataUrl);

  if (master.isEmpty()) {
    throw new Error("Could not render the macOS icon background.");
  }

  fs.mkdirSync(iconsetPath, { recursive: true });
  fs.writeFileSync(masterPath, master.toPNG());

  for (const [size, filename] of iconSizes) {
    const resized = master.resize({ width: size, height: size, quality: "best" });
    fs.writeFileSync(path.join(iconsetPath, filename), resized.toPNG());
  }

  app.quit();
});
