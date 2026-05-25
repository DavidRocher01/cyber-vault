const { chromium } = require('playwright');
const path = require('path');

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  const htmlFile = path.resolve(__dirname, '..', 'backend', 'phishing_templates_preview.html');
  const pdfFile = path.resolve(__dirname, '..', 'backend', 'phishing_templates_preview.pdf');
  const fileUrl = 'file:///' + htmlFile.replace(/\\/g, '/');
  await page.goto(fileUrl, { waitUntil: 'networkidle' });
  await page.pdf({
    path: pdfFile,
    format: 'A4',
    margin: { top: '12mm', bottom: '12mm', left: '12mm', right: '12mm' },
    printBackground: true,
  });
  await browser.close();
  console.log('PDF généré : ' + pdfFile);
})();
