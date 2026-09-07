(() => {
  const form = document.querySelector("[data-static-fortune]");
  if (form) {
    form.addEventListener("submit", (event) => {
      if (!form.reportValidity()) return;
      const name = form.elements.name.value.trim();
      const year = form.elements.birthday_year.value.padStart(4, "0");
      const month = form.elements.birthday_month.value.padStart(2, "0");
      const day = form.elements.birthday_day.value.padStart(2, "0");
      const birthday = `${year}-${month}-${day}`;
      const born = new Date(`${birthday}T00:00:00`);
      const valid = name && born.getFullYear() === Number(year) && born.getMonth() + 1 === Number(month) && born.getDate() === Number(day) && born <= new Date();
      if (!valid) return;
      event.preventDefault();
      sessionStorage.setItem("oni-reading", JSON.stringify({ name, birthday }));
      window.location.href = "result.html";
    }, { capture: true });
  }

  if (!document.body.hasAttribute("data-static-result")) return;
  const saved = sessionStorage.getItem("oni-reading");
  sessionStorage.removeItem("oni-reading");
  if (!saved || !window.FORTUNE_DATA) {
    window.location.replace("./#uranau");
    return;
  }

  const { name, birthday } = JSON.parse(saved);
  const data = window.FORTUNE_DATA;
  const reduce = (number) => {
    while (number > 9) number = [...String(number)].reduce((sum, digit) => sum + Number(digit), 0);
    return number;
  };
  const hash = (text) => {
    let value = 2166136261;
    for (const character of text) {
      value ^= character.codePointAt(0);
      value = Math.imul(value, 16777619);
    }
    return value >>> 0;
  };
  const parts = new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Tokyo", year: "numeric", month: "2-digit", day: "2-digit" }).formatToParts(new Date());
  const part = (type) => Number(parts.find((item) => item.type === type).value);
  const today = { year: part("year"), month: part("month"), day: part("day") };
  const todayIso = `${today.year}-${String(today.month).padStart(2, "0")}-${String(today.day).padStart(2, "0")}`;
  const born = birthday.split("-").map(Number);
  const personalYear = reduce(born[1] + born[2] + [...String(today.year)].reduce((sum, digit) => sum + Number(digit), 0));
  const dayNumber = reduce(reduce(personalYear + today.month) + today.day);
  const digits = birthday.replace(/\D/g, "").split("").map(Number);
  let lifeNumber = digits.reduce((sum, digit) => sum + digit, 0);
  while (![11, 22, 33].includes(lifeNumber) && lifeNumber > 9) lifeNumber = [...String(lifeNumber)].reduce((sum, digit) => sum + Number(digit), 0);
  const oni = data.oni[String(lifeNumber)];
  const base = data.fortunes[dayNumber - 1];
  const day = data.days[String(dayNumber)];
  const seed = hash(`${todayIso}:${name}:${birthday}`);
  const score = Math.max(40, Math.min(98, base.score + (seed % 9) - 4));
  const rank = score >= 88 ? "大吉" : score >= 76 ? "吉" : score >= 66 ? "中吉" : score >= 56 ? "小吉" : "末吉";
  const luckyNumber = ((seed >>> 8) % 99) + 1;
  const aspect = data.aspects[hash(`oni-aspect:${name}:${birthday}`) % data.aspects.length];

  const set = (selector, value) => { const node = document.querySelector(selector); if (node) node.textContent = value; };
  document.title = `${name}の今日の運勢｜お前のためだけの占い`;
  set(".result-hero .eyebrow", `${todayIso.replaceAll("-", ".")} / ${name}の運勢`);
  set(".score-ring span", score);
  document.querySelector(".score-ring")?.style.setProperty("--score", score);
  set(".rank", rank);
  set(".result-heading h1", base.headline);
  set(".result-hero blockquote", base.message);
  const reason = document.querySelector(".fortune-reason");
  if (reason) reason.innerHTML = `<b>今日の読み筋：</b>生来の『${oni.weapon}』に、今日は「${day.focus}」の気が重なる。`;
  set(".type-number strong", lifeNumber);
  set(".oni-profile h2", oni.name);
  set(".oni-role", oni.role);
  set(".oni-reading", oni.reading);
  const traits = document.querySelectorAll(".oni-traits strong");
  [oni.weapon, oni.weakness, oni.person].forEach((value, index) => { if (traits[index]) traits[index].textContent = value; });
  set(".hell-card h3", oni.hell);
  set(".hell-escape p", oni.escape);
  set(".free-detail h2", base.action);
  const lucky = document.querySelectorAll(".lucky-row b");
  if (lucky[0]) lucky[0].textContent = base.color;
  if (lucky[1]) lucky[1].textContent = luckyNumber;
  const details = document.querySelectorAll(".daily-detail-grid p");
  [base.work, base.money, base.love, day.social, day.body, day.best_time, day.caution].forEach((value, index) => { if (details[index]) details[index].textContent = value; });
  set(".lock-overlay h2", `12守護鬼 × 5つの相 = 全60鬼\nてめえは「${oni.name}・${aspect.name}」`);
  const profile = document.querySelector(".oni-profile");
  Object.assign(profile.dataset, { shareOni: oni.name, shareRole: oni.role, shareScore: score, shareWeapon: oni.weapon, shareWeakness: oni.weakness, shareHell: oni.hell });
})();
