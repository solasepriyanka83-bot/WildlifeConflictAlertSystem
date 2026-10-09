// Shared frontend behavior for WildSense dashboard.
// Page-specific auto-refresh / simulate logic lives inline in each template
// (live_status.html, alerts.html) since it needs page-specific DOM targets.

document.addEventListener("DOMContentLoaded", () => {
  // Auto-dismiss flash messages after 4s
  document.querySelectorAll(".flash").forEach((el) => {
    setTimeout(() => {
      el.style.transition = "opacity 0.4s ease";
      el.style.opacity = "0";
      setTimeout(() => el.remove(), 400);
    }, 4000);
  });
});
