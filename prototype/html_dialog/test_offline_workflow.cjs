// Optional browser checks: node --test prototype/html_dialog/test_offline_workflow.cjs
// Uses Playwright only for development; no runtime dependency in the HTML files.
const { test, before, after } = require('node:test');
const assert = require('node:assert/strict');
const { chromium } = require('playwright');
const fs = require('node:fs/promises');
const os = require('node:os');
const path = require('node:path');
const { pathToFileURL } = require('node:url');
let browser, dir, fixture, base;
const errors = [];
const json = data => JSON.stringify(data).replaceAll('<','\\u003c').replaceAll('>','\\u003e').replaceAll('&','\\u0026');
const replaceData = (html,id,data) => html.replace(new RegExp(`(<script id="${id}"[^>]*>)[\\s\\S]*?(</script>)`), (_,open,close) => open + json(data) + close);
const dataOf = (html,id) => JSON.parse(html.match(new RegExp(`<script id="${id}"[^>]*>([\\s\\S]*?)</script>`))[1]);
async function pageAt(file) {
  const page = await browser.newPage({viewport:{width:1440,height:1100},acceptDownloads:true});
  page.on('pageerror', error => errors.push(error.message));
  page.on('dialog',dialog => dialog.dismiss());
  // Exercise download fallback without opening the native picker in headless runs.
  await page.addInitScript(() => { window.showSaveFilePicker = undefined; });
  await page.goto(pathToFileURL(file).href);
  return page;
}
async function download(page, selector, name) {
  const pending = page.waitForEvent('download');
  await page.locator(selector).click();
  const event = await pending;
  const dest = path.join(dir,name || event.suggestedFilename());
  await event.saveAs(dest); return dest;
}
async function preparedFixture(scope='full',selection={reflection:true,review:true,outlook:true},name='prep.html',type='annual') {
  const employee = base.employees[0];
  const payload = {version:2,preparation_id:`PREP-${employee.case_id}`,package_id:base.package.package_id,case_id:employee.case_id,scope,dialog_type:type,selection,review_year:base.package.rb_year,outlook_year:base.package.ab_year,period_start:employee.period_start,period_end:employee.period_end,employee:employee.employee,manager:{pn:base.package.manager_pn,name:base.package.manager_name},competency_model:base.configuration.competency_model,previous_goals:employee.previous_goals.map(({id,title,criteria,steps,target_date})=>({id,title,criteria,steps,target_date})),previous_development_goals:[],fields:{}};
  const file = path.join(dir,name);
  await fs.writeFile(file,base.configuration.preparation_template.replace('__MD_PREPARATION_JSON__',json(payload)));
  return file;
}
before(async () => {
  dir = await fs.mkdtemp(path.join(os.tmpdir(),'md-offline-'));
  const options = {headless:true,args:['--no-sandbox']};
  if (process.env.MD_TEST_CHROMIUM) options.executablePath = process.env.MD_TEST_CHROMIUM;
  browser = await chromium.launch(options);
  const demo = await fs.readFile(path.join(__dirname,'../../demo/MD_Arbeitsmappe_Demo.html'),'utf8');
  base = dataOf(demo,'md-data');
  base.package.guidance_auto_open_disabled = true;
  base.employees = [base.employees[0]];
  base.employees[0].scope = 'full';
  base.employees[0].previous_goals.forEach(goal => { goal.achievement = ''; goal.review = ''; });
  base.employees[0].review.performance = 'MANAGER_PRIVATE_NOTES';
  base.employees[0].review.manager_comment = 'MANAGER_PRIVATE_COMMENT';
  fixture = path.join(dir,'workbook.html');
  await fs.writeFile(fixture,replaceData(demo,'md-data',base));
});
after(async () => { await browser?.close(); assert.deepEqual(errors,[],'No uncaught browser errors'); await fs.rm(dir,{recursive:true,force:true}); });

