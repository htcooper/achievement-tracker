// === State ===
let allTags = [];
let allCompanies = [];
let features = { ai_tags: false, notion: false };
let currentFormTags = [];
let editFormTags = [];

// === API Helpers ===
async function api(method, path, body) {
    const opts = { method, headers: { "Content-Type": "application/json" } };
    if (body) opts.body = JSON.stringify(body);
    const res = await fetch(`/api${path}`, opts);
    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Request failed" }));
        throw new Error(err.detail || "Request failed");
    }
    return res.json();
}

async function apiUpload(path, file) {
    const form = new FormData();
    form.append("file", file);
    const res = await fetch(`/api${path}`, { method: "POST", body: form });
    if (!res.ok) throw new Error("Upload failed");
    return res.json();
}

// === Toast ===
function showToast(msg, isError = false) {
    let toast = document.querySelector(".toast");
    if (!toast) {
        toast = document.createElement("div");
        toast.className = "toast";
        document.body.appendChild(toast);
    }
    toast.textContent = msg;
    toast.classList.toggle("error", isError);
    toast.classList.add("visible");
    setTimeout(() => toast.classList.remove("visible"), 3000);
}

// === Tag Input Component ===
function createTagInput(containerId, chipsId, inputId, autocompleteId, getTagsFn, setTagsFn) {
    const container = document.getElementById(containerId);
    const chipsEl = document.getElementById(chipsId);
    const input = document.getElementById(inputId);
    const dropdown = document.getElementById(autocompleteId);

    function render() {
        const tags = getTagsFn();
        chipsEl.innerHTML = tags.map(tag =>
            `<span class="tag-chip">${esc(tag)}<span class="remove-tag" data-tag="${esc(tag)}">&times;</span></span>`
        ).join("");
    }

    chipsEl.addEventListener("click", (e) => {
        const removeBtn = e.target.closest(".remove-tag");
        if (removeBtn) {
            const tag = removeBtn.dataset.tag;
            setTagsFn(getTagsFn().filter(t => t !== tag));
            render();
        }
    });

    container.addEventListener("click", () => input.focus());

    input.addEventListener("input", () => {
        const val = input.value.toLowerCase().trim();
        if (!val) {
            dropdown.classList.remove("visible");
            return;
        }
        const current = getTagsFn();
        const matches = allTags
            .filter(t => t.tag.includes(val))
            .slice(0, 8);

        if (matches.length === 0) {
            dropdown.classList.remove("visible");
            return;
        }

        dropdown.innerHTML = matches.map(t => {
            const added = current.includes(t.tag);
            return `<div class="tag-autocomplete-item" data-tag="${esc(t.tag)}">
                ${esc(t.tag)}${added ? '<span class="already-added">added</span>' : ""}
            </div>`;
        }).join("");
        dropdown.classList.add("visible");
    });

    dropdown.addEventListener("click", (e) => {
        const item = e.target.closest(".tag-autocomplete-item");
        if (!item) return;
        const tag = item.dataset.tag;
        const current = getTagsFn();
        if (!current.includes(tag)) {
            setTagsFn([...current, tag]);
            render();
        }
        input.value = "";
        dropdown.classList.remove("visible");
    });

    input.addEventListener("keydown", (e) => {
        if (e.key === "Enter" || e.key === ",") {
            e.preventDefault();
            const val = input.value.replace(",", "").trim().toLowerCase();
            if (val && !getTagsFn().includes(val)) {
                setTagsFn([...getTagsFn(), val]);
                render();
            }
            input.value = "";
            dropdown.classList.remove("visible");
        }
        if (e.key === "Backspace" && !input.value) {
            const tags = getTagsFn();
            if (tags.length > 0) {
                setTagsFn(tags.slice(0, -1));
                render();
            }
        }
    });

    document.addEventListener("click", (e) => {
        if (!container.contains(e.target)) {
            dropdown.classList.remove("visible");
        }
    });

    return { render };
}

