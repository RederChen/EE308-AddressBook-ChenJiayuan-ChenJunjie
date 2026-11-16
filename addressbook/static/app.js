"use strict";

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => Array.from(document.querySelectorAll(selector));

const KINDS = {
  mobile: "手机", phone: "电话", email: "邮箱", wechat: "微信",
  qq: "QQ", weibo: "微博", address: "地址", other: "其他",
};
const KIND_ORDER = Object.keys(KINDS);
const AVATARS = [
  ["#e7efe4", "#42633c"], ["#e9edf6", "#4a5c86"], ["#f6ece0", "#8a6438"],
  ["#f3e7ea", "#8a4a58"], ["#e4f0ee", "#3f6f68"], ["#f0ece2", "#6f6647"],
];
const PAGE_SIZE = 50;
const MAX_METHODS = 30;

const state = {
  contacts: [],
  total: 0,
  hasMore: false,
  limit: PAGE_SIZE,
  query: "",
  favoriteOnly: false,
  trash: false,
  sort: "favorite",
  selectedId: null,
  selection: new Set(),
  bulkMode: false,
};

/* ---------------------------------------------------------------- 工具函数 */

function escapeHTML(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[char]));
}
const escapeAttr = escapeHTML;

function icon(name, className = "") {
  return `<svg${className ? ` class="${className}"` : ""}><use href="#${name}"/></svg>`;
}

function avatarStyle(name) {
  const text = String(name || "?");
  const code = Array.from(text).reduce((sum, char) => sum + char.codePointAt(0), 0);
  const [background, color] = AVATARS[code % AVATARS.length];
  return `--avatar:${background};--avatar-text:${color}`;
}

function initial(name) {
  const text = String(name || "?").trim();
  return text ? Array.from(text)[0].toUpperCase() : "?";
}

function primaryMethod(contact) {
  const methods = contact.methods || [];
  return ["mobile", "phone", "email"].map((kind) => methods.find((item) => item.kind === kind)).find(Boolean)
    || methods[0] || null;
}

function contactLink(method) {
  const value = String(method.value || "").trim();
  if (!value) return "";
  if (method.kind === "mobile" || method.kind === "phone") {
    const dialable = value.replace(/[^\d+]/g, "");
    return dialable ? `tel:${dialable}` : "";
  }
  if (method.kind === "email") return `mailto:${value}`;
  return "";
}

function formatTime(value) {
  if (!value) return "未知时间";
  // SQLite 保存的是 UTC 时间（V1.2 起带毫秒），补上 Z 后按本地时区展示
  const date = new Date(String(value).replace(" ", "T") + "Z");
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleString("zh-CN", { hour12: false });
}

function toast(message, error = false, action = null) {
  const item = document.createElement("div");
  item.className = `toast${error ? " error" : ""}`;
  const text = document.createElement("span");
  text.textContent = message;
  item.append(text);
  if (action) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "toast-action";
    button.textContent = action.label;
    button.addEventListener("click", () => { item.remove(); action.onClick(); });
    item.append(button);
  }
  $("#toast-region").append(item);
  setTimeout(() => item.remove(), action ? 8000 : error ? 6000 : 3000);
}

async function api(url, options = {}) {
  let response;
  try {
    response = await fetch(url, options);
  } catch (error) {
    throw new Error("网络连接失败，请确认本地服务仍在运行");
  }
  if (response.status === 204) return null;
  let data = null;
  try {
    data = await response.json();
  } catch (error) {
    data = null;
  }
  if (!response.ok) {
    const failure = new Error((data && data.error) || `请求失败（${response.status}）`);
    failure.details = (data && data.details) || [];
    throw failure;
  }
  return data;
}

function messageOf(error) {
  return [error.message, ...(error.details || [])].join("\n");
}

/* ------------------------------------------------------------ 数据与渲染 */

function updateStats(stats) {
  if (!stats) return;
  $("#total-count").textContent = stats.total;
  $("#favorite-count").textContent = stats.favorites;
  $("#trash-count").textContent = stats.trash;
  $("#empty-trash-button").hidden = !(state.trash && stats.trash > 0);
}

