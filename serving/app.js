const SECTION_ORDER = ["domestic", "us", "macro", "sector", "weekly", "schedule", "feargreed"];
const SECTION_INDEX = {
  domestic: "01",
  us: "02",
  macro: "03",
  sector: "04",
  weekly: "05",
  schedule: "06",
  feargreed: "07",
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
    macro: "금리·환율·유가·원자재·가상자산",
    sector: "섹터",
    weekly: "주간",
    schedule: "일정",
    feargreed: "공포탐욕",
    uncategorized: "미분류",
  };
  return labels[topic] || topic;
}

function renderTopicChips(article, options = {}) {
  const row = document.createElement("div");
  row.className = "topic-row";

  if (!options.hidePrimary) {
    const primary = document.createElement("span");
    primary.className = "topic-chip primary";
    primary.textContent = `주제: ${topicLabel(article.primary_topic)}`;
    row.appendChild(primary);
  }

  (article.secondary_topics || []).slice(0, 3).forEach((topic) => {
    const chip = document.createElement("span");
    chip.className = "topic-chip";
    chip.textContent = topicLabel(topic);
    row.appendChild(chip);
  });

  return row;
}

function renderPrices(prices, sectionId) {
  const block = document.querySelector("#priceBlock");
  const heading = document.querySelector("#priceHeading");
  const list = document.querySelector("#activePrices");
  clearChildren(list);

  if (!prices.length) {
    block.hidden = true;
    return;
  }

  block.hidden = false;
  heading.textContent =
    sectionId === "macro" ? "금리·환율·유가·원자재·가상자산 지표" : "주요 지수";

  prices.forEach((text) => {
    const item = document.createElement("li");
    item.textContent = text;
    list.appendChild(item);
  });
}

function renderArticles(section, sectionId) {
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
    const meta = document.createElement("span");

    number.className = "story-number";
    number.textContent = String(index + 1).padStart(2, "0");
    link.href = article.url;
    link.target = "_blank";
    link.rel = "noreferrer";
    link.textContent = article.title;
    meta.className = "source-meta";
    meta.textContent = `${article.source || "출처 미상"} · ${formatDateTime(article.published_at)}`;

    item.append(number, link, meta);
    list.appendChild(item);
  });
}

function renderWeeklyBlocks(section) {
  const list = document.querySelector("#activeArticles");
  clearChildren(list);

  if (!section.weekly_blocks?.length) {
    const item = document.createElement("li");
    item.className = "empty";
    item.textContent = section.empty_message || "주간 브리핑 데이터가 없습니다.";
    list.appendChild(item);
    return;
  }

  section.weekly_blocks.forEach((block, index) => {
    const item = document.createElement("li");
    const number = document.createElement("span");
    const title = document.createElement("strong");
    const nested = document.createElement("ul");
    const isStockFlowBlock = (block.items || []).some((entry) => entry?.type === "stock_flow");

    item.className = "weekly-card";
    number.className = "story-number";
    number.textContent = String(index + 1).padStart(2, "0");
    title.className = "weekly-card-title";
    title.textContent = block.title;
    nested.className = "weekly-list";

    if (isStockFlowBlock) {
      item.append(number, title, renderStockFlowTable(block.items || []));
    } else {
      (block.items || []).forEach((entry) => {
        const nestedItem = document.createElement("li");
        if (entry && typeof entry === "object" && entry.url) {
          const link = document.createElement("a");
          link.href = entry.url;
          link.target = "_blank";
          link.rel = "noreferrer";
          link.textContent = entry.text || entry.url;
          nestedItem.appendChild(link);
        } else {
          nestedItem.textContent = typeof entry === "object" ? entry.text || "" : entry;
        }
        nested.appendChild(nestedItem);
      });
      item.append(number, title, nested);
    }
    list.appendChild(item);
  });
}

