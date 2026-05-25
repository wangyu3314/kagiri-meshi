/**
 * load_menus.js
 * limited_menus.json を読み込み、カード表示・フィルターを動的に生成する。
 */

const CATEGORY_CONFIG = {
  sushi:       { label: "回転寿司",      emoji: "🍣" },
  burger:      { label: "バーガー",      emoji: "🍔" },
  cafe:        { label: "カフェ",        emoji: "☕" },
  men:         { label: "うどん・そば",  emoji: "🍜" },
  don:         { label: "丼もの",        emoji: "🍚" },
  family:      { label: "ファミレス",    emoji: "🍽️" },
  ramen:       { label: "ラーメン",      emoji: "🍥" },
  sweets:      { label: "スイーツ",      emoji: "🍰" },
};
let allItems    = [];
let currentCat  = "all";
let currentShop = "all";

async function loadMenus() {
  try {
    const res = await fetch("limited_menus.json");
    if (!res.ok) throw new Error("not found");
    allItems = await res.json();
    buildFilters();
    updateStats();
    renderCards();
  } catch (e) {
    document.getElementById("grid").innerHTML =
      `<div class="empty"><span class="empty-icon">🍱</span>データを読み込めませんでした。<br>limited_menus.json が同じフォルダにあるか確認してください。</div>`;
  }
}

function updateStats() {
  document.getElementById("stat-total").textContent = allItems.length;
  document.getElementById("stat-shops").textContent = new Set(allItems.map(i => i.shop)).size;
}

function buildFilters() {
  const cats = [...new Set(allItems.map(i => i.category).filter(Boolean))];
  const catWrap = document.getElementById("filter-category");
  cats.forEach(cat => {
    const cfg = CATEGORY_CONFIG[cat] || { label: cat, emoji: "🍴" };
    const btn = document.createElement("button");
    btn.className = "filter-btn";
    btn.dataset.category = cat;
    btn.textContent = `${cfg.emoji} ${cfg.label}`;
    catWrap.appendChild(btn);
  });

  const shops = [...new Set(allItems.map(i => i.shop))].sort();
  const shopWrap = document.getElementById("filter-shop");
  shops.forEach(shop => {
    const btn = document.createElement("button");
    btn.className = "filter-btn";
    btn.dataset.shop = shop;
    btn.textContent = shop;
    shopWrap.appendChild(btn);
  });

  document.querySelectorAll("#filter-category .filter-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll("#filter-category .filter-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      currentCat = btn.dataset.category;
      currentShop = "all";
      document.querySelectorAll("#filter-shop .filter-btn").forEach(b => b.classList.remove("active"));
      document.querySelector("#filter-shop .filter-btn[data-shop='all']").classList.add("active");
      updateShopFilter();
      renderCards();
    });
  });

  document.querySelectorAll("#filter-shop .filter-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll("#filter-shop .filter-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      currentShop = btn.dataset.shop;
      renderCards();
    });
  });
}

function updateShopFilter() {
  const filtered = currentCat === "all" ? allItems : allItems.filter(i => i.category === currentCat);
  const activeShops = new Set(filtered.map(i => i.shop));
  document.querySelectorAll("#filter-shop .filter-btn[data-shop]").forEach(btn => {
    if (btn.dataset.shop === "all") return;
    btn.style.display = activeShops.has(btn.dataset.shop) ? "" : "none";
  });
}

function renderCards() {
  let items = allItems;
  if (currentCat  !== "all") items = items.filter(i => i.category === currentCat);
  if (currentShop !== "all") items = items.filter(i => i.shop === currentShop);

    // 記事投稿日順（新しいものを上に）
  items = [...items].sort((a, b) => {
    const dateA = new Date(a.published || a.fetched_at);
    const dateB = new Date(b.published || b.fetched_at);
    return dateB - dateA;
  });
  
  const grid = document.getElementById("grid");

  if (items.length === 0) {
    grid.innerHTML = `<div class="empty"><span class="empty-icon">🔍</span>該当する商品がありません</div>`;
    return;
  }

  grid.innerHTML = items.map((item, idx) => {
    const cfg      = CATEGORY_CONFIG[item.category] || { emoji: "🍴", label: item.category || "" };
    const catLabel = cfg.label;
    const delay    = `animation-delay:${idx * 0.04}s`;

    return `
      <a class="card" href="${item.link || '#'}" target="_blank" rel="noopener" style="${delay}">
        <div class="card-emoji">${cfg.emoji}</div>
        <div class="card-body">
          <div style="display:flex;align-items:center;gap:.35rem;flex-wrap:wrap">
            <span class="card-shop">${item.shop}</span>
            ${catLabel ? `<span class="card-cat">${catLabel}</span>` : ""}
          </div>
          <div class="card-name">${item.name}</div>
        </div>
      </a>`;
  }).join("");
}

loadMenus();