function placeholder(title, hint) {
  return `<div class="detail-placeholder">
    <div class="placeholder-illustration">${icon("i-contacts")}</div>
    <h2>${escapeHTML(title)}</h2>
    <p>${escapeHTML(hint)}</p>
  </div>`;
}

function emptyListHTML() {
  if (state.trash) {
    return `<div class="empty-state">${icon("i-trash")}<h3>回收站是空的</h3>
      <p>删除的联系人会被移到这里，可随时恢复。</p></div>`;
  }
  if (state.query) {
    return `<div class="empty-state">${icon("i-search")}<h3>没有匹配的联系人</h3>
      <p>换个关键词试试，或清空搜索条件。</p></div>`;
  }
  if (state.favoriteOnly) {
    return `<div class="empty-state">${icon("i-star")}<h3>还没有星标联系人</h3>
      <p>点击联系人卡片上的星形按钮即可收藏。</p></div>`;
  }
  return `<div class="empty-state">${icon("i-contacts")}<h3>通讯录还是空的</h3>
    <p>点击右上角“新建联系人”，或从 Excel 导入一份名单。</p></div>`;
}

function cardHTML(contact) {
  const primary = primaryMethod(contact);
  const primaryText = primary ? `${KINDS[primary.kind] || ""} · ${primary.value}` : "暂无联系方式";
  const checkbox = state.bulkMode
    ? `<input class="card-check" type="checkbox" data-check="${contact.id}" ${state.selection.has(contact.id) ? "checked" : ""} aria-label="选择 ${escapeAttr(contact.name)}">`
    : "";
  const star = state.trash
    ? ""
    : `<button class="star-button${contact.favorite ? " favorite" : ""}" type="button" data-action="favorite" data-id="${contact.id}" aria-pressed="${contact.favorite}" title="${contact.favorite ? "取消星标" : "设为星标"}" aria-label="${contact.favorite ? "取消星标" : "设为星标"}">${icon("i-star")}</button>`;
  return `<article class="contact-card${state.selectedId === contact.id ? " selected" : ""}" data-id="${contact.id}" tabindex="0" aria-label="${escapeAttr(contact.name)}">
    ${checkbox}
    <span class="avatar" style="${avatarStyle(contact.name)}">${escapeHTML(initial(contact.name))}</span>
    <div class="contact-card-info"><h3>${escapeHTML(contact.name)}</h3><p>${escapeHTML(primaryText)}</p></div>
    ${star}
    <span class="method-total">${contact.methods.length} 条</span>
  </article>`;
}

function methodHTML(method) {
  const label = method.label ? `<small>${escapeHTML(method.label)}</small>` : "";
  const link = contactLink(method);
  const content = link
    ? `<a class="method-link" href="${escapeAttr(link)}">${escapeHTML(method.value)}</a>`
    : escapeHTML(method.value);
  return `<div class="method-item">
    <span class="method-icon">${icon(["mobile", "phone"].includes(method.kind) ? "i-phone" : method.kind === "email" ? "i-mail" : "i-note")}</span>
    <div class="method-copy">${label}<div>${content}</div></div>
    <button class="copy-button" type="button" data-copy="${escapeAttr(method.value)}" title="复制" aria-label="复制${escapeAttr(KINDS[method.kind] || "联系方式")}">${icon("i-copy")}</button>
  </div>`;
}

function methodsBlock(contact) {
  if (!contact.methods.length) return '<p class="no-methods">还没有联系方式，点击“编辑”补充。</p>';
  return `<div class="method-list">${contact.methods.map(methodHTML).join("")}</div>`;
}

function notesBlock(contact) {
  return contact.notes
    ? `<p class="notes-copy">${escapeHTML(contact.notes)}</p>`
    : '<p class="notes-copy muted">暂无备注</p>';
}