function renderStockFlowTable(items) {
  const wrap = document.createElement("div");
  const table = document.createElement("table");
  const thead = document.createElement("thead");
  const tbody = document.createElement("tbody");
  const headerRow = document.createElement("tr");

  wrap.className = "stock-flow-table-wrap";
  table.className = "stock-flow-table";
  ["종목", "시장", "5거래일", "거래량", "평균 거래대금"].forEach((label) => {
    const th = document.createElement("th");
    th.textContent = label;
    headerRow.appendChild(th);
  });
  thead.appendChild(headerRow);

  items.forEach((entry) => {
    const row = document.createElement("tr");
    const name = document.createElement("td");
    const market = document.createElement("td");
    const change = document.createElement("td");
    const volume = document.createElement("td");
    const turnover = document.createElement("td");
    const link = document.createElement("a");
    const changeValue = Number(entry.weekly_change_pct || 0);

    link.href = entry.url || "#";
    link.target = "_blank";
    link.rel = "noreferrer";
    link.textContent = entry.name || "종목명 없음";
    name.appendChild(link);
    market.textContent = entry.market || "-";
    change.className = changeValue > 0 ? "up" : changeValue < 0 ? "down" : "flat";
    change.textContent = `${Math.abs(changeValue).toFixed(2)}% ${entry.direction || "보합"}`;
    volume.textContent = `${Number(entry.volume_ratio || 0).toFixed(2)}배`;
    turnover.textContent = entry.avg_turnover_label || "-";

    row.append(name, market, change, volume, turnover);
    tbody.appendChild(row);
  });

  table.append(thead, tbody);
  wrap.appendChild(table);
  return wrap;
}

function formatDateLabel(value) {
  if (!value) return "";
  const date = new Date(`${value}T00:00:00+09:00`);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("ko-KR", {
    month: "long",
    day: "numeric",
    weekday: "short",
  }).format(date);
}

function eventMatchesDate(event, date) {
  const start = event.start || "";
  const end = event.end || start;
  return start <= date && date <= end;
}

function categoryClass(category) {
  const key = {
    "금리": "rate",
    "물가": "inflation",
    "성장": "growth",
    "경기": "activity",
    "중앙은행": "central-bank",
  }[category] || "default";
  return `category-${key}`;
}

function eventCard(event) {
  const item = document.createElement("li");
  const title = document.createElement("a");
  const meta = document.createElement("span");
  const badge = document.createElement("span");
  const detail = document.createElement("p");

  item.className = "schedule-event";
  item.classList.add(categoryClass(event.category));
  title.href = event.source_url || "#";
  title.target = "_blank";
  title.rel = "noreferrer";
  title.textContent = event.title;
  badge.className = "schedule-badge";
  badge.textContent = event.category || "일정";
  meta.className = "schedule-meta";
  meta.textContent = `${event.date_label} · ${event.region} · ${event.category}`;
  detail.textContent = event.detail || "";

  item.append(badge, title, meta, detail);
  return item;
}

function renderScheduleEventList(events, emptyText) {
  const list = document.createElement("ul");
  list.className = "schedule-event-list";

  if (!events.length) {
    const empty = document.createElement("li");
    empty.className = "empty";
    empty.textContent = emptyText;
    list.appendChild(empty);
    return list;
  }

  events.forEach((event) => {
    list.appendChild(eventCard(event));
  });
  return list;
}

function earningsCard(event) {
  const item = document.createElement("li");
  const link = document.createElement("a");
  const meta = document.createElement("span");

  item.className = "earnings-item";
  link.href = event.source_url || "#";
  link.target = "_blank";
  link.rel = "noreferrer";
  link.textContent = `${event.ticker} · ${event.company}`;
  meta.textContent = `${formatDateLabel(event.date)} · ${event.timing}`;

  item.append(link, meta);
  return item;
}

function renderEarningsList(events, emptyText) {
  const list = document.createElement("ul");
  list.className = "earnings-list";

  if (!events.length) {
    const empty = document.createElement("li");
    empty.className = "empty";
    empty.textContent = emptyText;
    list.appendChild(empty);
    return list;
  }

  events.forEach((event) => {
    list.appendChild(earningsCard(event));
  });
  return list;
}

