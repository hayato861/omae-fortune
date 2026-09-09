document.addEventListener("DOMContentLoaded", () => {
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
