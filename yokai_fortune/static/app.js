document.addEventListener("DOMContentLoaded", () => {
  const ownerParam = String(window.location.search || "").match(/[?&]owner=([01])(?:&|$)/)?.[1];
  let isOwner = false;
  try {
    if (ownerParam === "1") localStorage.setItem("omae-owner", "1");
    if (ownerParam === "0") localStorage.removeItem("omae-owner");
    isOwner = localStorage.getItem("omae-owner") === "1";
  } catch (_) {}
  const sendEvent = (event) => {
    if (isOwner) return;
    const body = JSON.stringify({ event });
    if (navigator.sendBeacon) {
      navigator.sendBeacon("/events", new Blob([body], { type: "text/plain;charset=UTF-8" }));
    } else {
      fetch("/events", { method: "POST", headers: { "Content-Type": "text/plain;charset=UTF-8" }, body, keepalive: true }).catch(() => {});
    }
  };
  if (document.body.dataset.yokaiPage === "landing") {
    sendEvent("page_view");
    sendEvent("landing_view");
  } else if (document.body.dataset.yokaiPage === "result") {
    sendEvent("fortune_completed");
  }
  document.querySelectorAll("[data-track]").forEach((element) => {
    element.addEventListener("click", () => sendEvent(element.dataset.track));
  });
  const parts = [...document.querySelectorAll("[data-date-part]")];
  parts.forEach((input, index) => {
    input.addEventListener("input", () => {
      input.value = input.value
        .replace(/[０-９]/g, (digit) => String.fromCharCode(digit.charCodeAt(0) - 0xfee0))
        .replace(/\D/g, "")
        .slice(0, input.maxLength);
      if (input.value.length === input.maxLength && parts[index + 1]) {
        parts[index + 1].focus();
        parts[index + 1].select();
      }
    });
    input.addEventListener("keydown", (event) => {
      if (event.key === "Backspace" && input.value === "" && parts[index - 1]) parts[index - 1].focus();
    });
  });
});