function renderWeeklyEarnings(section) {
  const block = document.createElement("section");
  const heading = document.createElement("h3");
  const grid = document.createElement("div");
  const domestic = document.createElement("article");
  const us = document.createElement("article");
  const domesticTitle = document.createElement("strong");
  const usTitle = document.createElement("strong");

  block.className = "earnings-week";
  heading.className = "schedule-subtitle";
  heading.textContent = "이번 주 실적발표";
  grid.className = "earnings-grid";
  domesticTitle.textContent = "국내 주요 기업";
  usTitle.textContent = "미국 주요 기업";

  domestic.append(
    domesticTitle,
    renderEarningsList(section.week_earnings?.domestic || [], "이번 주 확인된 주요 국내 기업 실적발표 일정이 없습니다.")
  );
  us.append(
    usTitle,
    renderEarningsList(section.week_earnings?.us || [], "이번 주 확인된 주요 미국 기업 실적발표 일정이 없습니다.")
  );
  grid.append(domestic, us);
  block.append(heading, grid);
  return block;
}

function renderSelectedSchedule(container, section, selectedDate) {
  const panel = container.querySelector("[data-schedule-detail]");
  clearChildren(panel);

  const title = document.createElement("h3");
  const events = (section.events || []).filter((event) => eventMatchesDate(event, selectedDate));

  title.className = "schedule-subtitle";
  title.textContent = `${formatDateLabel(selectedDate)} 상세 일정`;
  panel.appendChild(title);
  panel.appendChild(renderScheduleEventList(events, "선택한 날짜에 등록된 주요 일정이 없습니다."));
}

function renderCalendarGrid(calendarGrid, section, month, wrapper) {
  clearChildren(calendarGrid);

  ["일", "월", "화", "수", "목", "금", "토"].forEach((label) => {
    const cell = document.createElement("span");
    cell.className = "calendar-weekday";
    cell.textContent = label;
    calendarGrid.appendChild(cell);
  });

  (month?.days || []).forEach((day) => {
    const button = document.createElement("button");
    const dayEvents = (section.events || []).filter((event) => eventMatchesDate(event, day.date));
    button.className = "calendar-day";
    button.type = "button";
    button.dataset.date = day.date;
    button.classList.toggle("muted", !day.in_month);
    button.classList.toggle("today", day.is_today);
    button.classList.toggle("has-event", day.event_count > 0);
    button.classList.toggle("high-impact", day.has_high_impact);
    if (dayEvents[0]) {
      button.classList.add(categoryClass(dayEvents[0].category));
    }
    button.innerHTML = `<span>${day.day}</span>${day.event_count ? `<em>${day.event_count}</em>` : ""}`;
    button.addEventListener("click", () => {
      calendarGrid.querySelectorAll(".calendar-day").forEach((cell) => cell.classList.remove("selected"));
      button.classList.add("selected");
      renderSelectedSchedule(wrapper, section, day.date);
    });
    calendarGrid.appendChild(button);
  });
}

