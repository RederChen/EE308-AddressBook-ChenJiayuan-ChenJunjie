const state = { contacts: [], selectedId: null, favoriteOnly: false, query: "" };
const KINDS = {
  mobile: "手机", phone: "电话", email: "邮箱", wechat: "微信",
  qq: "QQ", weibo: "微博", address: "地址", other: "其他"
};
const AVATARS = [
  ["#e5ede2", "#42633c"], ["#f3e9dc", "#9a7148"], ["#e6ebf2", "#526c8c"],
  ["#f2e4e3", "#965e5a"], ["#e8e3f0", "#706087"], ["#e2eeee", "#447878"]
];
const $ = (selector) => document.querySelector(selector);

function escapeHTML(value) {
  return String(value ?? "").replace(/[&<>'"]/g, (char) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;"
  })[char]);
}

function icon(name) { return `<svg aria-hidden="true"><use href="#i-${name}"/></svg>`; }
function avatarStyle(name) {
  const code = [...String(name)].reduce((sum, char) => sum + char.codePointAt(0), 0);
  const [background, color] = AVATARS[code % AVATARS.length];
  return `--avatar:${background};--avatar-text:${color}`;
}
function primaryMethod(contact) {
  const preferred = contact.methods.find((method) => ["mobile", "phone", "email"].includes(method.kind));
  return (preferred || contact.methods[0])?.value || "暂未填写联系方式";
}
function toast(message, error = false) {
  const element = document.createElement("div");
  element.className = `toast${error ? " error" : ""}`;
  element.textContent = message;
  $("#toast-region").appendChild(element);
  setTimeout(() => element.remove(), error ? 6000 : 3200);
}
async function api(url, options = {}) {
  const response = await fetch(url, options);
  if (response.status === 204) return null;
  const data = await response.json().catch(() => ({ error: "服务器返回了无法识别的内容" }));
  if (!response.ok) {
    const error = new Error(data.error || "操作失败");
    error.details = data.details;
    throw error;
  }
  return data;
}

async function loadContacts({ keepSelection = true } = {}) {
  const params = new URLSearchParams();
  if (state.query) params.set("query", state.query);
  if (state.favoriteOnly) params.set("favorite", "1");
  try {
    const data = await api(`/api/contacts?${params}`);
    state.contacts = data.contacts;
    $("#total-count").textContent = data.stats.total;
    $("#favorite-count").textContent = data.stats.favorites;
    $("#result-summary").textContent = `显示 ${state.contacts.length} 位 · 共 ${data.stats.total} 位联系人`;
    if (!keepSelection || !state.contacts.some((contact) => contact.id === state.selectedId)) {
      state.selectedId = state.contacts[0]?.id ?? null;
    }
    renderContacts();
    renderDetail();
  } catch (error) {
    $("#contact-list").innerHTML = `<div class="empty-state"><h3>加载失败</h3><p>${escapeHTML(error.message)}</p></div>`;
    toast(error.message, true);
  }
}

function renderContacts() {
  const list = $("#contact-list");
  if (!state.contacts.length) {
    const filtered = state.query || state.favoriteOnly;
    list.innerHTML = `<div class="empty-state">${icon(state.favoriteOnly ? "star" : "contacts")}
      <h3>${filtered ? "没有找到匹配的联系人" : "通讯录还是空的"}</h3>
      <p>${filtered ? "试试其他关键词，或切换查看全部联系人" : "新建第一位联系人，或从 Excel 批量导入"}</p>
      ${filtered ? "" : '<button class="button button-primary" data-action="new">新建联系人</button>'}</div>`;
    return;
  }
  list.innerHTML = state.contacts.map((contact) => `
    <article class="contact-card${contact.id === state.selectedId ? " selected" : ""}" data-id="${contact.id}" tabindex="0" aria-label="查看 ${escapeHTML(contact.name)}">
      <div class="avatar" style="${avatarStyle(contact.name)}">${escapeHTML([...contact.name][0] || "人")}</div>
      <div class="contact-card-info"><h3>${escapeHTML(contact.name)}</h3><p>${escapeHTML(primaryMethod(contact))}</p></div>
      <button class="star-button${contact.favorite ? " favorite" : ""}" data-action="favorite" data-id="${contact.id}" aria-label="${contact.favorite ? "取消收藏" : "收藏"} ${escapeHTML(contact.name)}" aria-pressed="${contact.favorite}">${icon("star")}</button>
    </article>`).join("");
}

