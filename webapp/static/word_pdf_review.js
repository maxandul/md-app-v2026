document.querySelectorAll('.add-goal').forEach(button => {
  button.addEventListener('click', () => {
    const body = document.getElementById(button.dataset.group + '-rows');
    const row = body.querySelector('tr').cloneNode(true);
    row.querySelectorAll('textarea,select').forEach(field => { field.value = ''; });
    body.appendChild(row);
  });
});
document.addEventListener('click', event => {
  if (!event.target.matches('.remove-goal')) return;
  const row = event.target.closest('tr');
  if (row.parentElement.children.length > 1) row.remove();
  else row.querySelectorAll('textarea,select').forEach(field => { field.value = ''; });
});