function renderSchedule(section) {
  const list = document.querySelector("#activeArticles");
  clearChildren(list);

  const wrapperItem = document.createElement("li");
  const wrapper = document.createElement("div");
  const calendarHead = document.createElement("div");
  const titleGroup = document.createElement("div");
  const monthTitle = document.createElement("strong");
  const weekTitle = document.createElement("span");
  const controls = document.createElement("div");
  const prevButton = document.createElement("button");
  const nextButton = document.createElement("button");
  const weekBlock = document.createElement("section");
  const weekHeading = document.createElement("h3");
  const calendar = document.createElement("section");
  const calendarTitle = document.createElement("h3");
  const calendarGrid = document.createElement("div");
  const detail = document.createElement("section");
  const months = section.calendar?.months?.length
    ? section.calendar.months
    : [{ month: section.calendar?.month, month_label: section.calendar?.month_label, days: section.calendar?.days || [] }];
  let activeMonthIndex = Math.max(0, months.findIndex((month) => month.month === section.calendar?.month));
  const firstEventDate = section.week_events?.[0]?.start || section.calendar?.week_start || section.calendar?.month;

  wrapperItem.className = "schedule-shell-item";
  wrapper.className = "schedule-shell";
  calendarHead.className = "schedule-calendar-head";
  titleGroup.className = "schedule-title-group";
  monthTitle.textContent = section.calendar?.month_label || "일정 달력";
  weekTitle.textContent = `이번 주 ${section.calendar?.week_label || ""}`;
  controls.className = "schedule-calendar-controls";
  prevButton.type = "button";
  prevButton.textContent = "이전";
  nextButton.type = "button";
  nextButton.textContent = "다음";

  weekBlock.className = "schedule-week";
  weekHeading.className = "schedule-subtitle";
  weekHeading.textContent = "이번 주 주요 일정";
  weekBlock.append(weekHeading, renderScheduleEventList(section.week_events || [], section.empty_message || "이번 주에 등록된 주요 일정이 없습니다."));

  calendar.className = "schedule-calendar";
  calendarTitle.className = "schedule-subtitle";
  calendarTitle.textContent = "월간 달력";
  calendarGrid.className = "calendar-grid";

  function setActiveMonth(index) {
    activeMonthIndex = Math.min(Math.max(index, 0), months.length - 1);
    const month = months[activeMonthIndex];
    monthTitle.textContent = month.month_label;
    prevButton.disabled = activeMonthIndex === 0;
    nextButton.disabled = activeMonthIndex === months.length - 1;
    renderCalendarGrid(calendarGrid, section, month, wrapper);

    const initialDate = activeMonthIndex === months.findIndex((row) => row.month === section.calendar?.month)
      ? firstEventDate
      : month.days?.find((day) => day.event_count > 0 && day.in_month)?.date;
    const initialButton = calendarGrid.querySelector(`[data-date="${initialDate}"]`) || calendarGrid.querySelector(".calendar-day.has-event");
    if (initialButton) {
      initialButton.classList.add("selected");
      renderSelectedSchedule(wrapper, section, initialButton.dataset.date);
    }
  }

  prevButton.addEventListener("click", () => setActiveMonth(activeMonthIndex - 1));
  nextButton.addEventListener("click", () => setActiveMonth(activeMonthIndex + 1));

  detail.className = "schedule-detail";
  detail.dataset.scheduleDetail = "true";
  titleGroup.append(monthTitle, weekTitle);
  controls.append(prevButton, nextButton);
  calendarHead.append(titleGroup, controls);
  calendar.append(calendarTitle, calendarGrid);
  wrapper.append(calendarHead, calendar, detail, weekBlock, renderWeeklyEarnings(section));
  wrapperItem.appendChild(wrapper);
  list.appendChild(wrapperItem);
  setActiveMonth(activeMonthIndex);
}

function formatIndicatorDate(value) {
  if (!value) return "업데이트 시간 없음";
  return formatDateTime(value);
}

function fearGreedTone(value) {
  if (value <= 24) return "fear-extreme";
  if (value <= 44) return "fear";
  if (value <= 55) return "neutral";
  if (value <= 75) return "greed";
  return "greed-extreme";
}

function renderFearGreed(section) {
  const list = document.querySelector("#activeArticles");
  clearChildren(list);

  const shellItem = document.createElement("li");
  const dashboard = document.createElement("div");
  const cards = document.createElement("div");

  shellItem.className = "feargreed-shell-item";
  dashboard.className = "feargreed-dashboard";
  cards.className = "feargreed-grid";

  if (!section.indicators?.length) {
    const empty = document.createElement("p");
    empty.className = "empty";
    empty.textContent = section.empty_message || "공포탐욕지수 데이터가 아직 없습니다.";
    dashboard.appendChild(empty);
  } else {
    section.indicators.forEach((indicator) => {
      const card = document.createElement("article");
      const head = document.createElement("div");
      const market = document.createElement("span");
      const title = document.createElement("strong");
      const gauge = document.createElement("div");
      const arc = document.createElement("div");
      const needle = document.createElement("i");
      const hub = document.createElement("span");
      const scale = document.createElement("div");
      const currentText = document.createElement("span");
      const value = document.createElement("b");
      const label = document.createElement("span");
      const change = document.createElement("p");
      const meta = document.createElement("p");

      const score = Number(indicator.value || 0);
      const boundedScore = Math.max(0, Math.min(100, score));
      const rotation = -90 + (boundedScore * 1.8);
      const direction = indicator.direction || "비교 불가";
      const changeValue = indicator.change === null || indicator.change === undefined
        ? ""
        : ` ${Math.abs(indicator.change)}p`;

      card.className = `feargreed-card ${fearGreedTone(score)}`;
      head.className = "feargreed-card-head";
      market.textContent = indicator.market || "시장";
      title.textContent = indicator.name;
      gauge.className = "feargreed-gauge";
      arc.className = "feargreed-arc";
      needle.className = "feargreed-needle";
      needle.style.transform = `translateX(-50%) rotate(${rotation}deg)`;
      hub.className = "feargreed-hub";
      scale.className = "feargreed-scale";
      scale.innerHTML = "<span>0</span><span>100</span>";
      currentText.className = "feargreed-current";
      currentText.textContent = "현재 지수";
      value.textContent = score;
      label.className = "feargreed-sentiment";
      label.textContent = indicator.label || "";
      change.className = "feargreed-change";
      change.textContent = `전일 대비 ${direction}${changeValue}`;
      meta.className = "feargreed-meta";
      meta.textContent = `${formatIndicatorDate(indicator.updated_at)} · ${indicator.method || indicator.source_name || ""}`;

      head.append(market, title);
      arc.append(needle, hub);
      gauge.append(arc, scale, currentText, value, label);
      card.append(head, gauge, change, meta);
      cards.appendChild(card);
    });
    dashboard.appendChild(cards);
  }

  shellItem.appendChild(dashboard);
  list.appendChild(shellItem);
}

