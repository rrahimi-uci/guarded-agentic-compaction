const menu = document.querySelector("[data-menu]");
const links = document.querySelector("[data-nav-links]");

if (menu && links) {
  menu.addEventListener("click", () => {
    const open = links.dataset.open === "true";
    links.dataset.open = String(!open);
    menu.setAttribute("aria-expanded", String(!open));
  });
}

document.querySelectorAll("pre").forEach((block) => {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "copy-code";
  button.textContent = "Copy";
  button.setAttribute("aria-label", "Copy code block");
  button.addEventListener("click", async () => {
    await navigator.clipboard.writeText(block.innerText.replace("Copy", "").trim());
    button.textContent = "Copied";
    window.setTimeout(() => { button.textContent = "Copy"; }, 1400);
  });
  block.appendChild(button);
});

const style = document.createElement("style");
style.textContent =
  ".copy-code{position:absolute;top:.65rem;right:.65rem;padding:.3rem .55rem;" +
  "border:1px solid rgba(255,255,255,.22);border-radius:6px;color:rgba(255,255,255,.72);" +
  "background:rgba(255,255,255,.07);font:600 .68rem/1 sans-serif;cursor:pointer}" +
  ".copy-code:hover{color:white;background:rgba(255,255,255,.14)}";
document.head.appendChild(style);