// === Company Autocomplete ===
function setupCompanyAutocomplete(inputId, dropdownId) {
    const input = document.getElementById(inputId);
    const dropdown = document.getElementById(dropdownId);

    input.addEventListener("input", () => {
        const val = input.value.toLowerCase().trim();
        if (!val) {
            dropdown.classList.remove("visible");
            return;
        }
        const matches = allCompanies.filter(c => c.toLowerCase().includes(val));
        if (matches.length === 0) {
            dropdown.classList.remove("visible");
            return;
        }
        dropdown.innerHTML = matches.map(c =>
            `<div class="company-autocomplete-item" data-company="${esc(c)}">${esc(c)}</div>`
        ).join("");
        dropdown.classList.add("visible");
    });

    dropdown.addEventListener("click", (e) => {
        const item = e.target.closest(".company-autocomplete-item");
        if (!item) return;
        input.value = item.dataset.company;
        dropdown.classList.remove("visible");
    });

    document.addEventListener("click", (e) => {
        if (!input.parentElement.contains(e.target)) {
            dropdown.classList.remove("visible");
        }
    });
}

setupCompanyAutocomplete("company", "company-autocomplete");
setupCompanyAutocomplete("edit-company", "edit-company-autocomplete");

// === Escape HTML ===
function esc(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
}

