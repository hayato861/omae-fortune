document.addEventListener("DOMContentLoaded", () => {
  const track = (event) => {
    const body = JSON.stringify({ event });
    if (navigator.sendBeacon) {
      navigator.sendBeacon("/events", new Blob([body], { type: "application/json" }));
    } else {
      fetch("/events", { method: "POST", headers: { "Content-Type": "application/json" }, body, keepalive: true }).catch(() => {});
    }
  };

  document.querySelectorAll("[data-track]").forEach((link) => {
    link.addEventListener("click", () => track(link.dataset.track));
  });

  const form = document.querySelector("[data-fortune-form]");
  const dateParts = [...document.querySelectorAll("[data-date-part]")];
  dateParts.forEach((input, index) => {
    input.addEventListener("input", () => {
      input.value = input.value.replace(/\D/g, "").slice(0, input.maxLength);
      if (input.value.length === input.maxLength && dateParts[index + 1]) {
        dateParts[index + 1].focus();
        dateParts[index + 1].select();
      }
    });
    input.addEventListener("keydown", (event) => {
      if (event.key === "Backspace" && input.value === "" && dateParts[index - 1]) {
        dateParts[index - 1].focus();
      }
    });
  });

  form?.addEventListener("submit", () => {
    track("fortune_started");
    const submit = form.querySelector('button[type="submit"]');
    submit.disabled = true;
    submit.querySelector("span").textContent = "百烈鬼が見抜いてる…";
    form.setAttribute("aria-busy", "true");
  });

  const button = document.querySelector(".share-result");
  if (!button) return;

  const roundedRect = (context, x, y, width, height, radius) => {
    context.beginPath();
    context.roundRect(x, y, width, height, radius);
    context.fill();
  };

  const loadImage = (source) => new Promise((resolve, reject) => {
    const image = new Image();
    image.onload = () => resolve(image);
    image.onerror = reject;
    image.src = source;
  });

  const makeCard = async (profile) => {
    await document.fonts?.ready;
    const canvas = document.createElement("canvas");
    canvas.width = 1200;
    canvas.height = 630;
    const context = canvas.getContext("2d");

    const gradient = context.createLinearGradient(0, 0, 1200, 630);
    gradient.addColorStop(0, "#14120f");
    gradient.addColorStop(0.62, "#211b16");
    gradient.addColorStop(1, "#5b1812");
    context.fillStyle = gradient;
    context.fillRect(0, 0, 1200, 630);

    try {
      const character = await loadImage(profile.dataset.cardImage);
      const cropWidth = character.width * 0.54;
      context.globalAlpha = 0.66;
      context.drawImage(character, character.width - cropWidth, 0, cropWidth, character.height, 700, 0, 500, 630);
      context.globalAlpha = 1;
      const veil = context.createLinearGradient(610, 0, 1050, 0);
      veil.addColorStop(0, "#181410");
      veil.addColorStop(1, "rgba(24,20,16,0)");
      context.fillStyle = veil;
      context.fillRect(580, 0, 500, 630);
    } catch (_) {
      // The text-only card remains usable if the image cannot be loaded.
    }

    context.fillStyle = "#d83a27";
    context.fillRect(0, 0, 18, 630);
    context.fillStyle = "#d3a62c";
    context.font = '700 24px "Zen Kaku Gothic New", sans-serif';
    context.fillText("百烈鬼が暴く、てめえの鬼印", 70, 70);

    context.fillStyle = "#ffffff";
    context.font = '800 72px "Shippori Mincho", serif';
    context.fillText(profile.dataset.shareOni, 65, 165);
    context.fillStyle = "#c8c0b2";
    context.font = '700 27px "Zen Kaku Gothic New", sans-serif';
    context.fillText(profile.dataset.shareRole, 70, 212);

    context.fillStyle = "#d83a27";
    roundedRect(context, 66, 248, 150, 90, 10);
    context.fillStyle = "#ffffff";
    context.font = '800 48px "Shippori Mincho", serif';
    context.fillText(`${profile.dataset.shareScore}点`, 87, 310);

    const rows = [
      ["鬼の武器", profile.dataset.shareWeapon],
      ["鬼の弱点", profile.dataset.shareWeakness],
      ["気をつける地獄", profile.dataset.shareHell],
    ];
    rows.forEach(([label, value], index) => {
      const y = 382 + index * 58;
      context.fillStyle = "#a79e90";
      context.font = '700 20px "Zen Kaku Gothic New", sans-serif';
      context.fillText(label, 70, y);
      context.fillStyle = "#ffffff";
      context.font = '700 27px "Shippori Mincho", serif';
      context.fillText(value, 245, y);
    });

    context.fillStyle = "#d3a62c";
    context.font = '800 24px "Shippori Mincho", serif';
    context.fillText("お前は何鬼だ？", 70, 580);
    context.fillStyle = "#aaa194";
    context.font = '600 19px "Zen Kaku Gothic New", sans-serif';
    context.fillText(window.location.origin.replace(/^https?:\/\//, ""), 275, 580);

    return new Promise((resolve) => canvas.toBlob(resolve, "image/png"));
  };

  button.addEventListener("click", async () => {
    const profile = document.querySelector(".oni-profile");
    const status = document.querySelector(".share-status");
    const text = `俺の守護鬼は「${profile.dataset.shareOni}」だった。気をつけるべきは「${profile.dataset.shareHell}」だとよ。\nお前は何鬼だ？\n#百烈鬼の鬼占 #鬼印診断`;
    track("share_started");
    button.disabled = true;
    status.textContent = "鬼印を焼きつけてる…";
    try {
      const blob = await makeCard(profile);
      const file = new File([blob], "oni-jirushi.png", { type: "image/png" });
      if (navigator.share && navigator.canShare?.({ files: [file] })) {
        await navigator.share({ title: "百烈鬼の鬼印診断", text, url: window.location.origin, files: [file] });
        status.textContent = "知らせてやったぜ。";
        track("share_completed");
      } else {
        const download = document.createElement("a");
        download.href = URL.createObjectURL(blob);
        download.download = "oni-jirushi.png";
        download.click();
        URL.revokeObjectURL(download.href);
        await navigator.clipboard?.writeText(`${text}\n${window.location.origin}`);
        status.textContent = "鬼印画像を保存したぜ。投稿文もコピーした。";
        track("share_completed");
      }
    } catch (error) {
      if (error.name !== "AbortError") status.textContent = "うまく渡せねえ。もう一度押してみな。";
    } finally {
      button.disabled = false;
    }
  });
});
