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
  await page.locator('[data-prepared="review.overall_rating"]').selectOption('B – sehr gut');
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
  assert.equal(data.prepared.review.overall_rating,'B – sehr gut');
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
    if (section==='review') { assert.ok(text.includes('Gesamtbewertung aus Mitarbeitendensicht')); assert.ok(text.includes('B – sehr gut')); }
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

test('red data notices, optional feedback and conditional return guidance survive saving',async () => {
  const page = await pageAt(fixture);
  await page.locator('#guidance-button').click();
  const notice = page.locator('#guidance-dialog .data-storage-note');
  assert.ok((await notice.textContent()).includes('automatisch an deine Mitarbeitenden oder an HR'));
  assert.equal(await notice.evaluate(el => getComputedStyle(el).borderLeftColor),'rgb(217, 60, 26)');
  assert.ok((await page.locator('#guidance-dialog').textContent()).includes('5 · Dokumente fertigstellen'));
  await page.locator('[data-guidance-close]').click();
  await page.locator('.workflow-nav [data-step="preparation"]').click();
  const feedback = page.locator('[data-preparation-part="feedback"]');
  assert.equal(await feedback.isChecked(),true);
  assert.equal(await feedback.isDisabled(),true);
  assert.equal(await page.locator('input[type="checkbox"]').first().getAttribute('data-preparation-part'),'feedback');
  assert.ok(!(await page.locator('#editor').innerText()).includes('Rückgabe:'));
  await page.locator('summary').filter({hasText:'Reflexionsfragen ansehen'}).click();
  assert.ok((await page.locator('#editor').innerText()).includes('Was waren deine wichtigsten Erfolge?'));
  await page.locator('.workflow-nav [data-step="basics"]').click();
  await page.locator('label').filter({has:page.locator('[data-bind="scope"][value="outlook_only"]')}).click();
  await page.locator('.workflow-nav [data-step="preparation"]').click();
  assert.equal(await feedback.isChecked(),false);
  assert.equal(await feedback.isDisabled(),false);
  await feedback.check();
  assert.equal(await page.locator('label').filter({hasText:'Das Feedback wird nach der Besprechung im Gespräch oder anschliessend separat'}).locator('input').isChecked(),true);
  await page.locator('[data-preparation-part="reflection"]').uncheck();
  await page.locator('[data-preparation-part="outlook"]').check();
  await page.locator('[data-preparation-part="return_outlook"]').check();
  assert.ok((await page.locator('#editor').innerText()).includes('im betreffenden Rückblick oder Ausblick importiert'));
  const file = await download(page,'[data-action="download-preparation"]','optional-feedback.html');
  const prepared = await pageAt(file);
  assert.deepEqual(await prepared.locator('[role="tab"]').allTextContents(),['Ausblick','Feedback']);
  assert.ok(!(await prepared.locator('#app').innerText()).includes('Deine persönliche Reflexion bleibt bei dir.'));
  assert.ok((await prepared.locator('.data-storage-note').textContent()).includes('automatisch an deine/n Vorgesetzte/n oder an HR'));
  assert.equal(await prepared.locator('.data-storage-note').evaluate(el => getComputedStyle(el).backgroundColor),'rgb(255, 240, 236)');
  await prepared.locator('[data-tab="feedback-section"]').click();
  assert.ok(!(await prepared.locator('#feedback-section').innerText()).includes('obligatorisch'));
  await prepared.locator('[data-field="feedback_keep"]').fill('OPTIONAL_FEEDBACK_PRIVATE');
  const own = await download(prepared,'#save-html','optional-saved.html');
  const reopened = await pageAt(own);
  await reopened.locator('[data-tab="feedback-section"]').click();
  assert.equal(await reopened.locator('[data-field="feedback_keep"]').inputValue(),'OPTIONAL_FEEDBACK_PRIVATE');
  await prepared.locator('[data-tab="outlook-section"]').click();
  await prepared.locator('#return-outlook').click();
  const returned = await download(prepared,'#return-confirm','optional-return.html');
  const returnPage = await pageAt(returned);
  assert.equal(await returnPage.locator('[data-tab="feedback-section"]').count(),0);
  assert.ok(!(await fs.readFile(returned,'utf8')).includes('OPTIONAL_FEEDBACK_PRIVATE'));
  await feedback.uncheck();
  const noFeedback = await pageAt(await download(page,'[data-action="download-preparation"]','no-feedback.html'));
  assert.equal(await noFeedback.locator('[data-tab="feedback-section"]').count(),0);
  if(process.env.MD_TEST_SCREENSHOTS) {
    await page.screenshot({path:path.join(process.env.MD_TEST_SCREENSHOTS,'workbook-v5.png'),fullPage:true});
    await prepared.screenshot({path:path.join(process.env.MD_TEST_SCREENSHOTS,'preparation-v5.png'),fullPage:true});
  }
  for(const p of [page,prepared,reopened,returnPage,noFeedback]) await p.close();
});