test('workbook selects parts, retains mandatory feedback and excludes manager entries',async () => {
  const page = await pageAt(fixture);
  await page.locator('[data-step="preparation"]').click();
  assert.equal(await page.locator('[data-preparation-part="reflection"]').isChecked(),true);
  assert.equal(await page.locator('[data-preparation-part="review"]').isChecked(),false);
  await page.locator('[data-action="preparation-all"]').click();
  assert.equal(await page.locator('[data-preparation-part="outlook"]').isChecked(),true);
  const file = await download(page,'[data-action="download-preparation"]','generated.html');
  const html = await fs.readFile(file,'utf8');
  assert.ok(!html.includes('MANAGER_PRIVATE_NOTES') && !html.includes('MANAGER_PRIVATE_COMMENT'));
  const payload = dataOf(html,'prep-data');
  assert.equal(payload.employee.employment_assignment,'1');
  assert.equal(payload.previous_goals[0].title,base.employees[0].previous_goals[0].title);
  const generated = await pageAt(file);
  assert.deepEqual(await generated.locator('[role="tab"]').allTextContents(),['Reflexion','Rückblick','Ausblick','Feedback']);
  if (process.env.MD_TEST_SCREENSHOTS) { await generated.screenshot({path:path.join(process.env.MD_TEST_SCREENSHOTS,'preparation-reflection.png'),fullPage:true}); await generated.locator('[data-tab="review-section"]').click(); await generated.screenshot({path:path.join(process.env.MD_TEST_SCREENSHOTS,'preparation-review.png'),fullPage:true}); }
  await generated.close();
  await page.locator('[data-action="preparation-none"]').click();
  const minimal = await download(page,'[data-action="download-preparation"]','minimal.html');
  const feedbackOnly = await pageAt(minimal);
  assert.deepEqual(await feedbackOnly.locator('[role="tab"]').allTextContents(),['Feedback']);
  await feedbackOnly.close(); await page.close();
});

test('return file removes reflection from JSON, rendered DOM and private print content',async () => {
  const page = await pageAt(await preparedFixture());
  await page.locator('[data-field="review_performance"]').fill('REFLECTION_SECRET_829');
  await page.locator('[data-field="outlook_goals"]').fill('PRIVATE_FUTURE_721');
  // Test privacy even when private notes were rendered into a previous PDF preview.
  await page.evaluate(() => { document.getElementById('print-root').textContent = 'REFLECTION_SECRET_829'; });
  await page.locator('[data-tab="review-section"]').click();
  await page.locator('[data-prepared="review.performance"]').fill('Meine Leistung');
  await page.locator('[data-prepared="review.previous_goals.0.achievement"]').selectOption('Erreicht');
  await page.locator('[data-tab="outlook-section"]').click();
  await page.locator('[data-add="outlook.performance_goals"]').click();
  await page.locator('[data-prepared="outlook.performance_goals.0.title"]').fill('Neues Ziel');
  await page.locator('[data-prepared="outlook.performance_goals.0.criteria"]').fill('Messbar');
  await page.locator('[data-prepared="outlook.performance_goals.0.target_date"]').fill('2026-12-31');
  await page.locator('[data-add="outlook.development_goals"]').click();
  await page.locator('[data-prepared="outlook.development_goals.0.competency"]').selectOption({index:1});
  await page.locator('[data-prepared="outlook.development_goals.0.title"]').fill('Lernen');
  await page.locator('[data-tab="feedback-section"]').click();
  await page.locator('[data-field="feedback_keep"]').fill('Vielen Dank');
  await page.locator('#return-file').click();
  const returned = await download(page,'#return-confirm','returned.html');
  const html = await fs.readFile(returned,'utf8');
  assert.ok(!html.includes('REFLECTION_SECRET_829') && !html.includes('PRIVATE_FUTURE_721'));
  const data = dataOf(html,'prep-data');
  assert.deepEqual(data.fields,{feedback_keep:'Vielen Dank'});
  assert.equal(data.prepared.review.performance,'Meine Leistung');
  assert.equal(data.prepared.outlook.performance_goals[0].title,'Neues Ziel');
  assert.equal(data.selection.reflection,false);
  assert.equal(await page.locator('#save-html').isEnabled(),true,'Return export does not falsely save own notes');
  const own = await download(page,'#save-html','own.html');
  assert.ok((await fs.readFile(own,'utf8')).includes('REFLECTION_SECRET_829'));
  const reopened = await pageAt(own);
  assert.equal(await reopened.locator('[data-field="review_performance"]').inputValue(),'REFLECTION_SECRET_829');
  await reopened.close();
  const returnPage = await pageAt(returned);
  assert.deepEqual(await returnPage.locator('[role="tab"]').allTextContents(),['Rückblick','Ausblick','Feedback']);
  await returnPage.close(); await page.close();
});

