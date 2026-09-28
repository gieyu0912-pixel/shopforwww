const $ = (id) => document.getElementById(id);
let picked = [];

function money(n) {
  return "NT$ " + Number(n).toLocaleString("zh-TW");
}

async function api(url, opts) {
  const res = await fetch(url, Object.assign({ credentials: "same-origin" }, opts || {}));
  const data = await res.json().catch(() => ({ ok: false }));
  return { status: res.status, data };
}

function showApp() {
  $("loginView").style.display = "none";
  $("appView").style.display = "grid";
}

function showLogin() {
  $("loginView").style.display = "grid";
  $("appView").style.display = "none";
}

async function boot() {
  const { status, data } = await api("/api/admin/me");
  if (status === 200 && data.ok) {
    showApp();
    applyPwAlert(data);
    refresh();
  } else {
    showLogin();
  }
}

function applyPwAlert(data) {
  const el = $("pwAlert");
  if (data.password_due) {
    el.style.display = "block";
    el.textContent = "密碼已超過 3 個月未更換，請立即到「更改密碼」更新，以保障後台安全。";
  } else {
    el.style.display = "block";
    el.style.background = "#eef6f1";
    el.style.borderColor = "#b7d7c4";
    el.style.color = "#2f6b4f";
    el.textContent = `密碼狀態正常。距離下次提醒還有 ${data.days_remaining} 天（上次更換：${data.password_changed || "—"}）。`;
  }
}

async function refresh() {
  const s = await api("/api/admin/stats");
  if (s.data.ok) {
    $("kPending").textContent = s.data.pending;
    $("kShipped").textContent = s.data.shipped;
    $("kProducts").textContent = s.data.products;
    $("kRev").textContent = money(s.data.revenue);
  }
  const o = await api("/api/admin/orders");
  if (!o.data.ok) return;
  const body = $("orderBody");
  if (!o.data.orders.length) {
    body.innerHTML = '<tr><td colspan="9">尚無訂單。前台結帳後會出現在這裡。</td></tr>';
    return;
  }
  body.innerHTML = o.data.orders.map((ord) => {
    const items = (ord.items || []).map((it) => `${it.name} ×${it.qty}`).join("<br/>");
    const btn = ord.status === "pending"
      ? `<button class="ship" data-id="${ord.id}">出貨</button>`
      : "—";
    return `<tr>
      <td>${ord.id}</td>
      <td>${(ord.created_at || "").replace("T", " ")}</td>
      <td>${ord.customer_name}</td>
      <td>${ord.phone}</td>
      <td>${ord.store_711}</td>
      <td>${items}</td>
      <td>${money(ord.total)}</td>
      <td><span class="badge ${ord.status}">${ord.status === "pending" ? "待出貨" : "已出貨"}</span></td>
      <td>${btn}</td>
    </tr>`;
  }).join("");
  body.querySelectorAll(".ship").forEach((b) => {
    b.onclick = async () => {
      b.disabled = true;
      await api("/api/admin/ship/" + b.dataset.id, { method: "POST" });
      refresh();
    };
  });
}

$("loginBtn").onclick = async () => {
  $("loginErr").textContent = "";
  const { data } = await api("/api/admin/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username: $("user").value, password: $("pass").value }),
  });
  if (!data.ok) {
    $("loginErr").textContent = data.error || "登入失敗";
    return;
  }
  showApp();
  applyPwAlert(data);
  refresh();
};

$("logout").onclick = async () => {
  await api("/api/admin/logout", { method: "POST" });
  showLogin();
};

document.querySelectorAll(".side button[data-tab]").forEach((b) => {
  b.onclick = () => {
    document.querySelectorAll(".side button[data-tab]").forEach((x) => x.classList.remove("on"));
    b.classList.add("on");
    document.querySelectorAll(".section").forEach((s) => s.classList.remove("on"));
    $("tab-" + b.dataset.tab).classList.add("on");
  };
});

function preview(files) {
  picked = Array.from(files).slice(0, 30);
  $("fileHint").textContent = `已選 ${picked.length} 張（上限 30）`;
  $("thumbs").innerHTML = "";
  picked.forEach((f) => {
    const img = document.createElement("img");
    img.src = URL.createObjectURL(f);
    $("thumbs").appendChild(img);
  });
}

$("files").onchange = (e) => preview(e.target.files);
["dragenter", "dragover"].forEach((ev) => {
  $("drop").addEventListener(ev, (e) => { e.preventDefault(); $("drop").classList.add("drag"); });
});
["dragleave", "drop"].forEach((ev) => {
  $("drop").addEventListener(ev, (e) => { e.preventDefault(); $("drop").classList.remove("drag"); });
});
$("drop").addEventListener("drop", (e) => preview(e.dataTransfer.files));

$("uploadBtn").onclick = async () => {
  if (!picked.length) {
    $("uploadMsg").textContent = "請先選擇圖片";
    return;
  }
  const fd = new FormData();
  picked.forEach((f) => fd.append("images", f));
  $("uploadBtn").disabled = true;
  $("uploadMsg").textContent = "上傳中…";
  try {
    const res = await fetch("/api/admin/upload", { method: "POST", body: fd, credentials: "same-origin" });
    const data = await res.json();
    if (!data.ok) {
      $("uploadMsg").textContent = data.error || "上傳失敗";
    } else {
      $("uploadMsg").textContent = `已新增 ${data.added} 件商品到前台。`;
      picked = [];
      $("thumbs").innerHTML = "";
      $("files").value = "";
      $("fileHint").textContent = "尚未選擇";
      refresh();
    }
  } catch {
    $("uploadMsg").textContent = "上傳發生錯誤";
  } finally {
    $("uploadBtn").disabled = false;
  }
};

$("pwBtn").onclick = async () => {
  $("pwErr").textContent = "";
  if ($("newPw").value !== $("newPw2").value) {
    $("pwErr").textContent = "兩次新密碼不一致";
    return;
  }
  const { data } = await api("/api/admin/password", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ old: $("oldPw").value, new: $("newPw").value }),
  });
  if (!data.ok) {
    $("pwErr").textContent = data.error || "更新失敗";
    return;
  }
  $("pwErr").style.color = "#2f6b4f";
  $("pwErr").textContent = "密碼已更新，90 天後會再次提醒。";
  $("oldPw").value = $("newPw").value = $("newPw2").value = "";
  const me = await api("/api/admin/me");
  if (me.data.ok) applyPwAlert(me.data);
};

boot();
