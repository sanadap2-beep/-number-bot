const tg = window.Telegram?.WebApp;
const state = { categories: [], products: [], filter: "all", query: "" };

if (tg) { tg.ready(); tg.expand(); }

const message = document.getElementById("message");
function showMessage(text, error = false) {
  message.textContent = text;
  message.classList.toggle("hidden", !text);
  message.style.color = error ? "var(--danger)" : "var(--brand)";
}

function authHeaders() {
  const headers = { "Content-Type": "application/json" };
  if (tg?.initData) headers.Authorization = `tma ${tg.initData}`;
  return headers;
}

async function api(path, options = {}) {
  const response = await fetch(`/api/v1${path}`, {
    ...options,
    headers: { ...authHeaders(), ...(options.headers || {}) },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || "تعذر الاتصال بالخادم");
  }
  return response.json();
}

function flattenCatalog(data) {
  const products = [];
  for (const category of data.categories) {
    for (const sub of category.sub_categories) {
      for (const product of sub.products) {
        products.push({ ...product, categoryId: category.id, categoryName: category.name, subName: sub.name });
      }
    }
  }
  return products;
}

function renderChips() {
  const chips = document.getElementById("chips");
  chips.innerHTML = `<button class="chip ${state.filter === "all" ? "active" : ""}" data-filter="all">الكل</button>`;
  for (const category of state.categories) {
    const button = document.createElement("button");
    button.className = `chip ${state.filter === String(category.id) ? "active" : ""}`;
    button.dataset.filter = category.id;
    button.textContent = `${category.emoji} ${category.name}`;
    chips.appendChild(button);
  }
  chips.querySelectorAll(".chip").forEach((button) => {
    button.onclick = () => { state.filter = String(button.dataset.filter); renderChips(); renderProducts(); };
  });
}

function renderProducts() {
  const root = document.getElementById("catalog");
  const empty = document.getElementById("empty");
  root.innerHTML = "";
  const query = state.query.toLocaleLowerCase();
  const products = state.products.filter((product) => {
    const matchesCategory = state.filter === "all" || String(product.categoryId) === state.filter;
    const matchesQuery = !query || `${product.name} ${product.description || ""} ${product.subName}`.toLocaleLowerCase().includes(query);
    return matchesCategory && matchesQuery;
  });
  empty.classList.toggle("hidden", products.length !== 0);
  let currentCategory = null;
  for (const product of products) {
    if (currentCategory !== product.categoryId) {
      currentCategory = product.categoryId;
      const title = document.createElement("h2");
      title.className = "category-title";
      title.textContent = product.categoryName;
      root.appendChild(title);
    }
    const card = document.createElement("article");
    card.className = "product";
    const promo = product.promotion;
    const price = promo ? promo.discounted_price : product.price_usd;
    card.innerHTML = `
      ${promo ? `<span class="badge">🔥 ${escapeHtml(promo.name)}</span>` : ""}
      <h3>${escapeHtml(product.name)}</h3>
      <p>${escapeHtml(product.description || "خدمة رقمية جاهزة للطلب")}</p>
      <div class="meta"><div><span class="price">${price}$</span>${promo ? `<span class="old">${product.price_usd}$</span>` : ""}</div><span class="rating">${product.rating ? `★ ${product.rating} (${product.reviews_count})` : "جديد"}</span></div>
      <button class="buy">شراء عبر Telegram</button>
      <button class="watch">🔔 مراقبة السعر والمخزون</button>
    `;
    card.querySelector(".buy").onclick = () => selectProduct(product.id);
    card.querySelector(".watch").onclick = () => watchProduct(product.id);
    root.appendChild(card);
  }
}

function escapeHtml(value) {
  return String(value).replace(/[&<>'"]/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" }[char]));
}

function selectProduct(productId) {
  if (!tg?.sendData) { showMessage("افتح المتجر من داخل Telegram لاختيار المنتج.", true); return; }
  tg.sendData(JSON.stringify({ action: "select_product", product_id: productId }));
  tg.close();
}

async function watchProduct(productId) {
  if (!tg?.initData) { showMessage("سجل دخولك من داخل Telegram لتفعيل التنبيه.", true); return; }
  try { await api("/watches", { method: "POST", body: JSON.stringify({ product_id: productId }) }); showMessage("🔔 تم تفعيل التنبيه لهذا المنتج."); }
  catch (error) { showMessage(error.message, true); }
}

async function load() {
  try {
    const catalog = await api("/catalog");
    state.categories = catalog.categories;
    state.products = flattenCatalog(catalog);
    renderChips(); renderProducts();
    if (tg?.initData) {
      const me = await api("/me");
      document.getElementById("balance").textContent = `${me.balance_usd}$`;
      document.getElementById("points").textContent = me.loyalty_points;
      document.getElementById("tier").textContent = me.loyalty_tier;
    } else showMessage("لإتمام الشراء، افتح المتجر من داخل Telegram.");
  } catch (error) { showMessage(error.message, true); }
}

document.getElementById("search").addEventListener("input", (event) => { state.query = event.target.value; renderProducts(); });
load();
