const state = { contacts: [], selectedId: null, favoriteOnly: false, query: "" };
const KINDS = {
  mobile: "Mobile", phone: "Phone", email: "Email", wechat: "WeChat",
  qq: "QQ", weibo: "Weibo", address: "Address", other: "Other"
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
  return (preferred || contact.methods[0])?.value || "No contact method provided";
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
  const data = await response.json().catch(() => ({ error: "The server returned an unreadable response" }));
  if (!response.ok) {
    const error = new Error(data.error || "Operation failed");
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
    $("#result-summary").textContent = `Showing ${state.contacts.length} of ${data.stats.total} contacts`;
    if (!keepSelection || !state.contacts.some((contact) => contact.id === state.selectedId)) {
      state.selectedId = state.contacts[0]?.id ?? null;
    }
    renderContacts();
    renderDetail();
  } catch (error) {
    $("#contact-list").innerHTML = `<div class="empty-state"><h3>Failed to load contacts</h3><p>${escapeHTML(error.message)}</p></div>`;
    toast(error.message, true);
  }
}

function renderContacts() {
  const list = $("#contact-list");
  if (!state.contacts.length) {
    const filtered = state.query || state.favoriteOnly;
    list.innerHTML = `<div class="empty-state">${icon(state.favoriteOnly ? "star" : "contacts")}
      <h3>${filtered ? "No matching contacts found" : "Your address book is empty"}</h3>
      <p>${filtered ? "Try another keyword or switch to All Contacts" : "Add your first contact or import contacts from Excel"}</p>
      ${filtered ? "" : '<button class="button button-primary" data-action="new">New Contact</button>'}</div>`;
    return;
  }
  list.innerHTML = state.contacts.map((contact) => `
    <article class="contact-card${contact.id === state.selectedId ? " selected" : ""}" data-id="${contact.id}" tabindex="0" aria-label="View ${escapeHTML(contact.name)}">
      <div class="avatar" style="${avatarStyle(contact.name)}">${escapeHTML([...contact.name][0] || "?")}</div>
      <div class="contact-card-info"><h3>${escapeHTML(contact.name)}</h3><p>${escapeHTML(primaryMethod(contact))}</p></div>
      <button class="star-button${contact.favorite ? " favorite" : ""}" data-action="favorite" data-id="${contact.id}" aria-label="${contact.favorite ? "Remove from favorites" : "Add to favorites"}: ${escapeHTML(contact.name)}" aria-pressed="${contact.favorite}">${icon("star")}</button>
    </article>`).join("");
}

function renderDetail() {
  const panel = $("#detail-panel");
  const contact = state.contacts.find((item) => item.id === state.selectedId);
  if (!contact) {
    panel.innerHTML = `<div class="detail-placeholder"><div class="placeholder-illustration">${icon("contacts")}</div><h2>Select a contact</h2><p>View all contact methods and notes</p></div>`;
    return;
  }
  const methods = contact.methods.length ? contact.methods.map((method) => `
    <div class="method-item"><span class="method-icon">${icon(["mobile", "phone"].includes(method.kind) ? "phone" : method.kind === "email" ? "mail" : "note")}</span>
      <div class="method-copy"><small>${escapeHTML(KINDS[method.kind] || method.kind)}${method.label ? ` · ${escapeHTML(method.label)}` : ""}</small><div>${escapeHTML(method.value)}</div></div></div>`).join("") : '<p class="no-methods">No contact methods yet. Click Edit to add one.</p>';
  panel.innerHTML = `
    <div class="detail-cover">
      <button class="star-button detail-star${contact.favorite ? " favorite" : ""}" data-action="favorite" data-id="${contact.id}" aria-label="Toggle favorite">${icon("star")}</button>
      <div class="avatar" style="${avatarStyle(contact.name)}">${escapeHTML([...contact.name][0] || "?")}</div>
      <h2>${escapeHTML(contact.name)}</h2><p class="detail-subtitle">${contact.methods.length} contact methods${contact.favorite ? " · Starred Contact" : ""}</p>
      <div class="detail-actions"><button class="button button-secondary" data-action="edit" data-id="${contact.id}">${icon("edit")}Edit</button><button class="button button-secondary delete-button" data-action="delete" data-id="${contact.id}">${icon("trash")}Delete</button></div>
    </div>
    <div class="detail-body"><h3 class="detail-section-title">CONTACT METHODS</h3><div class="method-list">${methods}</div><h3 class="detail-section-title">NOTES</h3><p class="notes-copy">${escapeHTML(contact.notes || "No notes yet")}</p></div>`;
}

