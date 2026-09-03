document.addEventListener("DOMContentLoaded", () => {
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
      } else {
        await navigator.clipboard.writeText(`${text}\n${window.location.origin}`);
        status.textContent = "結果をコピーしたぜ。好きな場所へ貼りな。";
      }
    } catch (error) {
      if (error.name !== "AbortError") status.textContent = "うまく渡せねえ。もう一度押してみな。";
    }
  });
});