function renderDetail() {
  const panel = $("#detail-panel");
  const contact = state.contacts.find((item) => item.id === state.selectedId);
  if (!contact) {
    panel.innerHTML = `<div class="detail-placeholder"><div class="placeholder-illustration">${icon("contacts")}</div><h2>选择一个联系人</h2><p>查看完整联系方式与备注</p></div>`;
    return;
  }
  const methods = contact.methods.length ? contact.methods.map((method) => `
    <div class="method-item"><span class="method-icon">${icon(["mobile", "phone"].includes(method.kind) ? "phone" : method.kind === "email" ? "mail" : "note")}</span>
      <div class="method-copy"><small>${escapeHTML(KINDS[method.kind] || method.kind)}${method.label ? ` · ${escapeHTML(method.label)}` : ""}</small><div>${escapeHTML(method.value)}</div></div></div>`).join("") : '<p class="no-methods">暂未填写联系方式，点击编辑即可添加。</p>';
  panel.innerHTML = `
    <div class="detail-cover">
      <button class="star-button detail-star${contact.favorite ? " favorite" : ""}" data-action="favorite" data-id="${contact.id}" aria-label="切换收藏">${icon("star")}</button>
      <div class="avatar" style="${avatarStyle(contact.name)}">${escapeHTML([...contact.name][0] || "人")}</div>
      <h2>${escapeHTML(contact.name)}</h2><p class="detail-subtitle">${contact.methods.length} 条联系方式${contact.favorite ? " · 星标联系人" : ""}</p>
      <div class="detail-actions"><button class="button button-secondary" data-action="edit" data-id="${contact.id}">${icon("edit")}编辑</button><button class="button button-secondary delete-button" data-action="delete" data-id="${contact.id}">${icon("trash")}删除</button></div>
    </div>
    <div class="detail-body"><h3 class="detail-section-title">联系方式</h3><div class="method-list">${methods}</div><h3 class="detail-section-title">备注</h3><p class="notes-copy">${escapeHTML(contact.notes || "暂无备注")}</p></div>`;
}

function selectFilter(favoriteOnly) {
  state.favoriteOnly = favoriteOnly;
  state.selectedId = null;
  $("#nav-all").classList.toggle("active", !favoriteOnly);
  $("#nav-favorites").classList.toggle("active", favoriteOnly);
  $("#page-title").textContent = favoriteOnly ? "星标联系人" : "全部联系人";
  loadContacts({ keepSelection: false });
}

function addMethodRow(method = { kind: "mobile", value: "", label: "" }) {
  if ($("#method-editor").children.length >= 30) return toast("每个联系人最多添加 30 条联系方式", true);
  const row = document.createElement("div");
  row.className = "method-row";
  const options = Object.entries(KINDS).map(([key, label]) => `<option value="${key}"${method.kind === key ? " selected" : ""}>${label}</option>`).join("");
  row.innerHTML = `<select class="method-kind" aria-label="联系方式类型">${options}</select><input class="method-value" aria-label="联系方式内容" maxlength="200" value="${escapeHTML(method.value)}" placeholder="请输入具体内容"><input class="method-label" aria-label="联系方式标签（可选）" maxlength="30" value="${escapeHTML(method.label || "")}" placeholder="标签（可选）"><button class="remove-method" type="button" aria-label="删除此联系方式">${icon("close")}</button>`;
  row.querySelector(".remove-method").addEventListener("click", () => row.remove());
  $("#method-editor").appendChild(row);
}

function openContactDialog(contact = null) {
  $("#contact-form").reset();
  $("#method-editor").innerHTML = "";
  $("#contact-id").value = contact?.id || "";
  $("#contact-dialog-title").textContent = contact ? "编辑联系人" : "新建联系人";
  $("#contact-name").value = contact?.name || "";
  $("#contact-favorite").checked = contact?.favorite || false;
  $("#contact-notes").value = contact?.notes || "";
  (contact?.methods.length ? contact.methods : [{ kind: "mobile", value: "" }]).forEach(addMethodRow);
  $("#contact-dialog").showModal();
  setTimeout(() => $("#contact-name").focus(), 50);
}