function detailHTML(contact) {
  return `<div class="detail-cover">
    <button class="star-button detail-star${contact.favorite ? " favorite" : ""}" type="button" data-action="favorite" data-id="${contact.id}" aria-pressed="${contact.favorite}" aria-label="切换星标">${icon("i-star")}</button>
    <span class="avatar" style="${avatarStyle(contact.name)}">${escapeHTML(initial(contact.name))}</span>
    <h2>${escapeHTML(contact.name)}</h2>
    <p class="detail-subtitle">${contact.methods.length} 条联系方式 · 更新于 ${escapeHTML(formatTime(contact.updated_at))}</p>
    <div class="detail-actions">
      <button class="button" type="button" data-action="edit" data-id="${contact.id}">${icon("i-edit")}编辑</button>
      <button class="button delete-button" type="button" data-action="delete" data-id="${contact.id}">${icon("i-trash")}删除</button>
    </div>
  </div>
  <div class="detail-body">
    <h3 class="detail-section-title">联系方式</h3>
    ${methodsBlock(contact)}
    <h3 class="detail-section-title">备注</h3>
    ${notesBlock(contact)}
    <h3 class="detail-section-title">记录</h3>
    <p class="detail-meta">${icon("i-clock")}创建于 ${escapeHTML(formatTime(contact.created_at))}</p>
  </div>`;
}

function trashDetailHTML(contact) {
  return `<div class="detail-cover">
    <span class="avatar" style="${avatarStyle(contact.name)}">${escapeHTML(initial(contact.name))}</span>
    <h2>${escapeHTML(contact.name)}</h2>
    <p class="detail-subtitle">已于 ${escapeHTML(formatTime(contact.deleted_at))} 移入回收站</p>
    <div class="detail-actions">
      <button class="button" type="button" data-action="restore" data-id="${contact.id}">${icon("i-restore")}恢复</button>
      <button class="button delete-button" type="button" data-action="purge" data-id="${contact.id}">${icon("i-trash")}彻底删除</button>
    </div>
  </div>
  <div class="detail-body">
    <h3 class="detail-section-title">联系方式</h3>
    ${methodsBlock(contact)}
    <h3 class="detail-section-title">备注</h3>
    ${notesBlock(contact)}
  </div>`;
}

function renderList() {
  const list = $("#contact-list");
  list.innerHTML = state.contacts.length
    ? state.contacts.map(cardHTML).join("")
    : emptyListHTML();
  const selectAll = $("#select-all");
  selectAll.checked = state.contacts.length > 0 && state.selection.size === state.contacts.length;
  selectAll.indeterminate = state.selection.size > 0 && state.selection.size < state.contacts.length;
  $("#bulk-count").textContent = `已选 ${state.selection.size} 位`;
  $("#load-more-button").hidden = !(state.hasMore && !state.trash);
  $("#list-hint").textContent = state.hasMore && !state.trash
    ? `已显示 ${state.contacts.length} / 共 ${state.total} 位`
    : "";
}

function renderDetail() {
  const panel = $("#detail-panel");
  const contact = state.contacts.find((item) => item.id === state.selectedId);
  if (state.trash) {
    panel.innerHTML = contact
      ? trashDetailHTML(contact)
      : placeholder("回收站是空的", "删除的联系人会先保留在这里，可随时恢复");
    return;
  }
  panel.innerHTML = contact
    ? detailHTML(contact)
    : placeholder("选择一个联系人", "查看完整联系方式与备注");
}

async function loadContacts({ keepSelection = true } = {}) {
  const params = new URLSearchParams();
  if (state.query) params.set("query", state.query);
  if (state.favoriteOnly) params.set("favorite", "1");
  if (state.trash) params.set("trash", "1");
  params.set("sort", state.sort);
  params.set("limit", state.limit);

  try {
    const data = await api(`/api/contacts?${params.toString()}`);
    state.contacts = data.contacts;
    state.total = data.total;
    state.hasMore = data.has_more;
    state.selection = new Set([...state.selection].filter((id) => state.contacts.some((item) => item.id === id)));
    if (!keepSelection || !state.contacts.some((item) => item.id === state.selectedId)) {
      state.selectedId = state.contacts.length ? state.contacts[0].id : null;
    }
    updateStats(data.stats);
    const modeText = state.trash ? "回收站" : state.favoriteOnly ? "星标联系" : "联系人";
    $("#result-summary").textContent = state.query
      ? `“${state.query}” 找到 ${state.total} 位${modeText}`
      : `共 ${state.total} 位${modeText}`;
    renderList();
    renderDetail();
  } catch (error) {
    $("#contact-list").innerHTML = `<div class="empty-state">${icon("i-contacts")}<h3>加载失败</h3><p>${escapeHTML(error.message)}</p></div>`;
    $("#result-summary").textContent = "加载失败";
    toast(messageOf(error), true);
  }
}

