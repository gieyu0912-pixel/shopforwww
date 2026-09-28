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

function brandOf(p) {
  const b = String(p.brand || "").toUpperCase();
  if (b === "A" || b === "B" || b === "C") return b;
  return "精選";
}

function cardHtml(p) {
  const zone = brandOf(p);
  return `<article class="card">
      <div class="pic" style="background-image:url('${imgSrc(p)}')"></div>
      <div class="meta">
        <div class="cat">品牌 ${zone} · ${p.category || ""}</div>
        <h3>${p.name}</h3>
        <div class="row">
          <span class="price">${money(p.price)}</span>
          <button class="add" data-id="${p.id}" aria-label="加入">＋</button>
        </div>
      </div>
    </article>`;
}

function fillGrid(el, list) {
  if (!el) return;
  if (!list.length) {
    el.innerHTML = '<p class="hint">此區尚無商品</p>';
    return;
  }
  el.innerHTML = list.map(cardHtml).join("");
  el.querySelectorAll(".add").forEach((b) => {
    b.onclick = (e) => { e.stopPropagation(); add(b.dataset.id); };
  });
  el.querySelectorAll(".card").forEach((card, i) => {
    card.onclick = () => add(list[i].id);
  });
}

function renderFilters() {
  const opts = ["全部", "品牌 A", "品牌 B", "品牌 C", "精選"];
  $("filters").innerHTML = opts.map((c) =>
    `<button class="chip ${c === state.filter ? "on" : ""}" data-c="${c}">${c}</button>`
  ).join("");
  $("filters").querySelectorAll("button").forEach((b) => {
    b.onclick = () => { state.filter = b.dataset.c; render(); };
  });
}

function render() {
  renderFilters();
  const a = state.products.filter((p) => brandOf(p) === "A");
  const b = state.products.filter((p) => brandOf(p) === "B");
  const c = state.products.filter((p) => brandOf(p) === "C");
  const pick = state.products.filter((p) => brandOf(p) === "精選");
  $("countLabel").textContent = state.products.length + " ITEMS";
  const show = (id, on) => { const n = $(id); if (n) n.style.display = on ? "" : "none"; };
  if (state.filter === "品牌 A") {
    show("zone-A", true); show("zone-B", false); show("zone-C", false); show("zone-pick", false);
  } else if (state.filter === "品牌 B") {
    show("zone-A", false); show("zone-B", true); show("zone-C", false); show("zone-pick", false);
  } else if (state.filter === "品牌 C") {
    show("zone-A", false); show("zone-B", false); show("zone-C", true); show("zone-pick", false);
  } else if (state.filter === "精選") {
    show("zone-A", false); show("zone-B", false); show("zone-C", false); show("zone-pick", true);
  } else {
    show("zone-A", true); show("zone-B", true); show("zone-C", true); show("zone-pick", true);
  }
  fillGrid($("grid-A"), a);
  fillGrid($("grid-B"), b);
  fillGrid($("grid-C"), c);
  fillGrid($("grid-pick"), pick);
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
