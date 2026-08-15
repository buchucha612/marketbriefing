const SECTION_ORDER = ["domestic", "us", "macro", "sector"];
const SECTION_INDEX = {
  domestic: "01",
  us: "02",
  macro: "03",
  sector: "04",
};

function formatDateTime(value) {
  if (!value) return "시간 정보 없음";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("ko-KR", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

function clearChildren(node) {
  while (node.firstChild) {
    node.removeChild(node.firstChild);
  }
}

function topicLabel(topic) {
  const labels = {
    domestic: "국내",
    us: "미국",
    macro: "금리·환율·유가·원자재",
    sector: "섹터",
    uncategorized: "미분류",
  };
  return labels[topic] || topic;
}

function renderTopicChips(article) {
  const row = document.createElement("div");
  row.className = "topic-row";

  const primary = document.createElement("span");
  primary.className = "topic-chip primary";
  primary.textContent = `주제: ${topicLabel(article.primary_topic)}`;
  row.appendChild(primary);

  (article.secondary_topics || []).slice(0, 3).forEach((topic) => {
    const chip = document.createElement("span");
    chip.className = "topic-chip";
    chip.textContent = topicLabel(topic);
    row.appendChild(chip);
  });

  return row;
}

function renderPrices(prices) {
  const list = document.querySelector("#activePrices");
  clearChildren(list);
  prices.forEach((text) => {
    const item = document.createElement("li");
    item.textContent = text;
    list.appendChild(item);
  });
}

function renderArticles(section) {
  const list = document.querySelector("#activeArticles");
  clearChildren(list);

  if (!section.articles.length) {
    const item = document.createElement("li");
    item.className = "empty";
    item.textContent = section.empty_message || "수집된 데이터가 없습니다.";
    list.appendChild(item);
    return;
  }

  section.articles.forEach((article, index) => {
    const item = document.createElement("li");
    const number = document.createElement("span");
    const link = document.createElement("a");
    const description = document.createElement("p");
    const original = document.createElement("p");
    const reason = document.createElement("p");
    const meta = document.createElement("span");

    number.className = "story-number";
    number.textContent = String(index + 1).padStart(2, "0");
    link.href = article.url;
    link.target = "_blank";
    link.rel = "noreferrer";
    link.textContent = article.title;
    description.textContent = article.description || "";
    original.className = "original-title";
    original.textContent =
      article.title_original && article.title_original !== article.title
        ? `원문 헤드라인: ${article.title_original}`
        : "";
    reason.className = "classification-reason";
    reason.textContent = article.classification_reason || "";
    meta.className = "source-meta";
    meta.textContent = `${article.source || "출처 미상"} · ${formatDateTime(article.published_at)}`;

    item.append(number, link, renderTopicChips(article), original, description, reason, meta);
    list.appendChild(item);
  });
}

function setActiveTab(sectionId) {
  document.querySelectorAll(".tab-button").forEach((button) => {
    button.classList.toggle("active", button.dataset.section === sectionId);
  });
}

function renderSection(briefing, sectionId) {
  const section = briefing.sections?.[sectionId] || briefing[sectionId];
  if (!section) return;

  document.querySelector("#activeSectionKicker").textContent = `Section ${SECTION_INDEX[sectionId] || "--"}`;
  document.querySelector("#activeSectionTitle").textContent = section.title;
  document.querySelector("#activeArticleCount").textContent = `${section.article_count || 0} articles`;
  document.querySelector("#activeSectionSummary").textContent = section.summary || "";
  renderPrices(section.prices || []);
  renderArticles(section);
  setActiveTab(sectionId);
}

function renderSnapshot(briefing) {
  const sections = briefing.sections || briefing;
  document.querySelector("#domesticCount").textContent = sections.domestic?.article_count ?? 0;
  document.querySelector("#usCount").textContent = sections.us?.article_count ?? 0;
  document.querySelector("#macroCount").textContent = sections.macro?.article_count ?? 0;
}

async function loadBriefing() {
  if (window.DAILY_MARKET_BRIEFING) {
    return window.DAILY_MARKET_BRIEFING;
  }

  const response = await fetch("./daily_market_briefing.json");
  if (!response.ok) {
    throw new Error("Briefing JSON not found");
  }
  return response.json();
}

loadBriefing()
  .then((briefing) => {
    document.querySelector("#headline").textContent = briefing.headline;
    document.querySelector("#generatedAt").textContent =
      `생성 시각 ${formatDateTime(briefing.generated_at)}`;
    renderSnapshot(briefing);
    renderSection(briefing, "domestic");

    document.querySelectorAll(".tab-button").forEach((button) => {
      button.addEventListener("click", () => {
        renderSection(briefing, button.dataset.section);
      });
    });
  })
  .catch(() => {
    document.querySelector("#headline").textContent =
      "브리핑 데이터를 찾을 수 없습니다. 수집 파이프라인을 먼저 실행해 주세요.";
  });