/* -------------------------------------------------------------- 视图切换 */

function setView({ favoriteOnly = state.favoriteOnly, trash = state.trash } = {}) {
  state.favoriteOnly = favoriteOnly;
  state.trash = trash;
  state.limit = PAGE_SIZE;
  state.selectedId = null;
  state.selection.clear();
  state.bulkMode = false;
  $("#bulk-bar").hidden = true;

  $("#nav-all").classList.toggle("active", !trash && !favoriteOnly);
  $("#nav-favorites").classList.toggle("active", !trash && favoriteOnly);
  $("#nav-trash").classList.toggle("active", trash);
  $("#page-title").textContent = trash ? "回收站" : favoriteOnly ? "星标联系人" : "全部联系人";
  $("#sort-select").disabled = trash;
  $("#empty-trash-button").hidden = !trash;
  updateBulkBar();
  loadContacts({ keepSelection: false });
}

function updateBulkBar() {
  $("#bulk-bar").hidden = !state.bulkMode;
  $("#bulk-toggle-button").classList.toggle("button-primary", state.bulkMode);
  const actions = $$("[data-bulk]");
  actions.forEach((button) => {
    const action = button.dataset.bulk;
    if (state.trash) button.hidden = !["restore", "purge"].includes(action);
    else button.hidden = !["favorite", "unfavorite", "delete"].includes(action);
  });
}

/* ------------------------------------------------------------ 收藏与删除 */

async function toggleFavorite(id) {
  try {
    await api(`/api/contacts/${id}/favorite`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
    });
    await loadContacts();
  } catch (error) {
    toast(messageOf(error), true);
  }
}

async function deleteContact(id) {
  const contact = state.contacts.find((item) => item.id === id);
  if (!window.confirm(`确定把“${contact ? contact.name : "该联系人"}”移入回收站吗？\n移入后可以随时恢复。`)) return;
  try {
    await api(`/api/contacts/${id}`, { method: "DELETE" });
    if (state.selectedId === id) state.selectedId = null;
    toast("已移入回收站", false, {
      label: "撤销",
      onClick: async () => {
        try {
          await api(`/api/contacts/${id}/restore`, { method: "POST" });
          toast("已恢复该联系人");
          await loadContacts();
        } catch (error) {
          toast(messageOf(error), true);
        }
      },
    });
    await loadContacts();
  } catch (error) {
    toast(messageOf(error), true);
  }
}

async function restoreContact(id) {
  try {
    await api(`/api/contacts/${id}/restore`, { method: "POST" });
    toast("已恢复到通讯录");
    await loadContacts();
  } catch (error) {
    toast(messageOf(error), true);
  }
}

async function purgeContact(id) {
  if (!window.confirm("彻底删除后无法恢复，确定继续吗？")) return;
  try {
    await api(`/api/trash/${id}`, { method: "DELETE" });
    toast("已彻底删除");
    await loadContacts();
  } catch (error) {
    toast(messageOf(error), true);
  }
}

async function emptyTrash() {
  if (!window.confirm("确定清空回收站吗？清空后所有内容都无法恢复。")) return;
  try {
    const data = await api("/api/trash", { method: "DELETE" });
    toast(`已清空回收站，共删除 ${data.purged} 位联系人`);
    await loadContacts();
  } catch (error) {
    toast(messageOf(error), true);
  }
}

/* ---------------------------------------------------------------- 批量操作 */

