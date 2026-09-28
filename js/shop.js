const state = { products: [], cart: {}, filter: "全部" };

const $ = (id) => document.getElementById(id);

function imgSrc(p) {
  const img = p.image || "";
  if (img.startsWith("uploads/")) return "/" + img;
  return "/images/" + img;
}

function money(n) {
  return "NT$ " + Number(n).toLocaleString("zh-TW");
}

function loadCart() {
  try { state.cart = JSON.parse(localStorage.getItem("sc_cart") || "{}"); }
  catch { state.cart = {}; }
}
function saveCart() {
  localStorage.setItem("sc_cart", JSON.stringify(state.cart));
  renderCart();
}

function add(id) {
  state.cart[id] = (state.cart[id] || 0) + 1;
  saveCart();
  openCart();
}
function setQty(id, q) {
  if (q <= 0) delete state.cart[id];
  else state.cart[id] = q;
  saveCart();
}

function openCart() { $("drawer").classList.add("show"); }
function closeCart() { $("drawer").classList.remove("show"); }

function renderCart() {
  const ids = Object.keys(state.cart);
  const count = ids.reduce((s, id) => s + state.cart[id], 0);
  $("cartCount").textContent = count;
  const list = $("cartList");
  if (!ids.length) {
    list.innerHTML = '<p class="hint">衣櫥還是空的。</p>';
    $("sum").textContent = money(0);
    return;
  }
  let total = 0;
  list.innerHTML = ids.map((id) => {
    const p = state.products.find((x) => String(x.id) === String(id));
    if (!p) return "";
    const qty = state.cart[id];
    total += p.price * qty;
    return `<div class="cart-item">
      <img src="${imgSrc(p)}" alt="" />
      <div>
        <div class="nm">${p.name}</div>
        <div class="pr">${money(p.price)}</div>
        <div class="qty">
          <button data-q="${qty - 1}" data-id="${id}">−</button>
          <span>${qty}</span>
          <button data-q="${qty + 1}" data-id="${id}">＋</button>
        </div>
      </div>
      <div class="pr">${money(p.price * qty)}</div>
    </div>`;
  }).join("");
  list.querySelectorAll("button[data-id]").forEach((b) => {
    b.onclick = () => setQty(b.dataset.id, Number(b.dataset.q));
  });
  $("sum").textContent = money(total);
}

function renderFilters() {
  const cats = ["全部", ...new Set(state.products.map((p) => p.category).filter(Boolean))];
  $("filters").innerHTML = cats.map((c) =>
    `<button class="chip ${c === state.filter ? "on" : ""}" data-c="${c}">${c}</button>`
  ).join("");
  $("filters").querySelectorAll("button").forEach((b) => {
    b.onclick = () => { state.filter = b.dataset.c; render(); };
  });
}

function render() {
  renderFilters();
  const list = state.filter === "全部"
    ? state.products
    : state.products.filter((p) => p.category === state.filter);
  $("countLabel").textContent = list.length + " ITEMS";
  $("grid").innerHTML = list.map((p) => `
    <article class="card">
      <div class="pic" style="background-image:url('${imgSrc(p)}')"></div>
      <div class="meta">
        <div class="cat">${p.category || "NEW"} · ${p.name_kr || ""}</div>
        <h3>${p.name}</h3>
        <div class="row">
          <span class="price">${money(p.price)}</span>
          <button class="add" data-id="${p.id}" aria-label="加入">＋</button>
        </div>
      </div>
    </article>`).join("");
  $("grid").querySelectorAll(".add").forEach((b) => {
    b.onclick = (e) => { e.stopPropagation(); add(b.dataset.id); };
  });
  $("grid").querySelectorAll(".card").forEach((card, i) => {
    const p = list[i];
    card.onclick = () => add(p.id);
  });
}

async function checkout() {
  const name = $("name").value.trim();
  const phone = $("phone").value.trim();
  const store = $("store").value.trim();
  const items = Object.keys(state.cart).map((id) => ({ id: Number(id), qty: state.cart[id] }));
  $("pay").disabled = true;
  try {
    const res = await fetch("/api/checkout", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, phone, store, items }),
    });
    const data = await res.json();
    if (!data.ok) {
      $("okbox").className = "okbox show";
      $("okbox").style.background = "#fdecec";
      $("okbox").style.color = "#8a2a2a";
      $("okbox").textContent = data.error || "送出失敗";
      return;
    }
    state.cart = {};
    saveCart();
    $("okbox").className = "okbox show";
    $("okbox").style.background = "";
    $("okbox").style.color = "";
    $("okbox").textContent = `訂單 #${data.order_id} 已成立，合計 ${money(data.total)}。請至指定 7-11 門市取貨。`;
    $("name").value = $("phone").value = $("store").value = "";
  } catch (e) {
    alert("網路異常，請稍後再試");
  } finally {
    $("pay").disabled = false;
  }
}

$("openCart").onclick = openCart;
$("mask").onclick = closeCart;
$("pay").onclick = checkout;

loadCart();
fetch("/api/products")
  .then((r) => r.json())
  .then((d) => {
    state.products = d.products || [];
    render();
    renderCart();
  })
  .catch(() => {
    $("grid").innerHTML = "<p class='hint'>無法載入商品，請確認伺服器已啟動。</p>";
  });