function selectFilter(favoriteOnly) {
  state.favoriteOnly = favoriteOnly;
  state.selectedId = null;
  $("#nav-all").classList.toggle("active", !favoriteOnly);
  $("#nav-favorites").classList.toggle("active", favoriteOnly);
  $("#page-title").textContent = favoriteOnly ? "Starred Contacts" : "All Contacts";
  loadContacts({ keepSelection: false });
}

function addMethodRow(method = { kind: "mobile", value: "" }) {
  if ($("#method-editor").children.length >= 30) return toast("You can add up to 30 contact methods per contact", true);
  const row = document.createElement("div");
  row.className = "method-row";
  const options = Object.entries(KINDS).map(([key, label]) => `<option value="${key}"${method.kind === key ? " selected" : ""}>${label}</option>`).join("");
  row.innerHTML = `<select aria-label="Contact method type">${options}</select><input aria-label="Contact method value" maxlength="200" value="${escapeHTML(method.value)}" placeholder="Enter contact details"><button class="remove-method" type="button" aria-label="Remove this contact method">${icon("close")}</button>`;
  row.querySelector(".remove-method").addEventListener("click", () => row.remove());
  $("#method-editor").appendChild(row);
}

function openContactDialog(contact = null) {
  $("#contact-form").reset();
  $("#method-editor").innerHTML = "";
  $("#contact-id").value = contact?.id || "";
  $("#contact-dialog-title").textContent = contact ? "Edit Contact" : "New Contact";
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
    methods: [...$("#method-editor").children].map((row) => ({ kind: row.querySelector("select").value, value: row.querySelector("input").value }))
  };
  const button = $("#save-contact-button");
  button.disabled = true;
  try {
    const contact = await api(id ? `/api/contacts/${id}` : "/api/contacts", {
      method: id ? "PUT" : "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload)
    });
    state.selectedId = contact.id;
    $("#contact-dialog").close();
    toast(id ? "Contact updated" : "Contact saved");
    await loadContacts();
  } catch (error) { toast(error.message, true); }
  finally { button.disabled = false; }
}

async function toggleFavorite(id) {
  try {
    const contact = await api(`/api/contacts/${id}/favorite`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: "{}" });
    state.selectedId = contact.id;
    toast(contact.favorite ? `Added ${contact.name} to favorites` : `Removed ${contact.name} from favorites`);
    await loadContacts();
  } catch (error) { toast(error.message, true); }
}

async function deleteContact(id) {
  const contact = state.contacts.find((item) => item.id === id);
  if (!contact || !window.confirm(`Delete "${contact.name}"? All associated contact methods will also be deleted. This action cannot be undone.`)) return;
  try {
    await api(`/api/contacts/${id}`, { method: "DELETE" });
    state.selectedId = null;
    toast("Contact deleted");
    await loadContacts({ keepSelection: false });
  } catch (error) { toast(error.message, true); }
}

async function importExcel(event) {
  event.preventDefault();
  const file = $("#excel-file").files[0];
  if (!file) return toast("Please select an Excel file first", true);
  const formData = new FormData();
  formData.append("file", file);
  const button = $("#confirm-import-button");
  button.disabled = true;
  try {
    const result = await api("/api/contacts/import", { method: "POST", body: formData });
    $("#import-dialog").close();
    $("#import-form").reset();
    $("#file-label").textContent = "Click to select an Excel file";
    const skipped = result.skipped.length ? `; skipped ${result.skipped.length} duplicate ${result.skipped.length === 1 ? "name" : "names"}` : "";
    toast(`Imported ${result.imported} ${result.imported === 1 ? "contact" : "contacts"}${skipped}`);
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
$("#excel-file").addEventListener("change", (event) => { $("#file-label").textContent = event.target.files[0]?.name || "Click to select an Excel file"; });
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