// === Format Date ===
function formatDate(isoStr) {
    const d = new Date(isoStr);
    return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

function getMonthKey(isoStr) {
    const d = new Date(isoStr);
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
}

function getMonthLabel(key) {
    const [year, month] = key.split("-");
    const d = new Date(parseInt(year), parseInt(month) - 1);
    return d.toLocaleDateString("en-US", { month: "long", year: "numeric" });
}

// === Render Achievements ===
const expandedMonths = new Set();
let firstLoad = true;

function renderAchievements(achievements) {
    const list = document.getElementById("achievements-list");

    if (achievements.length === 0) {
        list.innerHTML = '<div class="loading">No achievements yet. Add your first one above!</div>';
        return;
    }

    // Group by month
    const groups = new Map();
    for (const a of achievements) {
        const key = getMonthKey(a.created_at);
        if (!groups.has(key)) groups.set(key, []);
        groups.get(key).push(a);
    }

    // On first load, expand the most recent month
    if (firstLoad && groups.size > 0) {
        const firstKey = groups.keys().next().value;
        expandedMonths.add(firstKey);
        firstLoad = false;
    }

    list.innerHTML = Array.from(groups.entries()).map(([monthKey, items]) => {
        const expanded = expandedMonths.has(monthKey);
        return `
            <div class="month-group">
                <div class="month-header" data-month="${monthKey}">
                    <span class="chevron ${expanded ? "" : "collapsed"}">&#9660;</span>
                    <span>${getMonthLabel(monthKey)}</span>
                    <span class="count">(${items.length})</span>
                </div>
                <div class="month-items ${expanded ? "" : "collapsed"}" data-month-items="${monthKey}">
                    ${items.map(a => renderCard(a)).join("")}
                </div>
            </div>
        `;
    }).join("");

    // Month header click handlers
    list.querySelectorAll(".month-header").forEach(header => {
        header.addEventListener("click", () => {
            const key = header.dataset.month;
            const items = document.querySelector(`[data-month-items="${key}"]`);
            const chevron = header.querySelector(".chevron");
            if (expandedMonths.has(key)) {
                expandedMonths.delete(key);
                items.classList.add("collapsed");
                chevron.classList.add("collapsed");
            } else {
                expandedMonths.add(key);
                items.classList.remove("collapsed");
                chevron.classList.remove("collapsed");
            }
        });
    });

    // Card action handlers
    list.querySelectorAll("[data-action]").forEach(btn => {
        btn.addEventListener("click", (e) => {
            e.stopPropagation();
            const action = btn.dataset.action;
            const id = parseInt(btn.dataset.id);
            if (action === "edit") openEditModal(id);
            else if (action === "archive") toggleArchive(id);
            else if (action === "unarchive") toggleArchive(id);
            else if (action === "promote") openPromoteModal(id);
        });
    });
}

function renderCard(a) {
    const archivedClass = a.archived ? "archived" : "";
    const promotedBadge = a.notion_page_id
        ? '<span class="promoted-badge">&#10003; Promoted</span>'
        : "";

    const resultHtml = a.result
        ? `<div class="field"><span class="field-label">Result</span><div class="field-value">${esc(a.result)}</div></div>`
        : "";

    const tagsHtml = a.tags.length > 0
        ? `<div class="field"><span class="field-label">Tags</span><div class="tags">${a.tags.map(t => `<span class="tag">${esc(t)}</span>`).join("")}</div></div>`
        : "";

    const actions = a.archived
        ? `<button class="btn btn-secondary btn-sm" data-action="unarchive" data-id="${a.id}">Unarchive</button>`
        : `<button class="btn btn-secondary btn-sm" data-action="edit" data-id="${a.id}">Edit</button>
           <button class="btn btn-secondary btn-sm" data-action="archive" data-id="${a.id}">Archive</button>
           ${features.notion ? `<button class="btn btn-secondary btn-sm" data-action="promote" data-id="${a.id}" ${a.notion_page_id ? "disabled" : ""}>Promote to Notion</button>` : ""}
           ${promotedBadge}`;

    const titleHtml = a.title
        ? `<div class="card-title">${esc(a.title)}</div>`
        : "";

    return `
        <div class="achievement-card ${archivedClass}">
            <div class="date">${formatDate(a.created_at)}${a.company ? " &middot; " + esc(a.company) : ""}</div>
            ${titleHtml}
            <div class="field">
                <span class="field-label">Situation</span>
                <div class="field-value">${esc(a.situation)}</div>
            </div>
            <div class="field">
                <span class="field-label">What I did</span>
                <div class="field-value">${esc(a.action)}</div>
            </div>
            ${resultHtml}
            ${tagsHtml}
            <div class="actions">${actions}</div>
        </div>
    `;
}

// === Load Data ===
async function loadFeatures() {
    features = await api("GET", "/config/features");
    document.getElementById("suggest-tags-btn").style.display = features.ai_tags ? "" : "none";
    document.getElementById("suggest-title-btn").style.display = features.ai_tags ? "" : "none";
}

async function loadTags() {
    allTags = await api("GET", "/tags");
    // Update filter dropdown
    const select = document.getElementById("tag-filter");
    const currentVal = select.value;
    select.innerHTML = '<option value="">All tags</option>' +
        allTags.map(t => `<option value="${esc(t.tag)}">${esc(t.tag)} (${t.count})</option>`).join("");
    select.value = currentVal;
}

async function loadCompanies() {
    allCompanies = await api("GET", "/companies");
    const select = document.getElementById("company-filter");
    const currentVal = select.value;
    select.innerHTML = '<option value="">All companies</option>' +
        allCompanies.map(c => `<option value="${esc(c)}">${esc(c)}</option>`).join("");
    select.value = currentVal;
}

async function loadAchievements() {
    const q = document.getElementById("search-input").value || undefined;
    const tag = document.getElementById("tag-filter").value || undefined;
    const company = document.getElementById("company-filter").value || undefined;
    const dateFrom = document.getElementById("date-from").value || undefined;
    const dateTo = document.getElementById("date-to").value || undefined;
    const archived = document.getElementById("show-archived").checked;

    let query = "?";
    if (q) query += `q=${encodeURIComponent(q)}&`;
    if (tag) query += `tags=${encodeURIComponent(tag)}&`;
    if (company) query += `company=${encodeURIComponent(company)}&`;
    if (dateFrom) query += `date_from=${dateFrom}&`;
    if (dateTo) query += `date_to=${dateTo}&`;
    if (archived) query += `archived=true&`;

    const achievements = await api("GET", `/achievements${query}`);
    renderAchievements(achievements);
}

// === Create Achievement ===
const mainTagInput = createTagInput(
    "tag-input-container", "tag-chips", "tag-input", "tag-autocomplete",
    () => currentFormTags,
    (tags) => { currentFormTags = tags; }
);

document.getElementById("achievement-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const title = document.getElementById("title").value.trim() || null;
    const company = document.getElementById("company").value.trim() || null;
    const situation = document.getElementById("situation").value.trim();
    const action = document.getElementById("action").value.trim();
    const result = document.getElementById("result").value.trim() || null;

    try {
        await api("POST", "/achievements", { title, company, situation, action, result, tags: currentFormTags });
        showToast("Achievement saved!");
        document.getElementById("achievement-form").reset();
        currentFormTags = [];
        mainTagInput.render();
        document.getElementById("suggested-tags").innerHTML = "";
        await Promise.all([loadAchievements(), loadTags(), loadCompanies()]);
    } catch (err) {
        showToast(err.message, true);
    }
});