function toggleBulkMode(force) {
  state.bulkMode = typeof force === "boolean" ? force : !state.bulkMode;
  if (!state.bulkMode) state.selection.clear();
  updateBulkBar();
  renderList();
}

function toggleSelection(id) {
  if (state.selection.has(id)) state.selection.delete(id);
  else state.selection.add(id);
  renderList();
}

function toggleSelectAll(checked) {
  state.selection = checked ? new Set(state.contacts.map((item) => item.id)) : new Set();
  renderList();
}

async function runBulk(action) {
  const ids = [...state.selection];
  if (!ids.length) {
    toast("请先选择至少一位联系人", true);
    return;
  }
  const labels = {
    favorite: "收藏", unfavorite: "取消收藏", delete: "移入回收站",
    restore: "恢复", purge: "彻底删除",
  };
  const dangerous = ["delete", "purge"].includes(action);
  const suffix = action === "purge" ? "，彻底删除后无法恢复" : action === "delete" ? "，之后可在回收站恢复" : "";
  if (dangerous && !window.confirm(`确定对选中的 ${ids.length} 位联系人执行“${labels[action]}”吗${suffix}？`)) return;
  try {
    const result = await api("/api/contacts/bulk", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action, ids }),
    });
    toast(`已${labels[action]} ${result.affected} 位联系人`);
    state.selection.clear();
    await loadContacts();
  } catch (error) {
    toast(messageOf(error), true);
  }
}

/* -------------------------------------------------------------- 编辑表单 */

function addMethodRow(method = {}) {
  const editor = $("#method-editor");
  if (editor.children.length >= MAX_METHODS) {
    toast(`每个联系人最多 ${MAX_METHODS} 条联系方式`, true);
    return;
  }
  const row = document.createElement("div");
  row.className = "method-row";
  row.innerHTML = `<select class="method-kind" aria-label="联系方式类型">${KIND_ORDER.map((kind) => `<option value="${kind}"${kind === (method.kind || "mobile") ? " selected" : ""}>${KINDS[kind]}</option>`).join("")}</select>
    <input class="method-value" maxlength="200" placeholder="号码 / 邮箱 / 账号 / 地址" value="${escapeAttr(method.value || "")}">
    <input class="method-label" maxlength="30" placeholder="标签（可选）" value="${escapeAttr(method.label || "")}">
    <button class="remove-method" type="button" title="删除这条联系方式" aria-label="删除这条联系方式">${icon("i-close")}</button>`;
  row.querySelector(".remove-method").addEventListener("click", () => {
    row.remove();
    if (!editor.children.length) addMethodRow();
  });
  editor.append(row);
}

function openContactDialog(contact = null) {
  const form = $("#contact-form");
  form.reset();
  $("#method-editor").innerHTML = "";
  $("#contact-id").value = contact ? contact.id : "";
  $("#contact-dialog-title").textContent = contact ? "编辑联系人" : "新建联系人";
  $("#contact-name").value = contact ? contact.name : "";
  $("#contact-favorite").checked = contact ? contact.favorite : false;
  $("#contact-notes").value = contact ? contact.notes : "";
  const methods = contact && contact.methods.length ? contact.methods : [{ kind: "mobile", value: "", label: "" }];
  methods.forEach(addMethodRow);
  $("#contact-dialog").showModal();
  setTimeout(() => $("#contact-name").focus(), 50);
}

