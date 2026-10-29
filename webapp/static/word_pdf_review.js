document.querySelectorAll('.add-goal').forEach(button => {
  button.addEventListener('click', () => {
    const body = document.getElementById(button.dataset.group + '-rows');
    const row = body.querySelector('tr').cloneNode(true);
    row.querySelectorAll('textarea,select').forEach(field => { field.value = ''; });
    body.appendChild(row);
    reviewDirty = true;
  });
});
document.addEventListener('click', event => {
  if (!event.target.matches('.remove-goal')) return;
  reviewDirty = true;
  const row = event.target.closest('tr');
  if (row.parentElement.children.length > 1) row.remove();
  else row.querySelectorAll('textarea,select').forEach(field => { field.value = ''; });
});

const field = name => document.querySelector(`[name="${name}"]`);
function updateRequiredFields() {
  const regularReview = field('document_kind').value === 'review' && field('probation').value !== 'ja';
  const option = field('case_id').selectedOptions[0];
  for (const name of ['period_start', 'period_end']) {
    field(name).required = regularReview;
    field(name).min = regularReview ? (option?.dataset.reviewMin || '') : '';
    field(name).max = regularReview ? (option?.dataset.reviewMax || '') : '';
  }
  field('rating').required = regularReview && field('conducted').value !== 'nein';
  field('dialog_date').required = false;
  field('no_md_reason').required = false;
}
for (const name of ['conducted', 'document_kind', 'probation', 'case_id']) {
  field(name).addEventListener('change', updateRequiredFields);
}
updateRequiredFields();

let reviewDirty = false;
const reviewForm = document.querySelector('[data-review-form]');
reviewForm.addEventListener('input', () => { reviewDirty = true; });
reviewForm.addEventListener('change', () => { reviewDirty = true; });
reviewForm.addEventListener('submit', () => { reviewDirty = false; });
window.addEventListener('beforeunload', event => { if (reviewDirty) { event.preventDefault(); event.returnValue = ''; } });