test('import preview preserves existing text, selects empty fields and retains original contributions',async () => {
  const page = await pageAt(fixture);
  await page.locator('[data-step="preparation"]').click();
  await page.locator('#preparation-import-file').setInputFiles(path.join(dir,'returned.html'));
  await page.locator('#preparation-import-dialog[open]').waitFor();
  if (process.env.MD_TEST_SCREENSHOTS) await page.screenshot({path:path.join(process.env.MD_TEST_SCREENSHOTS,'import-preview.png'),fullPage:true});
  const review = page.locator('.subsection').filter({hasText:'Rückblick · Leistung und Aufgabenerfüllung'}).locator('input[type="checkbox"]');
  assert.equal(await review.isChecked(),false);
  await page.locator('#preparation-import-confirm').click();
  const saved = await download(page,'#save-button','imported.html');
  const data = dataOf(await fs.readFile(saved,'utf8'),'md-data');
  assert.equal(data.employees[0].review.performance,'MANAGER_PRIVATE_NOTES');
  assert.equal(data.employees[0].outlook.performance_goals[0].title,'Neues Ziel');
  assert.equal(data.employees[0].previous_goals[0].achievement,'Erreicht');
  assert.equal(data.employees[0].ma_preparation.feedback.feedback_keep,'Vielen Dank');
  assert.ok(data.employees[0].ma_preparation.entries.some(item=>item.value==='Meine Leistung'));
  await page.locator('#preparation-import-file').setInputFiles(path.join(dir,'returned.html'));
  await page.locator('#preparation-import-dialog[open]').waitFor();
  await review.check(); await page.locator('#preparation-import-confirm').click();
  const replaced = dataOf(await fs.readFile(await download(page,'#save-button','replaced.html'),'utf8'),'md-data');
  assert.equal(replaced.employees[0].review.performance,'Meine Leistung');
  assert.equal(replaced.employees[0].outlook.performance_goals.length,1,'No duplicate goals on reimport');
  await page.close();
});

test('personal files and mismatched employment, round, manager, scope and period are rejected',async () => {
  const page = await pageAt(fixture);
  await page.locator('[data-step="preparation"]').click();
  await page.locator('#preparation-import-file').setInputFiles(path.join(dir,'own.html'));
  await page.waitForFunction(()=>document.querySelector('#toast').textContent.includes('separate'));
  assert.equal(await page.locator('#preparation-import-dialog').evaluate(el=>el.open),false);
  const html = await fs.readFile(path.join(dir,'returned.html'),'utf8');
  for(const mutate of [data=>data.employee.employment_assignment='2',data=>data.package_id='other',data=>data.manager.pn='123',data=>data.scope='review_only',data=>data.period_end='2024-12-31',data=>data.review_year='2027']) {
    const data = dataOf(html,'prep-data'); mutate(data);
    const wrong = path.join(dir,'wrong.html'); await fs.writeFile(wrong,replaceData(html,'prep-data',data));
    await page.locator('#preparation-import-file').setInputFiles(wrong);
    await page.waitForFunction(()=>document.querySelector('#toast').textContent.includes('passt nicht'));
    assert.equal(await page.locator('#preparation-import-dialog').evaluate(el=>el.open),false);
  }
  assert.equal(await page.locator('#save-button').isDisabled(),true);
  await page.close();
});

