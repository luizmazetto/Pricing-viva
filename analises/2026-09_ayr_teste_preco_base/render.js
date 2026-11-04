// Renderiza slide_ayr_teste_preco_base.html em PNG (2x) e PDF 16:9. Uso: node render.js
const { chromium } = require('playwright');
const path = require('path');
(async () => {
  const src = 'file://' + path.join(__dirname, 'slide_ayr_teste_preco_base.html');
  const b = await chromium.launch();
  const pg = await b.newPage({ viewport: { width: 1600, height: 900 }, deviceScaleFactor: 2 });
  await pg.goto(src, { waitUntil: 'networkidle' });
  await pg.waitForTimeout(500);
  await pg.screenshot({ path: path.join(__dirname, 'slide_ayr_teste_preco_base.png') });
  await pg.emulateMedia({ media: 'print' });
  await pg.pdf({ path: path.join(__dirname, 'slide_ayr_teste_preco_base.pdf'), width: '1600px', height: '900px', printBackground: true });
  await b.close();
  console.log('ok');
})();