// === Suggest Tags ===
document.getElementById("suggest-tags-btn").addEventListener("click", async () => {
    const btn = document.getElementById("suggest-tags-btn");
    const situation = document.getElementById("situation").value.trim();
    const action = document.getElementById("action").value.trim();
    const result = document.getElementById("result").value.trim() || null;

    if (!situation && !action) {
        showToast("Add a situation or action first", true);
        return;
    }

    btn.disabled = true;
    btn.textContent = "Suggesting...";

    try {
        const data = await api("POST", "/suggest-tags", { situation, action, result });

        const container = document.getElementById("suggested-tags");
        const newSuggestions = data.suggested_tags.filter(t => !currentFormTags.includes(t));

        if (newSuggestions.length === 0) {
            container.innerHTML = "";
            showToast("No new tag suggestions");
            return;
        }

        container.innerHTML = newSuggestions.map(tag =>
            `<span class="suggested-tag" data-tag="${esc(tag)}">
                + ${esc(tag)}
                <span class="dismiss">&times;</span>
            </span>`
        ).join("");

        container.querySelectorAll(".suggested-tag").forEach(el => {
            el.addEventListener("click", (e) => {
                if (e.target.classList.contains("dismiss")) {
                    el.remove();
                    return;
                }
                const tag = el.dataset.tag;
                if (!currentFormTags.includes(tag)) {
                    currentFormTags.push(tag);
                    mainTagInput.render();
                }
                el.remove();
            });
        });
    } catch (err) {
        showToast(err.message, true);
    } finally {
        btn.disabled = false;
        btn.textContent = "Suggest Tags";
    }
});

// === Suggest Title ===
document.getElementById("suggest-title-btn").addEventListener("click", async () => {
    const btn = document.getElementById("suggest-title-btn");
    const situation = document.getElementById("situation").value.trim();
    const action = document.getElementById("action").value.trim();
    const result = document.getElementById("result").value.trim() || null;

    if (!situation && !action) {
        showToast("Add a situation or action first", true);
        return;
    }

    btn.disabled = true;
    btn.textContent = "Suggesting...";

    try {
        const data = await api("POST", "/suggest-title", { situation, action, result });
        if (data.suggested_title) {
            document.getElementById("title").value = data.suggested_title;
        } else {
            showToast("No title suggestion returned");
        }
    } catch (err) {
        showToast(err.message, true);
    } finally {
        btn.disabled = false;
        btn.textContent = "Suggest Title";
    }
});

// === Archive ===
async function toggleArchive(id) {
    try {
        await api("PATCH", `/achievements/${id}/archive`);
        showToast("Updated");
        await loadAchievements();
    } catch (err) {
        showToast(err.message, true);
    }
}

// === Edit Modal ===
const editTagInput = createTagInput(
    "edit-tag-input-container", "edit-tag-chips", "edit-tag-input", "edit-tag-autocomplete",
    () => editFormTags,
    (tags) => { editFormTags = tags; }
);

async function openEditModal(id) {
    const a = await api("GET", `/achievements/${id}`);
    document.getElementById("edit-id").value = a.id;
    document.getElementById("edit-title").value = a.title || "";
    document.getElementById("edit-company").value = a.company || "";
    document.getElementById("edit-situation").value = a.situation;
    document.getElementById("edit-action").value = a.action;
    document.getElementById("edit-result").value = a.result || "";
    editFormTags = [...a.tags];
    editTagInput.render();
    document.getElementById("edit-modal").classList.add("visible");
}

function closeEditModal() {
    document.getElementById("edit-modal").classList.remove("visible");
}

document.getElementById("edit-modal-close").addEventListener("click", closeEditModal);
document.getElementById("edit-cancel-btn").addEventListener("click", closeEditModal);

document.getElementById("edit-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const id = document.getElementById("edit-id").value;
    const title = document.getElementById("edit-title").value.trim() || null;
    const company = document.getElementById("edit-company").value.trim() || null;
    const situation = document.getElementById("edit-situation").value.trim();
    const action = document.getElementById("edit-action").value.trim();
    const result = document.getElementById("edit-result").value.trim() || null;

    try {
        await api("PUT", `/achievements/${id}`, { title, company, situation, action, result, tags: editFormTags });
        showToast("Achievement updated!");
        closeEditModal();
        await Promise.all([loadAchievements(), loadTags(), loadCompanies()]);
    } catch (err) {
        showToast(err.message, true);
    }
});