test('scope and probation control tabs and keep feedback restricted to reviews',async () => {
  for(const [scope,selection,expected,type] of [
    ['outlook_only',{reflection:true,review:true,outlook:true},['Reflexion','Ausblick'],'annual'],
    ['review_only',{reflection:false,review:true,outlook:true},['Rückblick','Feedback'],'probation'],
    ['outlook_only',{reflection:false,review:false,outlook:false},[],'annual']
  ]) {
    const page = await pageAt(await preparedFixture(scope,selection,`scope-${scope}-${type}.html`,type));
    assert.deepEqual(await page.locator('[role="tab"]').allTextContents(),expected);
    if (type==='probation') { await page.locator('[data-tab="review-section"]').click(); assert.ok((await page.locator('#review-section').textContent()).includes('Probezeit')); assert.equal(await page.locator('[data-prepared="review.previous_goals.0.achievement"]').count(),0); }
    await page.close();
  }
});

test('direct saving reuses chosen handle, copy prompts again and cancellation does not download',async () => {
  const page = await pageAt(await preparedFixture('full',undefined,'native.html'));
  await page.evaluate(() => {
    window.savedHtml=[]; window.pickerCalls=0;
    window.showSaveFilePicker=async ()=>{window.pickerCalls++;return {createWritable:async()=>({write:async html=>window.savedHtml.push(html),close:async()=>{}})}};
  });
  await page.locator('[data-field="review_performance"]').fill('Erster Stand');
  await page.locator('#save-html').click();
  await page.waitForFunction(()=>window.savedHtml.length===1);
  await page.locator('[data-field="review_performance"]').fill('Zweiter Stand');
  await page.locator('#save-html').click();
  await page.waitForFunction(()=>window.savedHtml.length===2);
  assert.equal(await page.evaluate(()=>window.pickerCalls),1);
  assert.ok((await page.evaluate(()=>window.savedHtml[1])).includes('Zweiter Stand'));
  await page.locator('#save-copy').click();
  await page.waitForFunction(()=>window.pickerCalls===2);
  let downloads=0; page.on('download',()=>downloads++);
  await page.evaluate(()=>window.showSaveFilePicker=async()=>{throw new DOMException('Abgebrochen','AbortError')});
  await page.locator('[data-field="review_performance"]').fill('Noch nicht gespeichert');
  await page.locator('#save-copy').click();
  assert.equal(await page.locator('#save-html').isEnabled(),true);
  assert.equal(downloads,0);
  await page.close();
});

test('picker or write failures download a copy and do not claim direct save',async () => {
  for(const fail of ['picker','write']) {
    const page = await pageAt(await preparedFixture('full',undefined,`failure-${fail}.html`));
    await page.evaluate(fail=>{window.showSaveFilePicker=async()=>{if(fail==='picker')throw new DOMException('Blocked','SecurityError');return {createWritable:async()=>{throw new Error('Write failed')}}};},fail);
    await page.locator('[data-field="review_performance"]').fill('Nicht verlieren');
    const result = await download(page,'#save-html',`fallback-${fail}.html`);
    assert.ok((await fs.readFile(result,'utf8')).includes('Nicht verlieren'));
    assert.ok((await page.locator('#toast').textContent()).includes('Neue Kopie'));
    await page.close();
  }
});

test('workbook supports direct save and reopen, preserving revision and import data',async () => {
  const page = await pageAt(fixture);
  await page.evaluate(()=>{window.output=[];window.calls=0;window.showSaveFilePicker=async()=>{window.calls++;return {createWritable:async()=>({write:async html=>window.output.push(html),close:async()=>{}})}};});
  await page.locator('[data-step="preparation"]').click();
  await page.locator('[data-action="preparation-all"]').click();
  await page.locator('#save-button').click();
  await page.waitForFunction(()=>window.output.length===1);
  const first = dataOf(await page.evaluate(()=>window.output[0]),'md-data');
  assert.equal(first.package.revision,base.package.revision+1);
  await page.locator('[data-action="preparation-none"]').click();
  await page.locator('#save-button').click();
  await page.waitForFunction(()=>window.output.length===2);
  assert.equal(await page.evaluate(()=>window.calls),1);
  const file = path.join(dir,'native-workbook.html'); await fs.writeFile(file,await page.evaluate(()=>window.output[1]));
  const reopened = await pageAt(file);
  await reopened.locator('[data-step="preparation"]').click();
  assert.equal(await reopened.locator('[data-preparation-part="reflection"]').isChecked(),false);
  await reopened.close(); await page.close();
});
