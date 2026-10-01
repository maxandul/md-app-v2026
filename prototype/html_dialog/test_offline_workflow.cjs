// Optional browser checks: node --test prototype/html_dialog/test_offline_workflow.cjs
// Uses Playwright only for development; no runtime dependency in the HTML files.
const { test, before, after } = require('node:test');
const assert = require('node:assert/strict');
const { chromium } = require('playwright');
const fs = require('node:fs/promises');
const os = require('node:os');
const path = require('node:path');
const { pathToFileURL } = require('node:url');
let browser, dir, fixture, importFixture, base;
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
async function importReturn(page,section,file) {
  await page.locator(`.workflow-nav [data-step="${section}"]`).click();
  await page.locator(`[data-action="import-preparation"][data-section="${section}"]`).click();
  await page.locator('#preparation-import-file').setInputFiles(file);
}
async function preparedFixture(scope='full',selection={reflection:true,review:true,outlook:true,return_review:true,return_outlook:true},name='prep.html',type='annual') {
  const employee = base.employees[0];
  const payload = {version:3,preparation_id:`PREP-${employee.case_id}`,package_id:base.package.package_id,case_id:employee.case_id,scope,dialog_type:type,selection,review_year:base.package.rb_year,outlook_year:base.package.ab_year,period_start:employee.period_start,period_end:employee.period_end,employee:employee.employee,manager:{pn:base.package.manager_pn,name:base.package.manager_name},competency_model:base.configuration.competency_model,previous_goals:employee.previous_goals.map(({id,title,criteria,steps,target_date})=>({id,title,criteria,steps,target_date})),previous_development_goals:[],fields:{}};
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
  base.package.save_hint_dismissed = true;
  base.employees = [base.employees[0]];
  base.employees[0].scope = 'full';
  base.employees[0].previous_goals.forEach(goal => { goal.achievement = ''; goal.review = ''; });
  base.employees[0].review.performance = 'MANAGER_PRIVATE_NOTES';
  base.employees[0].review.manager_comment = 'MANAGER_PRIVATE_COMMENT';
  fixture = path.join(dir,'workbook.html');
  await fs.writeFile(fixture,replaceData(demo,'md-data',base));
  const importData = structuredClone(base);
  importData.employees[0].meta.preparation_selection = {reflection:true,review:true,outlook:true,return_review:true,return_outlook:true};
  importFixture = path.join(dir,'import-workbook.html');
  await fs.writeFile(importFixture,replaceData(demo,'md-data',importData));
});
after(async () => { await browser?.close(); assert.deepEqual(errors,[],'No uncaught browser errors'); await fs.rm(dir,{recursive:true,force:true}); });

