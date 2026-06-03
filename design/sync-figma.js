import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Helper to parse .env file inside design/ directory
function loadEnv() {
  const envPath = path.join(__dirname, '.env');
  if (!fs.existsSync(envPath)) {
    console.error(`[Error] .env file not found at ${envPath}`);
    process.exit(1);
  }

  const content = fs.readFileSync(envPath, 'utf8');
  const env = {};
  content.split('\n').forEach(line => {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#')) return;
    const parts = trimmed.split('=');
    if (parts.length >= 2) {
      const key = parts[0].trim();
      const value = parts.slice(1).join('=').trim();
      env[key] = value;
    }
  });
  return env;
}

const env = loadEnv();
const FIGMA_API_TOKEN = env.FIGMA_API_TOKEN;
const FIGMA_FILE_KEY = env.FIGMA_FILE_KEY;

if (!FIGMA_API_TOKEN || !FIGMA_FILE_KEY) {
  console.error('[Error] FIGMA_API_TOKEN or FIGMA_FILE_KEY is missing in design/.env');
  process.exit(1);
}

const ICONS_DIR = path.join(__dirname, 'assets/figma-icons');
const IMAGES_DIR = path.join(__dirname, 'assets/figma-images');
const TOKENS_DIR = path.join(__dirname, 'tokens');

// Ensure directories exist
[ICONS_DIR, IMAGES_DIR, TOKENS_DIR].forEach(dir => {
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
});

async function figmaApi(endpoint, timeoutMs = 25000) {
  const url = `https://api.figma.com/v1${endpoint}`;
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(url, {
      headers: {
        'X-Figma-Token': FIGMA_API_TOKEN,
      },
      signal: controller.signal
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      throw new Error(`Figma API Request failed: ${response.status} ${response.statusText}\n${await response.text()}`);
    }

    return response.json();
  } catch (err) {
    clearTimeout(timeoutId);
    if (err.name === 'AbortError') {
      throw new Error(`Request timed out after ${timeoutMs / 1000}s`);
    }
    throw err;
  }
}

// Helper to call Figma API in batches of node IDs to avoid render timeouts
async function fetchImagesInBatches(fileKey, nodeIds, format, scale) {
  const batchSize = 1; // Single-node requests are safest and skip failures cleanly
  const results = { images: {} };
  const total = nodeIds.length;
  
  for (let i = 0; i < total; i += batchSize) {
    if (i > 0) {
      // Add a 500ms delay between requests to avoid Figma API rate limiting (429)
      await new Promise(resolve => setTimeout(resolve, 500));
    }
    const batch = nodeIds.slice(i, i + batchSize);
    const nodeIdsString = batch.join(',');
    const scaleParam = scale ? `&scale=${scale}` : '';
    console.log(`  [Batch ${i + 1}/${total}] Requesting ${format.toUpperCase()} for Node ID: ${nodeIdsString} ...`);
    try {
      // Set a 25 second timeout for rendering
      const res = await figmaApi(`/images/${fileKey}?ids=${nodeIdsString}&format=${format}${scaleParam}`, 25000);
      if (res.images) {
        Object.assign(results.images, res.images);
      }
    } catch (e) {
      console.warn(`  [Warning] Failed to fetch images for node ${nodeIdsString}: ${e.message}`);
    }
  }
  return results;
}

// Mapping of Korean labels in NavBar to English asset suffixes
const NAV_MAPPING = {
  "홈": "home",
  "음성 입력": "voice_input",
  "스토리 입력": "story_input",
  "씬 확인": "scene_check",
  "캐릭터": "character",
  "보이스": "voice",
  "배경": "background",
  "씬 편집": "scene_editor",
  "타임라인": "timeline",
  "렌더": "render",
  "출력": "export"
};

// Convert Figma color component (0-1) to Hex
const to255 = (c) => Math.round(c * 255);
function figmaColorToHex(color) {
  const r = to255(color.r).toString(16).padStart(2, '0');
  const g = to255(color.g).toString(16).padStart(2, '0');
  const b = to255(color.b).toString(16).padStart(2, '0');
  return `#${r}${g}${b}`;
}

