// Stop double submissions: after the first click, the submit button is disabled.
// (The server also protects itself with redirect-after-POST and database constraints.)
document.addEventListener("submit", function (event) {
  var form = event.target;
  if (!form || form.method.toLowerCase() !== "post") { return; }
  setTimeout(function () {
    form.querySelectorAll('button[type="submit"], input[type="submit"]').forEach(function (button) {
      button.disabled = true;
      button.dataset.originalText = button.textContent;
      button.textContent = "Please wait…";
    });
  }, 0);
});
// If the user comes back with the browser's Back button, make the buttons usable again.
window.addEventListener("pageshow", function (event) {
  if (!event.persisted) { return; }
  document.querySelectorAll("button[disabled][data-original-text]").forEach(function (button) {
    button.disabled = false;
    button.textContent = button.dataset.originalText;
  });
});
