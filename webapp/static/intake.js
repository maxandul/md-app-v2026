/* Retain old inbox bookmarks after splitting the long intake page. */
(() => {
  const tabs = document.querySelector('[data-intake-tab]');
  if (tabs && tabs.dataset.intakeTab !== 'mail' && location.hash === '#postfach') {
    const url = new URL(location.href);
    url.searchParams.set('tab', 'mail');
    location.replace(url.href);
  }
})();
