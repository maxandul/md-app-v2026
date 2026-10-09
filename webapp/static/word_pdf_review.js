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

const conducted = document.querySelector('[name="conducted"]');
function updateRequiredFields() {
  document.querySelector('[name="dialog_date"]').required = conducted.value !== 'nein';
  document.querySelector('[name="no_md_reason"]').required = conducted.value === 'nein';
}
conducted.addEventListener('change', updateRequiredFields);
updateRequiredFields();

let reviewDirty = false;
const reviewForm = document.querySelector('[data-review-form]');
reviewForm.addEventListener('input', () => { reviewDirty = true; });
reviewForm.addEventListener('change', () => { reviewDirty = true; });
reviewForm.addEventListener('submit', () => { reviewDirty = false; });
window.addEventListener('beforeunload', event => { if (reviewDirty) { event.preventDefault(); event.returnValue = ''; } });