async function saveContact(event) {
  event.preventDefault();
  const button = $("#save-contact-button");
  const payload = {
    name: $("#contact-name").value.trim(),
    favorite: $("#contact-favorite").checked,
    notes: $("#contact-notes").value.trim(),
    methods: $$("#method-editor .method-row").map((row) => ({
      kind: row.querySelector(".method-kind").value,
      value: row.querySelector(".method-value").value.trim(),
      label: row.querySelector(".method-label").value.trim(),
    })).filter((method) => method.value),
  };
  if (!payload.name) {
    toast("请填写联系人姓名", true);
    $("#contact-name").focus();
    return;
  }
  const id = $("#contact-id").value;
  button.disabled = true;
  try {
    await api(id ? `/api/contacts/${id}` : "/api/contacts", {
      method: id ? "PUT" : "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    $("#contact-dialog").close();
    toast(id ? "联系人已更新" : "联系人已创建");
    await loadContacts();
  } catch (error) {
    toast(messageOf(error), true);
  } finally {
    button.disabled = false;
  }
}

/* ---------------------------------------------------------------- 导入框 */

let previewData = null;

function selectedMode() {
  const checked = document.querySelector('input[name="import-mode"]:checked');
  return checked ? checked.value : "skip";
}

function renderPreview(data) {
  const box = $("#import-preview");
  const skipText = selectedMode() === "overwrite"
    ? `已存在 ${data.update} 位（导入时将覆盖）`
    : `已存在 ${data.update} 位（导入时将跳过）`;
  const names = (list, label) => list.length ? `<li>${label}示例：${list.map(escapeHTML).join("、")}</li>` : "";
  box.innerHTML = `<strong>预览结果：共 ${data.total} 位联系人</strong>
    <ul>
      <li>新增 ${data.create} 位</li>
      <li>${skipText}</li>
      <li>文件内重复 ${data.skip} 位</li>
      ${names(data.created_names || [], "新增")}
      ${names(data.updated_names || [], "已存在")}
    </ul>
    <p>确认无误后点击“开始导入”。</p>`;
  box.hidden = false;
}

async function previewImport() {
  const file = $("#excel-file").files[0];
  if (!file) {
    toast("请先选择要导入的 Excel 文件", true);
    return;
  }
  const button = $("#preview-import-button");
  button.disabled = true;
  try {
    const form = new FormData();
    form.append("file", file);
    previewData = await api("/api/contacts/import/preview", { method: "POST", body: form });
    renderPreview(previewData);
  } catch (error) {
    previewData = null;
    $("#import-preview").hidden = true;
    toast(messageOf(error), true);
  } finally {
    button.disabled = false;
  }
}

async function importExcel(event) {
  event.preventDefault();
  const file = $("#excel-file").files[0];
  if (!file) {
    toast("请先选择要导入的 Excel 文件", true);
    return;
  }
  const button = $("#confirm-import-button");
  button.disabled = true;
  try {
    const form = new FormData();
    form.append("file", file);
    form.append("mode", selectedMode());
    const data = await api("/api/contacts/import", { method: "POST", body: form });
    const parts = [`成功导入 ${data.imported} 位`];
    if (data.updated) parts.push(`覆盖 ${data.updated} 位`);
    if (data.skipped.length) parts.push(`跳过 ${data.skipped.length} 位同名联系人`);
    toast(parts.join("，"));
    $("#import-dialog").close();
    $("#import-form").reset();
    $("#file-label").textContent = "点击选择 Excel 文件";
    $("#import-preview").hidden = true;
    previewData = null;
    await loadContacts();
  } catch (error) {
    toast(messageOf(error), true);
  } finally {
    button.disabled = false;
  }
}

/* ------------------------------------------------------------ 事件绑定 */

async function copyText(text) {
  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(text);
    } else {
      const helper = document.createElement("textarea");
      helper.value = text;
      helper.style.position = "fixed";
      helper.style.opacity = "0";
      document.body.append(helper);
      helper.select();
      document.execCommand("copy");
      helper.remove();
    }
    toast("已复制到剪贴板");
  } catch (error) {
    toast("复制失败，请手动选择文本", true);
  }
}

function exportURL() {
  const params = new URLSearchParams();
  if (state.query) params.set("query", state.query);
  if (state.favoriteOnly) params.set("favorite", "1");
  if (state.trash) params.set("trash", "1");
  params.set("sort", state.sort);
  return `/api/contacts/export?${params.toString()}`;
}