async function run() {
  console.log('Fetching Figma File structure...');
  const fileData = await figmaApi(`/files/${FIGMA_FILE_KEY}`);
  console.log(`Successfully fetched file: "${fileData.name}"`);

  const stylesMeta = fileData.styles || {};
  const components = [];
  const nodesMap = {};
  const navIconsToDownload = []; // { id, name }

  // Traverse the tree
  function traverse(node) {
    nodesMap[node.id] = node;

    if (node.type === 'COMPONENT') {
      components.push({
        id: node.id,
        name: node.name,
      });
    }

    if (node.children) {
      node.children.forEach(traverse);
    }
  }

  traverse(fileData.document);
  console.log(`Found ${components.length} components in the document.`);

  // 1. Traverse Specifically the Nav component (ID: 5:32 or dynamically found) to extract individual inner icon vectors
  let navComponent = Object.values(nodesMap).find(node => node.name === 'Nav');
  if (!navComponent) {
    navComponent = nodesMap['5:55'] || nodesMap['5:32'];
  }
  if (navComponent) {
    console.log('Nav component found. Extracting individual icons...');
    
    // Find all INSTANCE nodes representing menu items inside the Nav bar
    const instances = [];
    function findInstances(node) {
      if (node.type === 'INSTANCE') {
        instances.push(node);
      }
      if (node.children) {
        node.children.forEach(findInstances);
      }
    }
    findInstances(navComponent);

    for (const inst of instances) {
      // Find the TEXT child and the VECTOR child in this instance
      let textVal = '';
      let vectorId = '';
      
      function searchChildren(child) {
        if (child.type === 'TEXT') {
          textVal = child.characters ? child.characters.trim() : '';
        } else if (child.type === 'VECTOR') {
          vectorId = child.id;
        }
        if (child.children) {
          child.children.forEach(searchChildren);
        }
      }
      searchChildren(inst);

      if (textVal && vectorId) {
        const engName = NAV_MAPPING[textVal] || textVal.replace(/[^a-zA-Z0-9_\-]/g, '_');
        navIconsToDownload.push({
          id: vectorId,
          filename: `nav_${engName}.svg`
        });
      }
    }
    console.log(`Identified ${navIconsToDownload.length} inner navigation icons to export.`);
  } else {
    console.warn('Nav component (ID 5:32) not found in figma file.');
  }

  const FORCE_OVERWRITE = process.argv.includes('--force') || process.argv.includes('-f');
  if (FORCE_OVERWRITE) {
    console.log('Force overwrite enabled. Will re-download all assets.');
  }

  // 2. Download Component Images to design/assets/images
  const componentsToDownload = [];
  for (const comp of components) {
    const safeName = comp.name.replace(/[\/\\:\*\?"<>\|]/g, '_');
    const pngPath = path.join(IMAGES_DIR, `${safeName}.png`);
    const svgPath = path.join(IMAGES_DIR, `${safeName}.svg`);

    const pngExists = fs.existsSync(pngPath);
    const svgExists = fs.existsSync(svgPath);

    if (FORCE_OVERWRITE || !pngExists || !svgExists) {
      componentsToDownload.push(comp);
    } else {
      console.log(`[Skip] Component "${comp.name}" already exists locally (PNG & SVG).`);
    }
  }

  if (componentsToDownload.length > 0) {
    const idsArray = componentsToDownload.map(c => c.id);
    
    console.log(`Fetching export URLs for ${componentsToDownload.length} components in batches...`);
    const pngRes = await fetchImagesInBatches(FIGMA_FILE_KEY, idsArray, 'png', 2);
    const svgRes = await fetchImagesInBatches(FIGMA_FILE_KEY, idsArray, 'svg');

    for (const comp of componentsToDownload) {
      const safeName = comp.name.replace(/[\/\\:\*\?"<>\|]/g, '_');
      
      // Download PNG if missing or force
      const pngPath = path.join(IMAGES_DIR, `${safeName}.png`);
      const pngUrl = pngRes.images[comp.id];
      if (pngUrl && (FORCE_OVERWRITE || !fs.existsSync(pngPath))) {
        console.log(`Downloading component image: ${safeName}.png ...`);
        try {
          const res = await fetch(pngUrl);
          if (!res.ok) throw new Error(`HTTP ${res.status}`);
          const buffer = Buffer.from(await res.arrayBuffer());
          fs.writeFileSync(pngPath, buffer);
        } catch (e) {
          console.error(`  [Error] Failed to download PNG for "${comp.name}": ${e.message}`);
        }
      }

      // Download SVG if missing or force
      const svgPath = path.join(IMAGES_DIR, `${safeName}.svg`);
      const svgUrl = svgRes.images[comp.id];
      if (svgUrl && (FORCE_OVERWRITE || !fs.existsSync(svgPath))) {
        console.log(`Downloading component image: ${safeName}.svg ...`);
        try {
          const res = await fetch(svgUrl);
          if (!res.ok) throw new Error(`HTTP ${res.status}`);
          const buffer = Buffer.from(await res.arrayBuffer());
          fs.writeFileSync(svgPath, buffer);
        } catch (e) {
          console.error(`  [Error] Failed to download SVG for "${comp.name}": ${e.message}`);
        }
      }
    }
  } else {
    console.log('All components are already downloaded locally. Skipping download.');
  }

  // 3. Download Nav Inner Icons (SVGs) to design/assets/icons
  const iconsToDownload = [];
  for (const item of navIconsToDownload) {
    const iconPath = path.join(ICONS_DIR, item.filename);
    if (FORCE_OVERWRITE || !fs.existsSync(iconPath)) {
      iconsToDownload.push(item);
    } else {
      console.log(`[Skip] Inner icon "${item.filename}" already exists locally.`);
    }
  }

  if (iconsToDownload.length > 0) {
    const iconNodeIds = iconsToDownload.map(item => item.id);
    console.log(`Fetching export URLs for ${iconsToDownload.length} inner icons (SVG) in batches...`);
    const iconSvgRes = await fetchImagesInBatches(FIGMA_FILE_KEY, iconNodeIds, 'svg');

    for (const item of iconsToDownload) {
      const svgUrl = iconSvgRes.images[item.id];
      if (svgUrl) {
        console.log(`Downloading inner icon SVG: ${item.filename} ...`);
        try {
          const res = await fetch(svgUrl);
          if (!res.ok) throw new Error(`HTTP ${res.status}`);
          const buffer = Buffer.from(await res.arrayBuffer());
          fs.writeFileSync(path.join(ICONS_DIR, item.filename), buffer);
        } catch (e) {
          console.error(`  [Error] Failed to download SVG for icon "${item.filename}": ${e.message}`);
        }
      }
    }
  } else {
    console.log('All inner navigation icons are already downloaded locally. Skipping download.');
  }

  // 4. Update Design Tokens (Colors / Text Styles)
  console.log('Processing Figma styles for design tokens...');
  const figmaColors = {};
  const figmaTypography = {};

  for (const [styleId, styleInfo] of Object.entries(stylesMeta)) {
    const name = styleInfo.name;
    const type = styleInfo.styleType;

    // Search document for node referencing style
    for (const node of Object.values(nodesMap)) {
      if (node.styles && node.styles[type.toLowerCase()] === styleId) {
        if (type === 'FILL' && node.fills && node.fills.length > 0) {
          const fill = node.fills[0];
          if (fill.type === 'SOLID') {
            figmaColors[name] = figmaColorToHex(fill.color);
            break;
          }
        } else if (type === 'TEXT' && node.style) {
          const s = node.style;
          figmaTypography[name] = {
            fontFamily: s.fontFamily,
            fontSize: s.fontSize,
            fontWeight: s.fontWeight,
            lineHeight: s.lineHeightPercentByRowOrColumn ? s.lineHeightPercentByRowOrColumn.toFixed(1) + '%' : 'normal'
          };
          break;
        }
      }
    }
  }

  // Write figma-specific tokens safely to figma_tokens.json so as not to overwrite main configurations
  if (Object.keys(figmaColors).length > 0 || Object.keys(figmaTypography).length > 0) {
    const figmaTokens = {
      colors: figmaColors,
      typography: figmaTypography
    };
    fs.writeFileSync(
      path.join(TOKENS_DIR, 'figma_tokens.json'),
      JSON.stringify(figmaTokens, null, 2)
    );
    console.log(`Generated figma_tokens.json under ${TOKENS_DIR}`);
  } else {
    console.log('No solid fill or text styles detected to write to JSON tokens.');
  }

  console.log('\n--- Sync Completed Successfully ---');
}

run().catch(err => {
  console.error('[Error] Sync failed:', err);
  process.exit(1);
});
