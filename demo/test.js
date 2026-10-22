const puppeteer = require('puppeteer');
const path = require('path');
const FILE = 'file://' + encodeURI(path.join(__dirname, 'index.html'));
const OUT = path.join(__dirname, '..', 'screenshots', 'demo');
require('fs').mkdirSync(OUT, { recursive: true });

const sleep = ms => new Promise(r => setTimeout(r, ms));

(async () => {
  const browser = await puppeteer.launch({
    executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    headless: 'new',
    args: ['--no-sandbox', '--font-render-hinting=none'],
  });
  const page = await browser.newPage();
  await page.setViewport({ width: 430, height: 932, deviceScaleFactor: 2, isMobile: true, hasTouch: true });

  const errs = [];
  page.on('pageerror', e => errs.push('PAGEERROR: ' + e.message));
  page.on('console', m => { if (m.type() === 'error') errs.push('CONSOLE: ' + m.text()); });

  await page.goto(FILE, { waitUntil: 'networkidle2', timeout: 30000 });
  await sleep(900);

  await page.screenshot({ path: path.join(OUT, '01-hero.png') });

  // 搜索
  await page.evaluate(() => { document.getElementById('q').value = '板烧'; document.getElementById('q').dispatchEvent(new Event('input')); });
  await sleep(400);
  const cnt1 = await page.$$eval('#grid .item', n => n.length);
  await page.screenshot({ path: path.join(OUT, '02-search.png') });

  // 价格区间 ¥10-15
  await page.evaluate(() => document.querySelectorAll('#prChips button')[1].click());
  await sleep(350);
  const cnt2 = await page.$$eval('#grid .item', n => n.length);
  await page.screenshot({ path: path.join(OUT, '03-price.png') });

  // 清空并选第 3 个
  await page.evaluate(() => { const q = document.getElementById('q'); q.value = ''; q.dispatchEvent(new Event('input')); });
  await sleep(300);
  await page.evaluate(() => document.querySelectorAll('#grid .item')[2].click());
  await sleep(300);
  const picked = await page.$eval('#picked .nm', n => n.textContent);

  // 数量 +1
  await page.evaluate(() => document.querySelectorAll('#picked .qty button')[1].click());
  await sleep(250);
  await page.evaluate(() => document.getElementById('s1').scrollIntoView({ block: 'end' }));
  await sleep(400);
  await page.screenshot({ path: path.join(OUT, '04-picked.png') });

  // 保存设定
  await page.evaluate(() => document.getElementById('saveBtn').click());
  await sleep(1100);
  await page.evaluate(() => document.getElementById('s2').scrollIntoView({ block: 'center' }));
  await sleep(500);
  await page.screenshot({ path: path.join(OUT, '05-setup-done.png') });

  // ③ 照旧
  await page.evaluate(() => document.getElementById('b3ok').click());
  await sleep(600);
  await page.evaluate(() => document.getElementById('s3').scrollIntoView({ block: 'center' }));
  await sleep(500);
  await page.screenshot({ path: path.join(OUT, '06-evening.png') });

  // ④ 建单
  await page.evaluate(() => document.getElementById('b4fire').click());
  await sleep(1200);
  await page.evaluate(() => document.getElementById('p4').scrollIntoView({ block: 'center' }));
  await sleep(500);
  const cd = await page.$eval('#cdv', n => n.textContent).catch(() => 'NO-CD');
  const amt = await page.$eval('.ord-h .amt', n => n.textContent).catch(() => 'NO-AMT');
  const bls = await page.$eval('.bls .q', n => n.textContent).catch(() => 'NO-BLS');
  await page.screenshot({ path: path.join(OUT, '07-order.png') });

  // 付款（第二个按钮）
  await page.evaluate(() => {
    const bs = document.querySelectorAll('#c4body .btn2 .btn');
    bs[bs.length - 1].click();
  });
  await sleep(800);
  await page.evaluate(() => document.getElementById('p4').scrollIntoView({ block: 'center' }));
  await sleep(400);
  await page.screenshot({ path: path.join(OUT, '08-paid.png') });

  // 日历
  await page.evaluate(() => document.getElementById('s5').scrollIntoView({ block: 'center' }));
  await sleep(450);
  const stats = await page.evaluate(() => ['st1', 'st2', 'st3'].map(i => document.getElementById(i).textContent));
  await page.screenshot({ path: path.join(OUT, '09-calendar.png') });

  await page.evaluate(() => document.getElementById('s6').scrollIntoView({ block: 'start' }));
  await sleep(450);
  await page.screenshot({ path: path.join(OUT, '10-how.png') });

  // 桌面
  const p2 = await browser.newPage();
  await p2.setViewport({ width: 1280, height: 900, deviceScaleFactor: 1 });
  await p2.goto(FILE, { waitUntil: 'networkidle2' });
  await sleep(800);
  await p2.screenshot({ path: path.join(OUT, '11-desktop.png') });

  // 整页长图
  await page.evaluate(() => { window.scrollTo(0, 0); });
  await sleep(300);
  await page.screenshot({ path: path.join(OUT, '12-full.png'), fullPage: true });

  const imgs = await page.evaluate(() => {
    const a = [...document.images];
    return { total: a.length, ok: a.filter(i => i.naturalWidth > 0).length };
  });

  console.log(JSON.stringify({ searchItems: cnt1, priceItems: cnt2, picked, cd, amt, bls, stats, imgs, errors: errs }, null, 2));
  await browser.close();
})();