document.getElementById("edit-delete-btn").addEventListener("click", async () => {
    if (!confirm("Delete this achievement? This cannot be undone.")) return;
    const id = document.getElementById("edit-id").value;
    try {
        await api("DELETE", `/achievements/${id}`);
        showToast("Achievement deleted");
        closeEditModal();
        await Promise.all([loadAchievements(), loadTags(), loadCompanies()]);
    } catch (err) {
        showToast(err.message, true);
    }
});

// === Promote Modal ===
async function openPromoteModal(id) {
    const a = await api("GET", `/achievements/${id}`);
    document.getElementById("promote-id").value = a.id;
    document.getElementById("promote-situation").value = a.situation;
    document.getElementById("promote-task").value = "";
    document.getElementById("promote-action").value = a.action;
    document.getElementById("promote-result").value = a.result || "";
    document.getElementById("promote-screenshots").value = "";
    document.getElementById("promote-modal").classList.add("visible");
}

function closePromoteModal() {
    document.getElementById("promote-modal").classList.remove("visible");
}

document.getElementById("promote-modal-close").addEventListener("click", closePromoteModal);
document.getElementById("promote-cancel-btn").addEventListener("click", closePromoteModal);

document.getElementById("promote-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const id = document.getElementById("promote-id").value;
    const situation = document.getElementById("promote-situation").value.trim();
    const task = document.getElementById("promote-task").value.trim();
    const action = document.getElementById("promote-action").value.trim();
    const result = document.getElementById("promote-result").value.trim();

    const submitBtn = e.target.querySelector("[type=submit]");
    submitBtn.disabled = true;
    submitBtn.textContent = "Sending...";

    try {
        // Upload screenshots first
        const files = document.getElementById("promote-screenshots").files;
        for (const file of files) {
            await apiUpload(`/achievements/${id}/screenshots`, file);
        }

        await api("POST", `/achievements/${id}/promote`, { situation, task, action, result });
        showToast("Promoted to Notion!");
        closePromoteModal();
        await loadAchievements();
    } catch (err) {
        showToast(err.message, true);
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = "Send to Notion";
    }
});

// === All Tags Modal ===
document.getElementById("view-all-tags-btn").addEventListener("click", async () => {
    await loadTags();
    const container = document.getElementById("all-tags-list");
    if (allTags.length === 0) {
        container.innerHTML = '<div class="loading">No tags yet</div>';
    } else {
        container.innerHTML = allTags.map(t =>
            `<span class="tag-item" data-tag="${esc(t.tag)}">
                ${esc(t.tag)} <span class="tag-count">${t.count}</span>
            </span>`
        ).join("");

        container.querySelectorAll(".tag-item").forEach(el => {
            el.addEventListener("click", () => {
                document.getElementById("tag-filter").value = el.dataset.tag;
                document.getElementById("tags-modal").classList.remove("visible");
                loadAchievements();
            });
        });
    }
    document.getElementById("tags-modal").classList.add("visible");
});

document.getElementById("tags-modal-close").addEventListener("click", () => {
    document.getElementById("tags-modal").classList.remove("visible");
});

// === Close modals on overlay click ===
document.querySelectorAll(".modal-overlay").forEach(overlay => {
    overlay.addEventListener("click", (e) => {
        if (e.target === overlay) overlay.classList.remove("visible");
    });
});

// === Filter listeners ===
let filterTimeout;
function debouncedLoad() {
    clearTimeout(filterTimeout);
    filterTimeout = setTimeout(loadAchievements, 300);
}

document.getElementById("search-input").addEventListener("input", debouncedLoad);
document.getElementById("tag-filter").addEventListener("change", loadAchievements);
document.getElementById("company-filter").addEventListener("change", loadAchievements);
document.getElementById("date-from").addEventListener("change", loadAchievements);
document.getElementById("date-to").addEventListener("change", loadAchievements);
document.getElementById("show-archived").addEventListener("change", loadAchievements);

// === Theme Toggle ===
function initTheme() {
    const saved = localStorage.getItem("theme");
    const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    const theme = saved || (prefersDark ? "dark" : "light");
    document.documentElement.setAttribute("data-theme", theme);
    // Checkbox checked = light mode (toggle is between Dark and Light)
    document.getElementById("theme-toggle").checked = theme === "light";
}

document.getElementById("theme-toggle").addEventListener("change", (e) => {
    const theme = e.target.checked ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("theme", theme);
});

// === Init ===
function init() {
    initTheme();
    loadFeatures();
    loadTags();
    loadCompanies();
    loadAchievements();
}

init();