test('workbook selects parts, retains mandatory feedback and excludes manager entries',async () => {
  const page = await pageAt(fixture);
  await page.locator('.workflow-nav [data-step="preparation"]').click();
  assert.equal(await page.locator('[data-preparation-part="reflection"]').isChecked(),true);
  assert.equal(await page.locator('[data-preparation-part="review"]').isChecked(),false);
  await page.locator('[data-preparation-part="review"]').check();
  await page.locator('[data-preparation-part="outlook"]').check();
  assert.equal(await page.locator('[data-preparation-part="outlook"]').isChecked(),true);
  await page.locator('[data-preparation-part="return_review"]').check();
  const file = await download(page,'[data-action="download-preparation"]','generated.html');
  const html = await fs.readFile(file,'utf8');
  assert.ok(!html.includes('MANAGER_PRIVATE_NOTES') && !html.includes('MANAGER_PRIVATE_COMMENT'));
  const payload = dataOf(html,'prep-data');
  assert.equal(payload.employee.employment_assignment,'1');
  assert.equal(payload.selection.return_review,true);
  assert.equal(payload.selection.return_outlook,false);
  assert.equal(payload.previous_goals[0].title,base.employees[0].previous_goals[0].title);
  const generated = await pageAt(file);
  assert.deepEqual(await generated.locator('[role="tab"]').allTextContents(),['Reflexion','Rückblick','Ausblick','Feedback']);
  if (process.env.MD_TEST_SCREENSHOTS) { await generated.screenshot({path:path.join(process.env.MD_TEST_SCREENSHOTS,'preparation-reflection.png'),fullPage:true}); await generated.locator('[data-tab="review-section"]').click(); await generated.screenshot({path:path.join(process.env.MD_TEST_SCREENSHOTS,'preparation-review.png'),fullPage:true}); }
  await generated.close();
  for (const part of ['reflection','review','outlook']) await page.locator(`[data-preparation-part="${part}"]`).uncheck();
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
  await page.locator('[data-field="feedback_keep"]').fill('FEEDBACK_PRIVATE_391');
  await page.locator('[data-tab="review-section"]').click();
  await page.locator('#return-review').click();
  const returned = await download(page,'#return-confirm','returned-review.html');
  await page.locator('[data-tab="outlook-section"]').click();
  await page.locator('#return-outlook').click();
  const outlookReturn = await download(page,'#return-confirm','returned-outlook.html');
  const html = await fs.readFile(returned,'utf8');
  assert.ok(!html.includes('REFLECTION_SECRET_829') && !html.includes('PRIVATE_FUTURE_721'));
  const data = dataOf(html,'prep-data');
  assert.deepEqual(data.fields,{});
  assert.ok(!html.includes('FEEDBACK_PRIVATE_391') && !html.includes('Neues Ziel'));
  assert.equal(data.return_section,'review');
  assert.deepEqual(Object.keys(data.prepared),['review']);
  assert.equal(data.prepared.review.performance,'Meine Leistung');
  const outlookData = dataOf(await fs.readFile(outlookReturn,'utf8'),'prep-data');
  assert.equal(outlookData.prepared.outlook.performance_goals[0].title,'Neues Ziel');
  assert.deepEqual(Object.keys(outlookData.prepared),['outlook']);
  assert.ok(!(await fs.readFile(outlookReturn,'utf8')).includes('FEEDBACK_PRIVATE_391'));
  assert.equal(data.selection.reflection,false);
  assert.equal(await page.locator('#save-html').isEnabled(),true,'Return export does not falsely save own notes');
  const own = await download(page,'#save-html','own.html');
  assert.ok((await fs.readFile(own,'utf8')).includes('REFLECTION_SECRET_829'));
  const reopened = await pageAt(own);
  assert.equal(await reopened.locator('[data-field="review_performance"]').inputValue(),'REFLECTION_SECRET_829');
  await reopened.close();
  const returnPage = await pageAt(returned);
  assert.deepEqual(await returnPage.locator('[role="tab"]').allTextContents(),['Rückblick']);
  await returnPage.close(); await page.close();
});

