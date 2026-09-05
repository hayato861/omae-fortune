document.addEventListener("DOMContentLoaded", () => {
  const form = document.querySelector("[data-fortune-form]");
  form?.addEventListener("submit", () => {
    const submit = form.querySelector('button[type="submit"]');
    submit.disabled = true;
    submit.querySelector("span").textContent = "百烈鬼が見抜いてる…";
    form.setAttribute("aria-busy", "true");
  });

  const button = document.querySelector(".share-result");
  if (!button) return;

  button.addEventListener("click", async () => {
    const profile = document.querySelector(".oni-profile");
    const status = document.querySelector(".share-status");
    const text = `${profile.dataset.shareName}の守護鬼は「${profile.dataset.shareOni}」だった。気をつけるべきは「${profile.dataset.shareHell}」だとよ。\n#百烈鬼の鬼占 #鬼印診断`;
    try {
      if (navigator.share) {
        await navigator.share({ title: "百烈鬼の鬼印診断", text, url: window.location.origin });
        status.textContent = "知らせてやったぜ。";
      } else if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(`${text}\n${window.location.origin}`);
        status.textContent = "結果をコピーしたぜ。好きな場所へ貼りな。";
      } else {
        const fallback = document.createElement("textarea");
        fallback.value = `${text}\n${window.location.origin}`;
        fallback.setAttribute("readonly", "");
        fallback.className = "copy-fallback";
        document.body.appendChild(fallback);
        fallback.select();
        document.execCommand("copy");
        fallback.remove();
        status.textContent = "結果をコピーしたぜ。好きな場所へ貼りな。";
      }
    } catch (error) {
      if (error.name !== "AbortError") status.textContent = "うまく渡せねえ。もう一度押してみな。";
    }
  });
});