async function saveContact(event) {
  event.preventDefault();
  const id = $("#contact-id").value;
  const payload = {
    name: $("#contact-name").value,
    favorite: $("#contact-favorite").checked,
    notes: $("#contact-notes").value,
    methods: [...$("#method-editor").children].map((row) => ({
      kind: row.querySelector(".method-kind").value,
      value: row.querySelector(".method-value").value,
      label: row.querySelector(".method-label").value
    }))
  };
  const button = $("#save-contact-button");
  button.disabled = true;
  try {
    const contact = await api(id ? `/api/contacts/${id}` : "/api/contacts", {
      method: id ? "PUT" : "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload)
    });
    state.selectedId = contact.id;
    $("#contact-dialog").close();
    toast(id ? "联系人已更新" : "联系人已保存");
    await loadContacts();
  } catch (error) { toast(error.message, true); }
  finally { button.disabled = false; }
}

async function toggleFavorite(id) {
  try {
    const contact = await api(`/api/contacts/${id}/favorite`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: "{}" });
    state.selectedId = contact.id;
    toast(contact.favorite ? `已收藏 ${contact.name}` : `已取消收藏 ${contact.name}`);
    await loadContacts();
  } catch (error) { toast(error.message, true); }
}

async function deleteContact(id) {
  const contact = state.contacts.find((item) => item.id === id);
  if (!contact || !window.confirm(`确定删除“${contact.name}”吗？其全部联系方式也会一并删除，此操作不可撤销。`)) return;
  try {
    await api(`/api/contacts/${id}`, { method: "DELETE" });
    state.selectedId = null;
    toast("联系人已删除");
    await loadContacts({ keepSelection: false });
  } catch (error) { toast(error.message, true); }
}

async function importExcel(event) {
  event.preventDefault();
  const file = $("#excel-file").files[0];
  if (!file) return toast("请先选择 Excel 文件", true);
  const formData = new FormData();
  formData.append("file", file);
  const button = $("#confirm-import-button");
  button.disabled = true;
  try {
    const result = await api("/api/contacts/import", { method: "POST", body: formData });
    $("#import-dialog").close();
    $("#import-form").reset();
    $("#file-label").textContent = "点击选择 Excel 文件";
    const skipped = result.skipped.length ? `，跳过 ${result.skipped.length} 位同名联系人` : "";
    toast(`成功导入 ${result.imported} 位联系人${skipped}`);
    state.selectedId = null;
    await loadContacts({ keepSelection: false });
  } catch (error) {
    toast([error.message, ...(error.details || [])].join("\n"), true);
  } finally { button.disabled = false; }
}

$("#nav-all").addEventListener("click", () => selectFilter(false));
$("#nav-favorites").addEventListener("click", () => selectFilter(true));
$("#new-contact-button").addEventListener("click", () => openContactDialog());
$("#add-method-button").addEventListener("click", () => addMethodRow());
$("#contact-form").addEventListener("submit", saveContact);
$("#import-form").addEventListener("submit", importExcel);
$("#import-button").addEventListener("click", () => $("#import-dialog").showModal());
$("#excel-file").addEventListener("change", (event) => { $("#file-label").textContent = event.target.files[0]?.name || "点击选择 Excel 文件"; });
document.querySelectorAll("[data-close]").forEach((button) => button.addEventListener("click", () => $(`#${button.dataset.close}`).close()));
document.querySelectorAll("dialog").forEach((dialog) => dialog.addEventListener("click", (event) => { if (event.target === dialog) dialog.close(); }));

document.body.addEventListener("click", (event) => {
  const action = event.target.closest("[data-action]");
  if (action) {
    event.stopPropagation();
    if (action.dataset.action === "favorite") toggleFavorite(Number(action.dataset.id));
    if (action.dataset.action === "edit") openContactDialog(state.contacts.find((item) => item.id === Number(action.dataset.id)));
    if (action.dataset.action === "delete") deleteContact(Number(action.dataset.id));
    if (action.dataset.action === "new") openContactDialog();
    return;
  }
  const card = event.target.closest(".contact-card");
  if (card) { state.selectedId = Number(card.dataset.id); renderContacts(); renderDetail(); }
});
document.body.addEventListener("keydown", (event) => {
  if ((event.key === "Enter" || event.key === " ") && event.target.classList.contains("contact-card")) {
    event.preventDefault(); state.selectedId = Number(event.target.dataset.id); renderContacts(); renderDetail();
  }
});
let searchTimer;
$("#search-input").addEventListener("input", (event) => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => { state.query = event.target.value.trim(); state.selectedId = null; loadContacts({ keepSelection: false }); }, 250);
});
document.addEventListener("keydown", (event) => {
  if (event.ctrlKey && event.key.toLowerCase() === "k") { event.preventDefault(); $("#search-input").focus(); }
});

loadContacts();