test('feedback competencies start empty, grow dynamically and survive removal and reopening',async () => {
  const page = await pageAt(await preparedFixture());
  const saving = await page.locator('.intro').textContent();
  assert.ok(saving.includes('beim nächsten Speichern automatisch überschrieben'));
  assert.ok(!saving.includes('Wenn dein Browser'));
  await page.locator('[data-tab="review-section"]').click();
  assert.ok((await page.locator('#review-section').innerText()).includes('das finale Rückblick-Dokument erstellt deine Führungskraft im Gespräch mit dir.'));
  await page.locator('[data-tab="feedback-section"]').click();
  assert.equal(await page.locator('#feedback-section .competency-row').count(),0);
  assert.ok((await page.locator('#feedback-section .warning-note').first().innerText()).startsWith('Das Feedback ist obligatorisch.'));
  assert.ok((await page.locator('#feedback-section .warning-note').last().innerText()).includes('sobald ihr dein Feedback besprochen habt'));
  const competency = base.configuration.competency_model[0].competencies[0].name;
  for(let index=1;index<=4;index++) {
    await page.locator('[data-action="add-feedback-competency"]').click();
    await page.locator(`[data-field="feedback_competency_${index}"]`).selectOption(competency);
    await page.locator(`[data-field="feedback_competency_text_${index}"]`).fill('Beobachtung '+index);
  }
  assert.equal(await page.locator('#feedback-section .competency-row').count(),4);
  await page.locator('[data-action="remove-feedback-competency"][data-feedback-index="2"]').click();
  assert.equal(await page.locator('#feedback-section .competency-row').count(),3);
  assert.equal(await page.locator('[data-field="feedback_competency_text_4"]').inputValue(),'Beobachtung 4');
  const saved = await download(page,'#save-html','dynamic-feedback.html');
  const reopened = await pageAt(saved);
  await reopened.locator('[data-tab="feedback-section"]').click();
  assert.equal(await reopened.locator('#feedback-section .competency-row').count(),3);
  assert.equal(await reopened.locator('[data-field="feedback_competency_text_4"]').inputValue(),'Beobachtung 4');
  await reopened.evaluate(()=>{window.print=()=>{};});
  await reopened.locator('[data-action="print-feedback"]').click();
  const text = await reopened.locator('#print-root').innerText();
  for(const index of [1,3,4]) assert.ok(text.includes('Beobachtung '+index));
  assert.ok(!text.includes('Beobachtung 2'));
  if(process.env.MD_TEST_PDF_DIR) await reopened.pdf({path:path.join(process.env.MD_TEST_PDF_DIR,'feedback.pdf'),format:'A4',printBackground:true,preferCSSPageSize:true});
  await reopened.evaluate(()=>window.dispatchEvent(new Event('afterprint')));
  if(process.env.MD_TEST_SCREENSHOTS) {
    await reopened.evaluate(()=>window.scrollTo(0,0));
    await reopened.screenshot({path:path.join(process.env.MD_TEST_SCREENSHOTS,'feedback-v6.png'),fullPage:true});
  }
  // Earlier files stored up to three flat field pairs, including comment-only entries.
  const legacy = dataOf(await fs.readFile(saved,'utf8'),'prep-data');
  delete legacy.feedback_competency_indices;
  legacy.fields = {feedback_competency_1:competency,feedback_competency_text_1:'Bisheriger Beitrag',feedback_competency_text_3:'Nur Beobachtung'};
  const legacyFile = path.join(dir,'legacy-feedback.html');
  await fs.writeFile(legacyFile,replaceData(await fs.readFile(saved,'utf8'),'prep-data',legacy));
  const migrated = await pageAt(legacyFile);
  await migrated.locator('[data-tab="feedback-section"]').click();
  assert.equal(await migrated.locator('#feedback-section .competency-row').count(),2);
  assert.equal(await migrated.locator('[data-field="feedback_competency_text_3"]').inputValue(),'Nur Beobachtung');
  for(const p of [page,reopened,migrated]) await p.close();
});

