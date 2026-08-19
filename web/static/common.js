/* 公共工具：会话管理、API 封装、渲染辅助 */

const App = {
  // ---- 会话（机制一的版本分配依据）----
  getSession() {
    let s = localStorage.getItem("oj_session_id");
    if (!s) {
      s = "web-" + crypto.randomUUID();
      localStorage.setItem("oj_session_id", s);
    }
    return s;
  },
  resetSession() {
    const s = "web-" + crypto.randomUUID();
    localStorage.setItem("oj_session_id", s);
    return s;
  },

  // ---- API ----
  async api(path, opts = {}) {
    const r = await fetch(path, opts);
    if (!r.ok) {
      let msg = r.statusText;
      try { msg = (await r.json()).detail || msg; } catch (e) {}
      throw new Error(msg);
    }
    return r.json();
  },
  async post(path, body) {
    return App.api(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  },

  // ---- 渲染辅助 ----
  esc(s) {
    return String(s ?? "").replace(/[&<>"']/g, c => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
    }[c]));
  },
  // 轻量 LaTeX 子集渲染（覆盖题库记号，无需 KaTeX/MathJax，离线可用）
  latexMath(latex) {
    const CMD = {
      "\\leq": "≤", "\\geq": "≥", "\\neq": "≠",
      "\\le": "≤", "\\ge": "≥", "\\ne": "≠", "\\lt": "<", "\\gt": ">",
      "\\times": "×", "\\cdot": "·", "\\ldots": "…", "\\dots": "…",
      "\\sim": "～", "\\infty": "∞", "\\pm": "±", "\\to": "→",
    };
    let s = latex;
    // 长命令优先替换，避免 \le 吃掉 \leq 之类前缀冲突
    for (const k of Object.keys(CMD).sort((a, b) => b.length - a.length)) {
      s = s.split(k).join(CMD[k]);
    }
    // 上下标：a_{ij} / a_i / 10^{9} / 10^9
    s = s.replace(/([_^])\{([^{}]*)\}/g, (m, op, body) =>
      op === "_" ? `<sub>${body}</sub>` : `<sup>${body}</sup>`);
    s = s.replace(/([_^])([A-Za-z0-9])/g, (m, op, ch) =>
      op === "_" ? `<sub>${ch}</sub>` : `<sup>${ch}</sup>`);
    return s;
  },
  // 极简 markdown：$数学$、`code`、**bold**
  md(s) {
    let t = App.esc(s);
    t = t.replace(/\$([^$]+)\$/g, (m, inner) => App.latexMath(inner));
    t = t.replace(/`([^`]+)`/g, "<code>$1</code>");
    t = t.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
    return t;
  },
  badgeVerdict(v) {
    return `<span class="badge verdict-${App.esc(v)}">${App.esc(v)}</span>`;
  },
  badgeDifficulty(d) {
    const cls = d === "easy" ? "easy" : "medium";
    const name = d === "easy" ? "入门" : "中档";
    return `<span class="badge ${cls}">${name}</span>`;
  },
  timeAgo(ts) {
    const dt = Date.now() / 1000 - ts;
    if (dt < 60) return Math.max(0, Math.floor(dt)) + " 秒前";
    if (dt < 3600) return Math.floor(dt / 60) + " 分钟前";
    if (dt < 86400) return Math.floor(dt / 3600) + " 小时前";
    return new Date(ts * 1000).toLocaleString("zh-CN");
  },
  toast(msg, ms = 2400) {
    let el = document.getElementById("toast");
    if (!el) {
      el = document.createElement("div"); el.id = "toast";
      document.body.appendChild(el);
    }
    el.textContent = msg;
    el.classList.add("show");
    clearTimeout(el._t);
    el._t = setTimeout(() => el.classList.remove("show"), ms);
  },
  qs(name) {
    return new URLSearchParams(location.search).get(name);
  },
};

// 顶部导航（每页引入）
function renderNav(active) {
  const session = App.getSession();
  const links = [
    ["index.html", "题目列表", "problems"],
    ["submissions.html", "提交记录", "submissions"],
    ["experiment.html", "实验数据", "experiment"],
  ].map(([href, label, key]) =>
    `<a href="${href}" class="${key === active ? "active" : ""}">${label}</a>`).join("");
  document.body.insertAdjacentHTML("afterbegin", `
    <nav class="nav">
      <div class="logo"><span class="dot"></span>OJ-Anti-AI 评测系统</div>
      ${links}
      <div class="spacer"></div>
      <div class="session">会话 ${App.esc(session.slice(0, 18))}</div>
    </nav>`);
}
