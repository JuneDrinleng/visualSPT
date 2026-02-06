// Simple page loader + per-page initializers
document.addEventListener("DOMContentLoaded", () => {
  const navBtns = document.querySelectorAll(".nav-btn");

  // Custom titlebar buttons (shell-level)
  const minBtn = document.getElementById("min-btn");
  const closeBtn = document.getElementById("close-btn");

  if (minBtn) {
    minBtn.addEventListener("click", () => {
      if (window.pywebview) window.pywebview.api.minimize_window();
      else window.minimize && window.minimize();
    });
  }
  if (closeBtn) {
    closeBtn.addEventListener("click", () => {
      // hide instead of close
      if (window.pywebview) window.pywebview.api.hide_window();
      else window.close && window.close();
    });
  }

  function setActiveButton(targetKey) {
    navBtns.forEach((b) => {
      const t = b.getAttribute("data-target");
      // Map data-target to page key for comparison
      const pageKey = t.replace(/^page-/, "");
      if (pageKey === targetKey) b.classList.add("active");
      else b.classList.remove("active");
    });
  }

  let _currentPage = null;

  async function loadPage(key, pushState = true) {
    if (key === _currentPage) return;
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
      // Re-initialize Lucide icons in dynamically loaded content
      if (typeof lucide !== "undefined") lucide.createIcons();
      setActiveButton(key);
      _currentPage = key;
      if (pushState) history.pushState({ page: key }, "", `#${key}`);
      // call page initializer if exists
      const initName = `init_${key.replace(/-/g, "_")}`;
      if (typeof window[initName] === "function") {
        window[initName]();
      }
    } catch (err) {
      app.innerHTML = `<div style="padding:40px;color:#c0392b">Failed to load page: ${err.message}</div>`;
    }
  }

  // nav button wiring
  navBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      const target = btn.getAttribute("data-target");
      // map old ids to page keys
      const pageKey = target.replace(/^page-/, "");
      loadPage(pageKey);
    });
  });

  // handle back/forward
  window.addEventListener("popstate", (e) => {
    const key =
      (e.state && e.state.page) ||
      location.hash.replace(/^#/, "") ||
      "traj-viewer";
    loadPage(key, false);
  });

  // initial load: use hash or default
  const initial = location.hash.replace(/^#/, "") || "traj-viewer";
  loadPage(initial, false);

  // --- Per-page initializer: traj-viewer ---
  window.init_traj_viewer = function () {
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
    const fpsInput = root.querySelector("#fps-input");
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
        fps: fpsInput ? parseInt(fpsInput.value) || 20 : 20,
        zero_start: zeroStartSwitch ? zeroStartSwitch.checked : false,
        x_unit: xUnitInput ? xUnitInput.value || "px" : "px",
        y_unit: yUnitInput ? yUnitInput.value || "px" : "px",
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
        // show loading indicator while backend generates the image
        loading.style.display = "block";
        plotImg.style.display = "none";
        errorMsg.style.display = "none";
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
            loading.style.display = "none";
            if (res.image) {
              plotImg.src = res.image;
              errorMsg.style.display = "none";
              plotImg.style.display = "block";
            } else if (res.error) {
              errorMsg.textContent = res.error;
              errorMsg.style.display = "block";
            }
          })
          .catch((err) => {
            loading.style.display = "none";
            errorMsg.textContent = "System error: " + err;
            errorMsg.style.display = "block";
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
          alert("Please run in the Pywebview environment!");
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
              errorMsg.textContent = "Error: " + res.error;
              errorMsg.style.display = "block";
              filePathDisplay.textContent = "Failed to read";
              isFileLoaded = false;
            } else {
              isFileLoaded = true;
              filePathDisplay.textContent = res.file_path.split(/[/\\]/).pop();
              if (res.total_trajs > 0) {
                controlPanel.style.display = "flex";
                slider.max = res.total_trajs - 1;
                slider.value = 0;
                indexLbl.textContent = "1";
                totalLbl.textContent = `/ ${res.total_trajs} total`;
                updatePlot();
              }
            }
          })
          .catch((err) => {
            loading.style.display = "none";
            errorMsg.textContent = "System error: " + err;
            errorMsg.style.display = "block";
          });
      });

    if (saveBtn)
      saveBtn.addEventListener("click", () => {
        if (!isFileLoaded) {
          alert("Please load data first!");
          return;
        }
        const params = getPlotParams();
        const originalText = saveBtn.innerHTML;
        saveBtn.innerHTML = "<span>⏳</span> Saving...";
        saveBtn.disabled = true;
        if (window.pywebview) {
          window.pywebview.api.save_plot(params).then((res) => {
            saveBtn.innerHTML = originalText;
            saveBtn.disabled = false;
            if (res.success) {
              alert("Saved successfully!\nPath: " + res.path);
            } else if (res.error) {
              alert("Save failed: " + res.error);
            }
          });
        }
      });
  };

  // --- Per-page initializer: activate-traj (dynamic/activation visualization) ---
  window.init_activate_traj = function () {
    // reuse viewer wiring but call activation API
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
    const fpsInput = root.querySelector("#fps-input");
    const trailLenInput = root.querySelector("#trail-len-input");
    const zeroStartSwitch = root.querySelector("#zero-start-switch");
    const xUnitInput = root.querySelector("#x-unit-input");
    const yUnitInput = root.querySelector("#y-unit-input");

    const titleInput = root.querySelector("#title-input");
    const timebarSwitch = root.querySelector("#timebar-switch");
    const showTitleSwitch = root.querySelector("#show-title-switch");
    const showAxisLabelsSwitch = root.querySelector("#show-axis-labels-switch");
    const showGridSwitch = root.querySelector("#show-grid-switch");
    const saveBtn = root.querySelector("#saveBtn");

    let isFileLoaded = false;

    function getPlotParams() {
      return {
        index: parseInt(slider.value) || 0,
        scale: scaleInput ? parseFloat(scaleInput.value) || 1.0 : 1.0,
        fps: fpsInput ? parseInt(fpsInput.value) || 20 : 20,
        trail_len:
          trailLenInput && trailLenInput.value
            ? parseInt(trailLenInput.value)
            : 0,
        zero_start: zeroStartSwitch ? zeroStartSwitch.checked : false,
        x_unit: xUnitInput ? xUnitInput.value || "px" : "px",
        y_unit: yUnitInput ? yUnitInput.value || "px" : "px",
        custom_title: titleInput ? titleInput.value : "",
        show_timebar: timebarSwitch ? timebarSwitch.checked : true,
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
        // show loading indicator while backend generates the animation
        loading.style.display = "block";
        plotImg.style.display = "none";
        errorMsg.style.display = "none";
        window.pywebview.api
          .change_activation(
            params.index,
            1.0, // keep scale default for activation
            params.fps,
            params.trail_len,
            params.zero_start,
            params.x_unit,
            params.y_unit,
            params.custom_title,
            params.show_timebar,
            params.show_title,
            params.show_axis_labels,
            params.show_grid,
          )
          .then((res) => {
            loading.style.display = "none";
            if (res.image) {
              plotImg.src = res.image;
              errorMsg.style.display = "none";
              plotImg.style.display = "block";
            } else if (res.error) {
              errorMsg.textContent = res.error;
              errorMsg.style.display = "block";
            }
          })
          .catch((err) => {
            loading.style.display = "none";
            errorMsg.textContent = "System error: " + err;
            errorMsg.style.display = "block";
          });
      }
    }

    // wire events (same wiring as viewer)
    if (slider) {
      slider.addEventListener("input", () => {
        indexLbl.textContent = parseInt(slider.value) + 1;
      });
      slider.addEventListener("change", updatePlot);
    }
    if (scaleInput) scaleInput.addEventListener("change", updatePlot);
    if (fpsInput) fpsInput.addEventListener("change", updatePlot);
    if (trailLenInput) trailLenInput.addEventListener("change", updatePlot);
    if (zeroStartSwitch) zeroStartSwitch.addEventListener("change", updatePlot);
    if (xUnitInput) xUnitInput.addEventListener("change", updatePlot);
    if (yUnitInput) yUnitInput.addEventListener("change", updatePlot);
    if (titleInput) titleInput.addEventListener("change", updatePlot);
    if (timebarSwitch) timebarSwitch.addEventListener("change", updatePlot);
    if (showTitleSwitch) showTitleSwitch.addEventListener("change", updatePlot);
    if (showAxisLabelsSwitch)
      showAxisLabelsSwitch.addEventListener("change", updatePlot);
    if (showGridSwitch) showGridSwitch.addEventListener("change", updatePlot);

    if (uploadBtn)
      uploadBtn.addEventListener("click", () => {
        if (!window.pywebview) {
          alert("Please run in the Pywebview environment!");
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
              errorMsg.textContent = "Error: " + res.error;
              errorMsg.style.display = "block";
              filePathDisplay.textContent = "Failed to read";
              isFileLoaded = false;
            } else {
              isFileLoaded = true;
              filePathDisplay.textContent = res.file_path.split(/[/\\]/).pop();
              if (res.total_trajs > 0) {
                controlPanel.style.display = "flex";
                slider.max = res.total_trajs - 1;
                slider.value = 0;
                indexLbl.textContent = "1";
                totalLbl.textContent = `/ ${res.total_trajs} total`;
                updatePlot();
              }
            }
          })
          .catch((err) => {
            loading.style.display = "none";
            errorMsg.textContent = "System error: " + err;
            errorMsg.style.display = "block";
          });
      });

    if (saveBtn)
      saveBtn.addEventListener("click", () => {
        if (!isFileLoaded) {
          alert("Please load data first!");
          return;
        }
        const params = getPlotParams();
        const originalText = saveBtn.innerHTML;
        saveBtn.innerHTML = "<span>⏳</span> Saving...";
        saveBtn.disabled = true;
        if (window.pywebview) {
          window.pywebview.api.save_plot(params).then((res) => {
            saveBtn.innerHTML = originalText;
            saveBtn.disabled = false;
            if (res.success) {
              alert("Saved successfully!\nPath: " + res.path);
            } else if (res.error) {
              alert("Save failed: " + res.error);
            }
          });
        }
      });
  };
});