test('scope confirmation survives saving and is invalidated by local and SAP scope changes', async () => {
  const page = await pageAt(fixture);
  assert.equal(await page.locator('#guidance-dialog').evaluate(el=>el.open),false);
  assert.equal(await page.locator('#process-overview').evaluate(el=>el.open),true);
  assert.ok((await page.locator('.workflow-nav').innerText()).includes('Noch prüfen'));
  await page.locator('[data-action="confirm-scope"]').click();
  assert.ok((await page.locator('.workflow-nav').innerText()).includes('Umfang bestätigt'));
  await page.locator('#process-overview > summary').click();
  assert.equal(await page.locator('#process-overview').evaluate(el=>el.open),false);
  const saved = await download(page,'#save-button','confirmed.html');
  const data = dataOf(await fs.readFile(saved,'utf8'),'md-data');
  assert.ok(data.employees[0].meta.scope_confirmation);
  const reopened = await pageAt(saved);
  assert.equal(await reopened.locator('#process-overview').evaluate(el=>el.open),false);
  assert.ok((await reopened.locator('.workflow-nav').innerText()).includes('Umfang bestätigt'));
  await reopened.locator('.workflow-nav [data-step="basics"]').click();
  await reopened.locator('label').filter({has:reopened.locator('[data-bind="scope"][value="review_only"]')}).click();
  assert.equal(await reopened.locator('[data-action="confirm-scope"]').isDisabled(),true);
  await reopened.locator('[data-bind="scope_reason"]').fill('Dokumentierter Spezialfall');
  assert.equal(await reopened.locator('[data-action="confirm-scope"]').isDisabled(),false);
  await reopened.locator('[data-action="confirm-scope"]').click();
  assert.deepEqual(await reopened.locator('.workflow-nav button').allTextContents().then(items=>items.map(t=>t.split(' · ')[0])),['1','2','3','4']);
  assert.equal(await reopened.locator('.workflow-nav [data-step="outlook"]').count(),0);
  data.employees[0].suggestion.scope = 'review_only';
  const updated = path.join(dir,'sap-scope-change.html');
  await fs.writeFile(updated,replaceData(await fs.readFile(saved,'utf8'),'md-data',data));
  const changed = await pageAt(updated);
  assert.ok((await changed.locator('.workflow-nav').innerText()).includes('Noch prüfen'));
  for (const p of [page,reopened,changed]) await p.close();
});

test('no-MD scope collects its reason before confirmation and closes only after confirmation', async () => {
  const page = await pageAt(fixture);
  await page.locator('label').filter({has:page.locator('[data-bind="scope"][value="none"]')}).click();
  assert.equal(await page.locator('[data-action="confirm-scope"]').isDisabled(),true);
  const reason = await page.locator('[data-bind="no_md_reason"] option').evaluateAll(items=>items.find(item=>item.value && item.value !== 'Anderer Grund').value);
  await page.locator('[data-bind="no_md_reason"]').selectOption(reason);
  await page.locator('[data-action="confirm-scope"]').click();
  assert.equal(await page.locator('.workflow-nav button').count(),2);
  assert.equal(await page.locator('[data-action="close-case"]').isDisabled(),false);
  page.removeAllListeners('dialog'); page.on('dialog',dialog=>dialog.accept());
  await page.locator('[data-action="close-case"]').click();
  assert.equal(await page.locator('[data-action="reopen-case"]').count(),1);
  const saved = await download(page,'#save-button','closed-none.html');
  assert.equal(dataOf(await fs.readFile(saved,'utf8'),'md-data').employees[0].meta.closed,true);
  await page.close();
});

test('preparation creation status survives reopen and changes to regenerate after selection edits', async () => {
  const page = await pageAt(fixture);
  await page.locator('[data-action="confirm-scope"]').click();
  await download(page,'[data-action="download-preparation"]','status-preparation.html');
  assert.ok((await page.locator('.workflow-nav').innerText()).includes('Datei erstellt'));
  const saved = await download(page,'#save-button','preparation-status.html');
  const reopened = await pageAt(saved);
  assert.ok((await reopened.locator('.workflow-nav').innerText()).includes('Datei erstellt'));
  await reopened.locator('.workflow-nav [data-step="preparation"]').click();
  await reopened.locator('[data-preparation-part="reflection"]').uncheck();
  assert.ok((await reopened.locator('.workflow-nav').innerText()).includes('Neu erstellen'));
  await reopened.locator('[data-preparation-part="review"]').check();
  await reopened.locator('[data-preparation-part="return_review"]').check();
  const explanation = await reopened.locator('.hr-recommendation').filter({hasText:'Was bedeutet'}).innerText();
  assert.ok(explanation.includes('Personaldossier'));
  assert.ok(explanation.includes('Beitrag entfernen'));
  assert.ok(!explanation.includes('Die persönliche Reflexion'));
  assert.ok(explanation.includes('Das Feedback ist nicht Bestandteil'));
  await download(reopened,'[data-action="download-preparation"]','status-regenerated.html');
  assert.ok((await reopened.locator('.workflow-nav').innerText()).includes('Datei erstellt'));
  for (const p of [page,reopened]) await p.close();
});