test('separate imports keep all manager entries and display fixed employee contributions beside them',async () => {
  const page = await pageAt(importFixture);
  await page.locator('.workflow-nav [data-step="preparation"]').click();
  for (const section of ['review','outlook']) {
    await importReturn(page,section,path.join(dir,`returned-${section}.html`));
    await page.locator('#preparation-import-dialog[open]').waitFor();
    if (process.env.MD_TEST_SCREENSHOTS) await page.screenshot({path:path.join(process.env.MD_TEST_SCREENSHOTS,'import-preview.png'),fullPage:true});
    assert.equal(await page.locator('[data-import-entry]').count(),0);
    await page.locator('#preparation-import-confirm').click();
  }
  await page.locator('.workflow-nav [data-step="review"]').click();
  assert.equal(await page.locator('[data-bind="review.performance"]').inputValue(),'MANAGER_PRIVATE_NOTES');
  assert.ok((await page.locator('.ma-fixed').allTextContents()).some(text=>text.includes('Meine Leistung')));
  await page.locator('[data-bind="review.performance"]').fill('Eigene vorbereitete Einschätzung');
  if (process.env.MD_TEST_SCREENSHOTS) await page.locator('.field').filter({has:page.locator('[data-bind="review.performance"]')}).screenshot({path:path.join(process.env.MD_TEST_SCREENSHOTS,'manager-with-contributions.png')});
  const saved = await download(page,'#save-button','imported.html');
  const data = dataOf(await fs.readFile(saved,'utf8'),'md-data');
  assert.equal(data.employees[0].review.performance,'Eigene vorbereitete Einschätzung');
  assert.equal(data.employees[0].outlook.performance_goals.length,0);
  assert.equal(data.employees[0].previous_goals[0].achievement,'');
  assert.ok(data.employees[0].ma_preparation.review.entries.some(item=>item.value==='Meine Leistung'));
  assert.ok(data.employees[0].ma_preparation.outlook.entries.some(item=>item.path==='outlook.performance_goals'));
  assert.ok(!JSON.stringify(data.employees[0].ma_preparation).includes('FEEDBACK_PRIVATE_391'));
  await page.locator('.workflow-nav [data-step="preparation"]').click();
  await importReturn(page,'review',path.join(dir,'returned-review.html'));
  await page.locator('#preparation-import-dialog[open]').waitFor();
  await page.locator('#preparation-import-confirm').click();
  const repeated = dataOf(await fs.readFile(await download(page,'#save-button','repeated.html'),'utf8'),'md-data');
  assert.equal(repeated.employees[0].review.performance,'Eigene vorbereitete Einschätzung');
  assert.deepEqual(repeated.employees[0].ma_preparation.outlook,data.employees[0].ma_preparation.outlook);
  const reopened = await pageAt(saved);
  await reopened.locator('.workflow-nav [data-step="review"]').click();
  assert.ok((await reopened.locator('.ma-fixed').allTextContents()).some(text=>text.includes('Meine Leistung')));
  await reopened.close(); await page.close();
});