function setActiveTab(sectionId) {
  document.querySelectorAll(".tab-button").forEach((button) => {
    button.classList.toggle("active", button.dataset.section === sectionId);
  });
}

function renderSection(briefing, sectionId) {
  const section = briefing.sections?.[sectionId] || briefing[sectionId];
  if (!section) return;
  const summary = document.querySelector("#activeSectionSummary");
  const showSummary = sectionId === "weekly";

  document.querySelector("#activeSectionKicker").textContent = `Section ${SECTION_INDEX[sectionId] || "--"}`;
  document.querySelector("#activeSectionTitle").textContent = section.title;
  document.querySelector("#activeArticleCount").textContent =
    sectionId === "weekly" || sectionId === "schedule" || sectionId === "feargreed"
      ? `${section.article_count || 0}건`
      : `${section.article_count || 0} articles`;
  summary.textContent = showSummary ? section.summary || "" : "";
  summary.hidden = !summary.textContent;
  renderPrices(section.prices || [], sectionId);
  if (sectionId === "weekly") {
    renderWeeklyBlocks(section);
  } else if (sectionId === "schedule") {
    renderSchedule(section);
  } else if (sectionId === "feargreed") {
    renderFearGreed(section);
  } else {
    renderArticles(section, sectionId);
  }
  setActiveTab(sectionId);
}

function renderSnapshot(briefing) {
  const sections = briefing.sections || briefing;
  document.querySelector("#domesticCount").textContent = sections.domestic?.article_count ?? 0;
  document.querySelector("#usCount").textContent = sections.us?.article_count ?? 0;
  document.querySelector("#macroCount").textContent = sections.macro?.article_count ?? 0;
}

function renderMarketIndicators(briefing) {
  const sections = briefing.sections || briefing;
  const prices = sections.macro?.prices || [];
  const block = document.querySelector("#marketIndicators");
  const list = document.querySelector("#indicatorList");
  clearChildren(list);

  if (!prices.length) {
    block.hidden = true;
    return;
  }

  block.hidden = false;
  prices.forEach((text) => {
    const item = document.createElement("li");
    item.textContent = text;
    list.appendChild(item);
  });
}

async function loadBriefing() {
  try {
    const response = await fetch(`./daily_market_briefing.json?v=${Date.now()}`, {
      cache: "no-store",
    });
    if (response.ok) {
      return response.json();
    }
  } catch {
    // file:// previews cannot always fetch JSON, so keep the generated script as a fallback.
  }

  if (window.DAILY_MARKET_BRIEFING) {
    return window.DAILY_MARKET_BRIEFING;
  }

  throw new Error("Briefing JSON not found");
}

loadBriefing()
  .then((briefing) => {
    document.querySelector("#generatedAt").textContent =
      `생성 시각 ${formatDateTime(briefing.generated_at)}`;
    renderSnapshot(briefing);
    renderMarketIndicators(briefing);
    renderSection(briefing, "domestic");

    document.querySelectorAll(".tab-button").forEach((button) => {
      button.addEventListener("click", () => {
        renderSection(briefing, button.dataset.section);
      });
    });
  })
  .catch(() => {
    document.querySelector("#generatedAt").textContent = "데이터를 불러오지 못했습니다";
  });
