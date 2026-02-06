// Simple page loader + per-page initializers
document.addEventListener("DOMContentLoaded", () => {
  const navBtns = document.querySelectorAll(".nav-btn");

  function setActiveButton(targetKey) {
    navBtns.forEach((b) => {
      const t = b.getAttribute("data-target");
      if (t === targetKey) b.classList.add("active");
      else b.classList.remove("active");
    });
  }

  async function loadPage(key, pushState = true) {
    const app = document.getElementById("app");
    try {
      const res = await fetch(`pages/${key}.html`);
      if (!res.ok) throw new Error(`Failed to load page ${key}`);
      const html = await res.text();
      app.innerHTML = html;
      // ensure any <link> in the fragment is applied (browsers will handle it when injected)
      // remove stale per-page stylesheets
      const existing = document.querySelectorAll("link[data-page-css]");
      existing.forEach((n) => n.remove());
      // relocate any link elements from the injected HTML into head and mark them
      const temp = document.createElement("div");
      temp.innerHTML = html;
      const links = temp.querySelectorAll('link[rel="stylesheet"]');
      links.forEach((lnk) => {
        const href = lnk.getAttribute("href");
        if (href) {
          const linkEl = document.createElement("link");
          linkEl.rel = "stylesheet";
          linkEl.href = href;
          linkEl.setAttribute("data-page-css", key);
          document.head.appendChild(linkEl);
        }
      });
      // re-set innerHTML after extracting links to avoid duplicate tags
      app.innerHTML = html.replace(/<link[^>]+>/gi, "");
      setActiveButton(key);
      if (pushState) history.pushState({ page: key }, "", `#${key}`);
      // call page initializer if exists
      const initName = `init_${key.replace(/-/g, "_")}`;
      if (typeof window[initName] === "function") {
        window[initName]();
      }
    } catch (err) {
      app.innerHTML = `<div style="padding:40px;color:#c0392b">页面加载失败: ${err.message}</div>`;
    }
  }

  // nav button wiring
  navBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      const target = btn.getAttribute("data-target");
      // map old ids to page keys
      const pageKey =
        target === "page-viz" ? "viewer" : target.replace(/^page-/, "");
      loadPage(pageKey);
    });
  });

  // handle back/forward
  window.addEventListener("popstate", (e) => {
    const key =
      (e.state && e.state.page) || location.hash.replace(/^#/, "") || "viewer";
    loadPage(key, false);
  });

  // initial load: use hash or default
  const initial = location.hash.replace(/^#/, "") || "viewer";
  loadPage(initial, false);

  // --- Per-page initializer: viewer ---
  window.init_viewer = function () {
    // attach previous logic but only for elements inside #app
    const root = document.getElementById("app");
    const uploadBtn = root.querySelector("#uploadBtn");
    const filePathDisplay = root.querySelector("#file-path-display");
    const plotImg = root.querySelector("#plot-image");
    const loading = root.querySelector("#loading");
    const errorMsg = root.querySelector("#error-msg");
    const placeholder = root.querySelector("#placeholder");

    const controlPanel = root.querySelector("#control-panel");
    const slider = root.querySelector("#traj-slider");
    const indexLbl = root.querySelector("#traj-index-lbl");
    const totalLbl = root.querySelector("#total-traj-lbl");

    const scaleInput = root.querySelector("#scale-input");
    const zeroStartSwitch = root.querySelector("#zero-start-switch");
    const xUnitInput = root.querySelector("#x-unit-input");
    const yUnitInput = root.querySelector("#y-unit-input");

    const titleInput = root.querySelector("#title-input");
    const markersSwitch = root.querySelector("#markers-switch");
    const showTitleSwitch = root.querySelector("#show-title-switch");
    const showAxisLabelsSwitch = root.querySelector("#show-axis-labels-switch");
    const showGridSwitch = root.querySelector("#show-grid-switch");
    const saveBtn = root.querySelector("#saveBtn");

    let isFileLoaded = false;

    function getPlotParams() {
      return {
        index: parseInt(slider.value) || 0,
        scale: parseFloat(scaleInput.value) || 1.0,
        zero_start: zeroStartSwitch.checked,
        x_unit: xUnitInput.value || "px",
        y_unit: yUnitInput.value || "px",
        custom_title: titleInput ? titleInput.value : "",
        show_markers: markersSwitch ? markersSwitch.checked : true,
        show_title: showTitleSwitch ? showTitleSwitch.checked : true,
        show_axis_labels: showAxisLabelsSwitch
          ? showAxisLabelsSwitch.checked
          : true,
        show_grid: showGridSwitch ? showGridSwitch.checked : true,
      };
    }

    function updatePlot() {
      if (!isFileLoaded) return;
      const params = getPlotParams();
      indexLbl.textContent = params.index + 1;
      if (window.pywebview) {
        window.pywebview.api
          .change_trajectory(
            params.index,
            params.scale,
            params.zero_start,
            params.x_unit,
            params.y_unit,
            params.custom_title,
            params.show_markers,
            params.show_title,
            params.show_axis_labels,
            params.show_grid,
          )
          .then((res) => {
            if (res.image) {
              plotImg.src = res.image;
              errorMsg.style.display = "none";
              plotImg.style.display = "block";
            } else if (res.error) {
              errorMsg.textContent = res.error;
              errorMsg.style.display = "block";
            }
          });
      }
    }

    // wire events
    if (slider) {
      slider.addEventListener("input", () => {
        indexLbl.textContent = parseInt(slider.value) + 1;
      });
      slider.addEventListener("change", updatePlot);
    }
    if (scaleInput) scaleInput.addEventListener("change", updatePlot);
    if (zeroStartSwitch) zeroStartSwitch.addEventListener("change", updatePlot);
    if (xUnitInput) xUnitInput.addEventListener("change", updatePlot);
    if (yUnitInput) yUnitInput.addEventListener("change", updatePlot);
    if (titleInput) titleInput.addEventListener("change", updatePlot);
    if (markersSwitch) markersSwitch.addEventListener("change", updatePlot);
    if (showTitleSwitch) showTitleSwitch.addEventListener("change", updatePlot);
    if (showAxisLabelsSwitch)
      showAxisLabelsSwitch.addEventListener("change", updatePlot);
    if (showGridSwitch) showGridSwitch.addEventListener("change", updatePlot);

    if (uploadBtn)
      uploadBtn.addEventListener("click", () => {
        if (!window.pywebview) {
          alert("请在 Pywebview 环境下运行！");
          return;
        }
        placeholder.style.display = "none";
        plotImg.style.display = "none";
        errorMsg.style.display = "none";
        loading.style.display = "block";

        window.pywebview.api
          .process_file_dialog()
          .then((res) => {
            loading.style.display = "none";
            if (res.cancelled) {
              if (!isFileLoaded) placeholder.style.display = "flex";
              return;
            }
            if (res.error) {
              errorMsg.textContent = "错误: " + res.error;
              errorMsg.style.display = "block";
              filePathDisplay.textContent = "读取失败";
              isFileLoaded = false;
            } else {
              isFileLoaded = true;
              filePathDisplay.textContent = res.file_path.split(/[/\\]/).pop();
              if (res.total_trajs > 0) {
                controlPanel.style.display = "flex";
                slider.max = res.total_trajs - 1;
                slider.value = 0;
                indexLbl.textContent = "1";
                totalLbl.textContent = `/ 共 ${res.total_trajs} 条`;
                updatePlot();
              }
            }
          })
          .catch((err) => {
            loading.style.display = "none";
            errorMsg.textContent = "系统异常: " + err;
            errorMsg.style.display = "block";
          });
      });

    if (saveBtn)
      saveBtn.addEventListener("click", () => {
        if (!isFileLoaded) {
          alert("请先加载数据！");
          return;
        }
        const params = getPlotParams();
        const originalText = saveBtn.innerHTML;
        saveBtn.innerHTML = "<span>⏳</span> 保存中...";
        saveBtn.disabled = true;
        if (window.pywebview) {
          window.pywebview.api.save_plot(params).then((res) => {
            saveBtn.innerHTML = originalText;
            saveBtn.disabled = false;
            if (res.success) {
              alert("保存成功！\n路径: " + res.path);
            } else if (res.error) {
              alert("保存失败: " + res.error);
            }
          });
        }
      });
  };
});
