const fs = require("fs");
const path = require("path");
const { app, nativeImage } = require("electron");

const projectRoot = path.resolve(__dirname, "..");
const sourcePath = process.env.TESSARIS_LOGO_SOURCE;

if (!sourcePath) {
  throw new Error("Set TESSARIS_LOGO_SOURCE to the square Tessaris Si icon PNG.");
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

  // Keep the official Si artwork intact. The source already includes its
  // transparent safe area, so resizing it directly produces consistent Dock,
  // Finder and installer artwork without re-cropping or adding another tile.
  const master = source.resize({ width: 1024, height: 1024, quality: "best" });

  if (master.isEmpty()) {
    throw new Error("Could not resize the Tessaris Si icon.");
  }

  fs.mkdirSync(iconsetPath, { recursive: true });
  fs.writeFileSync(masterPath, master.toPNG());

  for (const [size, filename] of iconSizes) {
    const resized = master.resize({ width: size, height: size, quality: "best" });
    fs.writeFileSync(path.join(iconsetPath, filename), resized.toPNG());
  }

  app.quit();
});