function bindEvents() {
  $("#nav-all").addEventListener("click", () => setView({ favoriteOnly: false, trash: false }));
  $("#nav-favorites").addEventListener("click", () => setView({ favoriteOnly: true, trash: false }));
  $("#nav-trash").addEventListener("click", () => setView({ favoriteOnly: false, trash: true }));
  $("#new-contact-button").addEventListener("click", () => openContactDialog());
  $("#add-method-button").addEventListener("click", () => addMethodRow());
  $("#contact-form").addEventListener("submit", saveContact);
  $("#import-form").addEventListener("submit", importExcel);
  $("#import-button").addEventListener("click", () => $("#import-dialog").showModal());
  $("#preview-import-button").addEventListener("click", previewImport);
  $("#empty-trash-button").addEventListener("click", emptyTrash);
  $("#bulk-toggle-button").addEventListener("click", () => toggleBulkMode());
  $("#bulk-exit-button").addEventListener("click", () => toggleBulkMode(false));
  $("#load-more-button").addEventListener("click", () => {
    state.limit += PAGE_SIZE;
    loadContacts();
  });
  $("#sort-select").addEventListener("change", (event) => {
    state.sort = event.target.value;
    loadContacts();
  });
  $("#excel-file").addEventListener("change", (event) => {
    const file = event.target.files[0];
    $("#file-label").textContent = file ? file.name : "点击选择 Excel 文件";
    $("#import-preview").hidden = true;
    previewData = null;
  });
  $$('input[name="import-mode"]').forEach((input) => input.addEventListener("change", () => {
    if (previewData) renderPreview(previewData);
  }));
  $("#select-all").addEventListener("change", (event) => toggleSelectAll(event.target.checked));
  $$("[data-bulk]").forEach((button) => button.addEventListener("click", () => runBulk(button.dataset.bulk)));
  $("#export-button").addEventListener("click", (event) => {
    event.currentTarget.href = exportURL();
  });
  $$("[data-close]").forEach((button) => button.addEventListener("click", () => $(`#${button.dataset.close}`).close()));
  $$("dialog").forEach((dialog) => dialog.addEventListener("click", (event) => {
    if (event.target === dialog) dialog.close();
  }));

  document.body.addEventListener("click", (event) => {
    const copy = event.target.closest("[data-copy]");
    if (copy) {
      event.stopPropagation();
      copyText(copy.dataset.copy);
      return;
    }
    const check = event.target.closest("[data-check]");
    if (check) {
      event.stopPropagation();
      toggleSelection(Number(check.dataset.check));
      return;
    }
    const action = event.target.closest("[data-action]");
    if (action) {
      event.stopPropagation();
      const id = Number(action.dataset.id);
      if (action.dataset.action === "favorite") toggleFavorite(id);
      if (action.dataset.action === "edit") openContactDialog(state.contacts.find((item) => item.id === id));
      if (action.dataset.action === "delete") deleteContact(id);
      if (action.dataset.action === "restore") restoreContact(id);
      if (action.dataset.action === "purge") purgeContact(id);
      return;
    }
    const card = event.target.closest(".contact-card");
    if (card) {
      const id = Number(card.dataset.id);
      if (state.bulkMode) toggleSelection(id);
      else {
        state.selectedId = id;
        renderList();
        renderDetail();
      }
    }
  });

  document.body.addEventListener("keydown", (event) => {
    if ((event.key === "Enter" || event.key === " ") && event.target.classList.contains("contact-card")) {
      event.preventDefault();
      const id = Number(event.target.dataset.id);
      if (state.bulkMode) toggleSelection(id);
      else {
        state.selectedId = id;
        renderList();
        renderDetail();
      }
    }
  });

  let searchTimer;
  $("#search-input").addEventListener("input", (event) => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => {
      state.query = event.target.value.trim();
      state.limit = PAGE_SIZE;
      loadContacts({ keepSelection: false });
    }, 250);
  });

  document.addEventListener("keydown", (event) => {
    if (event.ctrlKey && event.key.toLowerCase() === "k") {
      event.preventDefault();
      $("#search-input").focus();
      $("#search-input").select();
    }
    if (event.ctrlKey && event.key.toLowerCase() === "n") {
      event.preventDefault();
      openContactDialog();
    }
    if (event.ctrlKey && event.key.toLowerCase() === "b") {
      event.preventDefault();
      toggleBulkMode();
    }
  });
}

bindEvents();
loadContacts();