test('personal files and mismatched employment, round, manager, scope and period are rejected',async () => {
  const page = await pageAt(importFixture);
  await page.locator('.workflow-nav [data-step="preparation"]').click();
  await importReturn(page,'review',path.join(dir,'own.html'));
  await page.waitForFunction(()=>document.querySelector('#toast').textContent.includes('separate'));
  assert.equal(await page.locator('#preparation-import-dialog').evaluate(el=>el.open),false);
  const html = await fs.readFile(path.join(dir,'returned-review.html'),'utf8');
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

test('direct saving reuses chosen handle and cancellation does not download',async () => {
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
  assert.equal(await page.locator('#save-copy').count(),0);
  let downloads=0; page.on('download',()=>downloads++);
  const fresh = await pageAt(await preparedFixture('full',undefined,'cancel.html'));
  fresh.on('download',()=>downloads++);
  await fresh.evaluate(()=>window.showSaveFilePicker=async()=>{throw new DOMException('Abgebrochen','AbortError')});
  await fresh.locator('[data-field="review_performance"]').fill('Noch nicht gespeichert');
  await fresh.locator('#save-html').click();
  assert.equal(await fresh.locator('#save-html').isEnabled(),true);
  await fresh.close();
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
  await page.locator('.workflow-nav [data-step="preparation"]').click();
  await page.locator('[data-preparation-part="review"]').check();
  await page.locator('#save-button').click();
  await page.waitForFunction(()=>window.output.length===1);
  const first = dataOf(await page.evaluate(()=>window.output[0]),'md-data');
  assert.equal(first.package.revision,base.package.revision+1);
  await page.locator('[data-preparation-part="reflection"]').uncheck();
  await page.locator('#save-button').click();
  await page.waitForFunction(()=>window.output.length===2);
  assert.equal(await page.evaluate(()=>window.calls),1);
  const file = path.join(dir,'native-workbook.html'); await fs.writeFile(file,await page.evaluate(()=>window.output[1]));
  const reopened = await pageAt(file);
  await reopened.locator('.workflow-nav [data-step="preparation"]').click();
  assert.equal(await reopened.locator('[data-preparation-part="reflection"]').isChecked(),false);
  await reopened.close(); await page.close();
});


test('save explanation can be dismissed and stays dismissed in the saved workbook',async () => {
  const content = await fs.readFile(fixture,'utf8');
  const payload = dataOf(content,'md-data'); payload.package.save_hint_dismissed = false;
  const file = path.join(dir,'save-explanation.html'); await fs.writeFile(file,replaceData(content,'md-data',payload));
  const page = await pageAt(file);
  await page.locator('.workflow-nav [data-step="preparation"]').click();
  await page.locator('[data-preparation-part="review"]').check();
  await page.locator('#save-button').click();
  await page.locator('#save-hint-dialog[open]').waitFor();
  assert.ok((await page.locator('#save-hint-dialog').textContent()).includes('Datei frisch per E-Mail erhalten'));
  await page.locator('#save-hint-cancel').click();
  assert.equal(await page.locator('#save-button').isEnabled(),true);
  await page.locator('#save-button').click();
  await page.locator('#save-hint-dismiss').check();
  const saved = await download(page,'#save-hint-confirm','save-dismissed.html');
  assert.equal(dataOf(await fs.readFile(saved,'utf8'),'md-data').package.save_hint_dismissed,true);
  const reopened = await pageAt(saved);
  await reopened.locator('.workflow-nav [data-step="preparation"]').click();
  await reopened.locator('[data-preparation-part="outlook"]').check();
  await download(reopened,'#save-button','save-again.html');
  assert.equal(await reopened.locator('#save-hint-dialog').evaluate(el=>el.open),false);
  assert.equal(await reopened.locator('#save-copy-button').count(),0);
  await reopened.close(); await page.close();
});

test('preparation without requested returns offers forms but no return buttons',async () => {
  const page = await pageAt(await preparedFixture('full',{reflection:true,review:true,outlook:true,return_review:false,return_outlook:false},'optional-forms.html'));
  assert.deepEqual(await page.locator('[role="tab"]').allTextContents(),['Reflexion','Rückblick','Ausblick','Feedback']);
  assert.equal(await page.locator('#return-review').count(),0);
  assert.equal(await page.locator('#return-outlook').count(),0);
  await page.locator('[data-tab="review-section"]').click();
  assert.ok(!(await page.locator('#review-section').textContent()).includes('Rückgabe wurde nicht angefordert'));
  await page.close();
});


test('preparation hints and end-of-form buttons match all valid scope and return combinations',async () => {
  for (const scope of ['full','review_only','outlook_only']) {
    const reviewModes = scope === 'outlook_only' ? [0] : [0,1,2];
    const outlookModes = scope === 'review_only' ? [0] : [0,1,2];
    for (const reflection of [false,true]) for (const review of reviewModes) for (const outlook of outlookModes) {
      const selection = {reflection,review:review>0,outlook:outlook>0,return_review:review===2,return_outlook:outlook===2};
      const page = await pageAt(await preparedFixture(scope,selection,'matrix.html'));
      const hasFeedback = scope !== 'outlook_only';
      assert.equal(await page.locator('#feedback-section [data-action="print-feedback"]').count(),hasFeedback ? 1 : 0);
      if (!hasFeedback) assert.ok(!(await page.locator('#app').innerText()).toLowerCase().includes('feedback'));
      for (const section of ['review','outlook']) {
        const requested = selection['return_'+section];
        assert.equal(await page.locator('#return-'+section).count(),requested ? 1 : 0);
        if (requested) {
          assert.equal(await page.locator('#return-'+section).evaluate(el=>el.closest('[role="tabpanel"]').id),section+'-section');
          assert.equal(await page.locator('#return-'+section).evaluate(el=>el.closest('.section').lastElementChild.contains(el)),true);
          await page.locator('[data-tab="'+section+'-section"]').click();
          await page.locator('#return-'+section).click();
          const dialog = await page.locator('#return-dialog').innerText();
          assert.ok(!dialog.includes('anderen Gesprächsteil'));
          if (!hasFeedback) assert.ok(!dialog.toLowerCase().includes('feedback'));
          if (!reflection) assert.ok(!dialog.toLowerCase().includes('reflexion'));
          await page.locator('#return-cancel').click();
        }
      }
      assert.equal(await page.locator('#requested-return-note').isVisible(),review===2 || outlook===2);
      await page.close();
    }
  }
});

test('import buttons belong to requested conversation parts and reject a return for the other part',async () => {
  const page = await pageAt(fixture);
  for (const step of ['preparation','review','outlook']) {
    await page.locator('.workflow-nav [data-step="'+step+'"]').click();
    assert.equal(await page.locator('[data-action="import-preparation"]').count(),0);
  }
  await page.locator('.workflow-nav [data-step="preparation"]').click();
  await page.locator('[data-preparation-part="review"]').check();
  await page.locator('[data-preparation-part="return_review"]').check();
  await page.locator('.workflow-nav [data-step="review"]').click();
  assert.equal(await page.locator('[data-action="import-preparation"][data-section="review"]').count(),1);
  await importReturn(page,'review',path.join(dir,'returned-outlook.html'));
  await page.waitForFunction(()=>document.querySelector('#toast').textContent.includes('passenden Gesprächsteil'));
  assert.equal(await page.locator('#preparation-import-dialog').evaluate(el=>el.open),false);
  await page.close();
});

test('employee contributions are included in PDFs and can be removed without changing manager inputs',async () => {
  const page = await pageAt(importFixture);
  for (const section of ['review','outlook']) {
    await importReturn(page,section,path.join(dir,`returned-${section}.html`));
    await page.locator('#preparation-import-dialog[open]').waitFor();
    await page.locator('#preparation-import-confirm').click();
  }
  await page.evaluate(()=>{window.confirm=()=>true;window.print=()=>{};});
  for (const section of ['review','outlook']) {
    await page.locator('.workflow-nav [data-step="finish"]').click();
    await page.locator('[data-action="print-'+section+'"]').click();
    const text = await page.locator('#print-root').textContent();
    assert.ok(text.includes('Beiträge der mitarbeitenden Person aus der Vorbereitung'));
    assert.ok(text.includes(section==='review' ? 'Meine Leistung' : 'Neues Ziel'));
    assert.ok(!text.includes(section==='review' ? 'Neues Ziel' : 'Meine Leistung'));
    assert.ok(!text.includes('FEEDBACK_PRIVATE_391') && !text.includes('REFLECTION_SECRET_829'));
    if (process.env.MD_TEST_PDF_DIR) await page.pdf({path:path.join(process.env.MD_TEST_PDF_DIR,section+'.pdf'),format:'A4',printBackground:true,preferCSSPageSize:true});
    await page.evaluate(()=>window.dispatchEvent(new Event('afterprint')));
  }
  await page.locator('.workflow-nav [data-step="review"]').click();
  await page.locator('[data-action="remove-contribution"][data-path="review.performance"]').click();
  assert.equal(await page.locator('[data-bind="review.performance"]').inputValue(),'MANAGER_PRIVATE_NOTES');
  assert.ok(!(await page.locator('.ma-fixed').allTextContents()).some(text=>text.includes('Meine Leistung')));
  await page.locator('.workflow-nav [data-step="finish"]').click();
  await page.locator('[data-action="print-review"]').click();
  assert.ok(!(await page.locator('#print-root').textContent()).includes('Meine Leistung'));
  await page.evaluate(()=>window.dispatchEvent(new Event('afterprint')));
  const saved = await download(page,'#save-button','removed-contribution.html');
  const data = dataOf(await fs.readFile(saved,'utf8'),'md-data');
  assert.ok(!data.employees[0].ma_preparation.review.entries.some(entry=>entry.path==='review.performance'));
  assert.ok(data.employees[0].ma_preparation.outlook.entries.length>0);
  await page.close();
});
