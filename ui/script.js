
document.addEventListener("DOMContentLoaded", () => {

  var windowFrame = document.getElementById("windowFrame");
  if (windowFrame) {
    windowFrame.style.display = "";
  }

  function trackLoadingProgress() {
    const progressBar = document.querySelector(
      "#loadingOverlay .loading-progress-bar",
    );
    const loadingText = document.getElementById("loadingText");
    const loadingSubtext = document.getElementById("loadingSubtext");
    let lastProgress = 0;

    const poll = setInterval(() => {
      if (
        !window.pywebview ||
        !window.pywebview.api ||
        !window.pywebview.api.get_loading_progress
      ) {

        if (progressBar) progressBar.style.width = "3%";
        return;
      }

      window.pywebview.api
        .get_loading_progress()
        .then((res) => {
          if (!res) return;
          const pct = Math.max(lastProgress, res.progress || 0);
          lastProgress = pct;

          if (progressBar) progressBar.style.width = pct + "%";
          if (loadingSubtext && res.stage)
            loadingSubtext.textContent = res.stage;

          if (res.done || pct >= 100) {
            clearInterval(poll);

            if (progressBar) progressBar.style.width = "100%";
            if (loadingText) loadingText.textContent = "Ready";
            if (loadingSubtext) loadingSubtext.textContent = "";

            setTimeout(() => {
              const overlay = document.getElementById("loadingOverlay");
              if (overlay) {
                overlay.classList.add("fade-out");
                setTimeout(() => {
                  overlay.remove();

                  if (typeof window.checkForUpdates === "function") {
                    window.checkForUpdates(true);
                  }
                }, 250);
              }
            }, 200);
            console.log("[UI] Libraries ready, overlay removed");
          }
        })
        .catch(() => {});
    }, 150);

    setTimeout(() => {
      clearInterval(poll);
      const overlay = document.getElementById("loadingOverlay");
      if (overlay) {
        overlay.classList.add("fade-out");
        setTimeout(() => {
          overlay.remove();
          if (typeof window.checkForUpdates === "function") {
            window.checkForUpdates(true);
          }
        }, 250);
        console.log("[UI] Timeout, overlay removed");
      }
    }, 10000);
  }
  trackLoadingProgress();

  const navBtns = document.querySelectorAll(".nav-btn");

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

      if (window.pywebview) window.pywebview.api.hide_window();
      else window.close && window.close();
    });
  }

  function setActiveButton(targetKey) {
    navBtns.forEach((b) => {
      const t = b.getAttribute("data-target");

      const pageKey = t.replace(/^page-/, "");
      if (pageKey === targetKey) b.classList.add("active");
      else b.classList.remove("active");
    });
    updateNavIndicator();
  }

  function updateNavIndicator() {
    const sidebar = document.querySelector(".sidebar");
    const activeBtn = document.querySelector(".nav-btn.active");

    if (sidebar && activeBtn) {
      const top = activeBtn.offsetTop;
      const height = activeBtn.offsetHeight;
      sidebar.style.setProperty("--nav-indicator-top", `${top}px`);
      sidebar.style.setProperty("--nav-indicator-height", `${height}px`);
    }
  }

  let _currentPage = null;
  const _initializedPages = new Set();

  function _injectPageCSS(html, key) {
    if (document.querySelector(`link[data-page-css="${key}"]`)) return;
    const temp = document.createElement("div");
    temp.innerHTML = html;
    temp.querySelectorAll('link[rel="stylesheet"]').forEach((lnk) => {
      const href = lnk.getAttribute("href");
      if (!href) return;
      const el = document.createElement("link");
      el.rel = "stylesheet";
      el.href = href;
      el.setAttribute("data-page-css", key);
      document.head.appendChild(el);
    });
  }

  async function _preloadPages() {
    const pageKeys = ["traj-viewer", "activate-traj", "msd-viewer", "settings", "others"];
    const app = document.getElementById("app");
    await Promise.all(
      pageKeys.map(async (key) => {
        try {
          const res = await fetch(`pages/${key}.html`);
          if (!res.ok) throw new Error(`HTTP ${res.status}`);
          const html = await res.text();
          _injectPageCSS(html, key);

          const linkStripped = html.replace(/<link[^>]+>/gi, "");
          const tempDiv = document.createElement("div");
          tempDiv.innerHTML = linkStripped;
          const scriptDefs = Array.from(tempDiv.querySelectorAll("script")).map((s) => ({
            text: s.textContent,
            attrs: Array.from(s.attributes),
          }));

          const cleanHtml = linkStripped.replace(
            /<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi,
            "",
          );
          const container = document.createElement("div");
          container.id = `page-${key}`;
          container.className = "page-root";
          container.innerHTML = cleanHtml;

          app.appendChild(container);

          scriptDefs.forEach(({ text, attrs }) => {
            const s = document.createElement("script");
            attrs.forEach((a) => s.setAttribute(a.name, a.value));
            s.textContent = text;
            container.appendChild(s);
          });
        } catch (err) {
          console.error(`[page] Failed to preload ${key}:`, err);
        }
      })
    );
    if (typeof lucide !== "undefined") lucide.createIcons();
  }

  function switchPage(key, pushState = true) {
    if (key === _currentPage) return;

    if (_currentPage) {
      const prev = document.getElementById(`page-${_currentPage}`);
      if (prev) {
        if (typeof prev._cleanup === "function") prev._cleanup();
        prev.style.display = "none";
      }
    }

    const container = document.getElementById(`page-${key}`);
    if (!container) {
      console.warn(`[page] container not found: ${key}`);
      return;
    }

    container.style.display = "flex";

    if (!_initializedPages.has(key)) {
      _initializedPages.add(key);
      const initFn = window[`init_${key.replace(/-/g, "_")}`];
      if (typeof initFn === "function") initFn(container);
    }

    setActiveButton(key);
    updateNavIndicator();
    _currentPage = key;
    if (pushState) history.pushState({ page: key }, "", `#${key}`);
  }

  navBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      const pageKey = btn.getAttribute("data-target").replace(/^page-/, "");
      switchPage(pageKey);
    });
  });

  window.addEventListener("popstate", (e) => {
    const key =
      (e.state && e.state.page) ||
      location.hash.replace(/^#/, "") ||
      "traj-viewer";
    switchPage(key, false);
  });

  updateNavIndicator();
  const initial = location.hash.replace(/^#/, "") || "traj-viewer";
  _preloadPages().then(() => switchPage(initial, false));

  window.init_traj_viewer = function (root) {
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
    const unitInput = root.querySelector("#unit-input");
    const fpsInput = root.querySelector("#fps-input");
    const zeroStartSwitch = root.querySelector("#zero-start-switch");

    const titleInput = root.querySelector("#title-input");
    const markersSwitch = root.querySelector("#markers-switch");
    const showTitleSwitch = root.querySelector("#show-title-switch");
    const showAxisLabelsSwitch = root.querySelector("#show-axis-labels-switch");
    const showGridSwitch = root.querySelector("#show-grid-switch");
    const showColorbarSwitch = root.querySelector("#show-colorbar-switch");
    const showTicksSwitch = root.querySelector("#show-ticks-switch");
    const showBorderSwitch = root.querySelector("#show-border-switch");
    const saveBtn = root.querySelector("#saveBtn");
    const batchSaveBtn = root.querySelector("#batchSaveBtn");

    let isFileLoaded = false;

    function getPlotParams() {
      const unit = unitInput ? unitInput.value || "px" : "px";
      return {
        index: parseInt(slider.value) || 0,
        scale: parseFloat(scaleInput.value) || 1.0,
        fps: fpsInput ? parseInt(fpsInput.value) || 20 : 20,
        zero_start: zeroStartSwitch ? zeroStartSwitch.checked : false,
        x_unit: unit,
        y_unit: unit,
        custom_title: titleInput ? titleInput.value : "",
        show_markers: markersSwitch ? markersSwitch.checked : true,
        show_title: showTitleSwitch ? showTitleSwitch.checked : true,
        show_axis_labels: showAxisLabelsSwitch
          ? showAxisLabelsSwitch.checked
          : true,
        show_grid: showGridSwitch ? showGridSwitch.checked : true,
        show_colorbar: showColorbarSwitch ? showColorbarSwitch.checked : true,
        show_ticks: showTicksSwitch ? showTicksSwitch.checked : true,
        show_border: showBorderSwitch ? showBorderSwitch.checked : true,
      };
    }

    function updatePlot() {
      if (!isFileLoaded) return;
      const params = getPlotParams();
      indexLbl.textContent = params.index + 1;
      if (window.pywebview) {

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
            params.show_colorbar,
            params.show_ticks,
            params.show_border,
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

    if (slider) {
      slider.addEventListener("input", () => {
        indexLbl.textContent = parseInt(slider.value) + 1;
      });
      slider.addEventListener("change", updatePlot);
    }
    if (scaleInput) scaleInput.addEventListener("change", updatePlot);
    if (unitInput) unitInput.addEventListener("change", updatePlot);
    if (zeroStartSwitch) zeroStartSwitch.addEventListener("change", updatePlot);
    if (titleInput) titleInput.addEventListener("change", updatePlot);
    if (markersSwitch) markersSwitch.addEventListener("change", updatePlot);
    if (showTitleSwitch) showTitleSwitch.addEventListener("change", updatePlot);
    if (showAxisLabelsSwitch)
      showAxisLabelsSwitch.addEventListener("change", updatePlot);
    if (showGridSwitch) showGridSwitch.addEventListener("change", updatePlot);
    if (showColorbarSwitch)
      showColorbarSwitch.addEventListener("change", updatePlot);
    if (showTicksSwitch) showTicksSwitch.addEventListener("change", updatePlot);
    if (showBorderSwitch)
      showBorderSwitch.addEventListener("change", updatePlot);

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
    if (batchSaveBtn)
      batchSaveBtn.addEventListener("click", () => {
        if (!isFileLoaded) {
          alert("Please load data first!");
          return;
        }
        if (!window.pywebview) return;
        const params = getPlotParams();
        const totalTrajs = parseInt(slider.max) + 1;
        const progressBar = batchSaveBtn.querySelector(".batch-progress");
        const batchLabel = batchSaveBtn.querySelector(".batch-label");
        window.pywebview.api.select_folder().then((folderRes) => {
          if (!folderRes || folderRes.cancelled) return;
          const folder = folderRes.path;
          batchSaveBtn.disabled = true;
          progressBar.style.width = "0%";
          let completed = 0;
          function saveNext(idx) {
            if (idx >= totalTrajs) {
              batchLabel.innerHTML =
                '<i data-lucide="files" class="icon-btn"></i> Batch';
              if (typeof lucide !== "undefined") lucide.createIcons();
              progressBar.style.width = "0%";
              batchSaveBtn.disabled = false;
              alert(
                "Batch save complete!\n" +
                  totalTrajs +
                  " files saved to:\n" +
                  folder,
              );
              return;
            }
            const p = Object.assign({}, params, { index: idx });
            window.pywebview.api
              .batch_save_single_msd(folder, p)
              .then((res) => {
                completed++;
                const pct = (completed / totalTrajs) * 100;
                progressBar.style.width = pct + "%";
                saveNext(idx + 1);
              })
              .catch(() => {
                completed++;
                saveNext(idx + 1);
              });
          }
          saveNext(0);
        });
      });

    if (batchSaveBtn)
      batchSaveBtn.addEventListener("click", () => {
        if (!isFileLoaded) {
          alert("Please load data first!");
          return;
        }
        if (!window.pywebview) return;
        const params = getPlotParams();
        const totalTrajs = parseInt(slider.max) + 1;
        const progressBar = batchSaveBtn.querySelector(".batch-progress");
        const batchLabel = batchSaveBtn.querySelector(".batch-label");

        window.pywebview.api.select_folder().then((folderRes) => {
          if (!folderRes || folderRes.cancelled) return;
          const folder = folderRes.path;
          batchSaveBtn.disabled = true;
          progressBar.style.width = "0%";
          let completed = 0;

          function saveNext(idx) {
            if (idx >= totalTrajs) {
              batchLabel.innerHTML =
                '<i data-lucide="files" class="icon-btn"></i> Batch';
              if (typeof lucide !== "undefined") lucide.createIcons();
              progressBar.style.width = "0%";
              batchSaveBtn.disabled = false;
              alert(
                "Batch save complete!\n" +
                  totalTrajs +
                  " files saved to:\n" +
                  folder,
              );
              return;
            }
            const p = Object.assign({}, params, { index: idx });
            window.pywebview.api
              .batch_save_single_plot(folder, p)
              .then((res) => {
                completed++;
                const pct = (completed / totalTrajs) * 100;
                progressBar.style.width = pct + "%";
                saveNext(idx + 1);
              })
              .catch(() => {
                completed++;
                saveNext(idx + 1);
              });
          }
          saveNext(0);
        });
      });
  };

  window.init_msd_viewer = function (root) {
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
    const xUnitInput = root.querySelector("#x-unit-input");
    const yUnitInput = root.querySelector("#y-unit-input");
    const dtInput = root.querySelector("#dt-input");
    const dtUnitInput = root.querySelector("#dt-unit-input");

    const titleInput = root.querySelector("#title-input");
    const legendSwitch = root.querySelector("#markers-switch");
    const eamsdSwitch = root.querySelector("#zero-start-switch");
    const tamsdSwitch = root.querySelector("#show-grid-switch");
    const tamsdMeanSwitch = root.querySelector("#plot-tamsd-mean-switch");
    const showTitleSwitch = root.querySelector("#show-title-switch");
    const showAxisLabelsSwitch = root.querySelector("#show-axis-labels-switch");
    const saveBtn = root.querySelector("#saveBtn");

    let isFileLoaded = false;

    function getPlotParams() {
      return {
        index: parseInt(slider.value) || 0,
        scale: parseFloat(scaleInput.value) || 1.0,
        x_unit: dtUnitInput
          ? dtUnitInput.value ||
            (xUnitInput ? xUnitInput.value || "frame" : "frame")
          : xUnitInput
            ? xUnitInput.value || "frame"
            : "frame",
        dt: dtInput ? parseFloat(dtInput.value) || 1.0 : 1.0,
        y_unit: yUnitInput ? yUnitInput.value || "unit" : "unit",
        custom_title: titleInput ? titleInput.value : "",
        show_legend: legendSwitch ? legendSwitch.checked : true,
        plot_eamsd: eamsdSwitch ? eamsdSwitch.checked : true,
        plot_tamsd: tamsdSwitch ? tamsdSwitch.checked : true,
        plot_tamsd_mean: tamsdMeanSwitch ? tamsdMeanSwitch.checked : true,
        show_title: showTitleSwitch ? showTitleSwitch.checked : true,
        show_axis_labels: showAxisLabelsSwitch
          ? showAxisLabelsSwitch.checked
          : true,
      };
    }

    function updatePlot() {
      if (!isFileLoaded) return;
      const params = getPlotParams();
      indexLbl.textContent = params.index + 1;
      if (window.pywebview) {
        loading.style.display = "block";
        plotImg.style.display = "none";
        errorMsg.style.display = "none";
        window.pywebview.api
          .change_msd(
            params.index,
            params.scale,
            params.x_unit,
            params.y_unit,
            params.custom_title,
            params.show_legend,
            params.plot_eamsd,
            params.plot_tamsd,
            params.plot_tamsd_mean,
            params.show_title,
            params.show_axis_labels,
            params.dt,
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

    if (slider) {
      slider.addEventListener("input", () => {
        indexLbl.textContent = parseInt(slider.value) + 1;
      });
      slider.addEventListener("change", updatePlot);
    }
    if (scaleInput) scaleInput.addEventListener("change", updatePlot);
    if (xUnitInput) xUnitInput.addEventListener("change", updatePlot);
    if (yUnitInput) yUnitInput.addEventListener("change", updatePlot);
    if (dtInput) dtInput.addEventListener("change", updatePlot);
    if (dtUnitInput) dtUnitInput.addEventListener("change", updatePlot);
    if (titleInput) titleInput.addEventListener("change", updatePlot);
    if (legendSwitch) legendSwitch.addEventListener("change", updatePlot);
    if (eamsdSwitch) eamsdSwitch.addEventListener("change", updatePlot);
    if (tamsdSwitch) tamsdSwitch.addEventListener("change", updatePlot);
    if (tamsdMeanSwitch) tamsdMeanSwitch.addEventListener("change", updatePlot);
    if (showTitleSwitch) showTitleSwitch.addEventListener("change", updatePlot);
    if (showAxisLabelsSwitch)
      showAxisLabelsSwitch.addEventListener("change", updatePlot);

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
          window.pywebview.api.save_msd_plot(params).then((res) => {
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
    const batchSaveBtn = root.querySelector("#batchSaveBtn");
    if (batchSaveBtn)
      batchSaveBtn.addEventListener("click", () => {
        if (!isFileLoaded) {
          alert("Please load data first!");
          return;
        }
        if (!window.pywebview) return;
        const params = getPlotParams();
        const totalTrajs = parseInt(slider.max) + 1;
        const progressBar = batchSaveBtn.querySelector(".batch-progress");
        const batchLabel = batchSaveBtn.querySelector(".batch-label");
        window.pywebview.api.select_folder().then((folderRes) => {
          if (!folderRes || folderRes.cancelled) return;
          const folder = folderRes.path;
          batchSaveBtn.disabled = true;
          progressBar.style.width = "0%";
          let completed = 0;
          function saveNext(idx) {
            if (idx >= totalTrajs) {
              batchLabel.innerHTML =
                '<i data-lucide="files" class="icon-btn"></i> Batch';
              if (typeof lucide !== "undefined") lucide.createIcons();
              progressBar.style.width = "0%";
              batchSaveBtn.disabled = false;
              alert(
                "Batch save complete!\n" +
                  totalTrajs +
                  " files saved to:\n" +
                  folder,
              );
              return;
            }
            const p = Object.assign({}, params, { index: idx });
            window.pywebview.api
              .batch_save_single_msd(folder, p)
              .then((res) => {
                completed++;
                const pct = (completed / totalTrajs) * 100;
                progressBar.style.width = pct + "%";
                saveNext(idx + 1);
              })
              .catch(() => {
                completed++;
                saveNext(idx + 1);
              });
          }
          saveNext(0);
        });
      });
  };

  window.init_activate_traj = function (root) {
    const uploadBtn = root.querySelector("#uploadBtn");
    const filePathDisplay = root.querySelector("#file-path-display");
    const canvas = root.querySelector("#anim-canvas");
    const plotImg = root.querySelector("#plot-image");
    const loading = root.querySelector("#loading");
    const errorMsg = root.querySelector("#error-msg");
    const placeholder = root.querySelector("#placeholder");

    const controlPanel = root.querySelector("#control-panel");
    const slider = root.querySelector("#traj-slider");
    const indexLbl = root.querySelector("#traj-index-lbl");
    const totalLbl = root.querySelector("#total-traj-lbl");

    const animControls = root.querySelector("#anim-controls");
    const playPauseBtn = root.querySelector("#play-pause-btn");
    const frameLbl = root.querySelector("#frame-lbl");
    const frameSlider = root.querySelector("#frame-slider");

    const scaleInput = root.querySelector("#scale-input");
    const unitInput = root.querySelector("#unit-input");
    const fpsInput = root.querySelector("#fps-input");
    const trailLenInput = root.querySelector("#trail-len-input");
    const zeroStartSwitch = root.querySelector("#zero-start-switch");

    const titleInput = root.querySelector("#title-input");
    const timebarSwitch = root.querySelector("#timebar-switch");
    const showTitleSwitch = root.querySelector("#show-title-switch");
    const showAxisLabelsSwitch = root.querySelector("#show-axis-labels-switch");
    const showGridSwitch = root.querySelector("#show-grid-switch");
    const saveBtn = root.querySelector("#saveBtn");
    const batchSaveBtn = root.querySelector("#batchSaveBtn");

    let isFileLoaded = false;

    let trajX = [];
    let trajY = [];
    let trajLen = 0;
    let animFrame = 0;
    let animPlaying = false;
    let animRAF = null;
    let lastFrameTime = 0;

    function getAnimParams() {
      const unit = unitInput ? unitInput.value || "px" : "px";
      return {
        fps: fpsInput ? parseInt(fpsInput.value) || 20 : 20,
        trail_len:
          trailLenInput && trailLenInput.value
            ? parseInt(trailLenInput.value)
            : 0,
        x_unit: unit,
        y_unit: unit,
        show_timebar: timebarSwitch ? timebarSwitch.checked : true,
        show_axis_labels: showAxisLabelsSwitch
          ? showAxisLabelsSwitch.checked
          : true,
        show_grid: showGridSwitch ? showGridSwitch.checked : true,
      };
    }

    function coolwarmColor(t) {

      const r =
        t < 0.5
          ? Math.round(59 + t * 2 * (221 - 59))
          : Math.round(221 + (t - 0.5) * 2 * (180 - 221));
      const g =
        t < 0.5
          ? Math.round(76 + t * 2 * (221 - 76))
          : Math.round(221 + (t - 0.5) * 2 * (4 - 221));
      const b =
        t < 0.5
          ? Math.round(192 + t * 2 * (221 - 192))
          : Math.round(221 + (t - 0.5) * 2 * (38 - 221));
      return `rgb(${Math.max(0, Math.min(255, r))},${Math.max(0, Math.min(255, g))},${Math.max(0, Math.min(255, b))})`;
    }

    function resizeCanvas() {
      if (!canvas) return;
      const container = canvas.parentElement;
      const dpr = window.devicePixelRatio || 1;
      const w = container.clientWidth;
      const h = container.clientHeight;
      canvas.width = w * dpr;
      canvas.height = h * dpr;
      canvas.style.width = w + "px";
      canvas.style.height = h + "px";
    }

    function drawFrame(frame, targetCanvas, dprOverride) {
      const c = targetCanvas || canvas;
      if (!c || trajLen < 2) return;
      const params = getAnimParams();
      const ctx = c.getContext("2d");
      const dpr =
        dprOverride || (targetCanvas ? 1 : window.devicePixelRatio || 1);
      const W = c.width;
      const H = c.height;

      ctx.clearRect(0, 0, W, H);
      ctx.fillStyle = "#fff";
      ctx.fillRect(0, 0, W, H);

      let maxAbsX = 0,
        maxAbsY = 0;
      for (let i = 0; i < trajLen; i++) {
        const ax = Math.abs(trajX[i]);
        const ay = Math.abs(trajY[i]);
        if (ax > maxAbsX) maxAbsX = ax;
        if (ay > maxAbsY) maxAbsY = ay;
      }
      const dataLimit = Math.max(maxAbsX, maxAbsY) * 1.1 || 1;

      const timebarH = params.show_timebar ? 30 * dpr : 0;
      const labelPad = params.show_axis_labels ? 40 * dpr : 10 * dpr;
      const pad = labelPad;
      const plotW = W - pad * 2;
      const plotH = H - pad * 2 - timebarH;
      const plotSize = Math.min(plotW, plotH);
      const ox = (W - plotSize) / 2;
      const oy = (H - plotSize - timebarH) / 2;

      function toCanvasX(dx) {
        return ox + (dx / dataLimit + 1) * 0.5 * plotSize;
      }
      function toCanvasY(dy) {
        return oy + (1 - (dy / dataLimit + 1) * 0.5) * plotSize;
      }

      if (params.show_grid) {
        ctx.save();
        ctx.strokeStyle = "rgba(128,128,128,0.25)";
        ctx.lineWidth = 1 * dpr;
        ctx.setLineDash([4 * dpr, 4 * dpr]);

        const zeroY = toCanvasY(0);
        ctx.beginPath();
        ctx.moveTo(ox, zeroY);
        ctx.lineTo(ox + plotSize, zeroY);
        ctx.stroke();

        const zeroX = toCanvasX(0);
        ctx.beginPath();
        ctx.moveTo(zeroX, oy);
        ctx.lineTo(zeroX, oy + plotSize);
        ctx.stroke();
        ctx.restore();
      }

      if (params.show_axis_labels) {
        ctx.save();
        const fontSize = Math.round(7 * dpr);
        ctx.font = `${fontSize}px sans-serif`;
        ctx.fillStyle = "rgba(128,128,128,0.6)";

        const limitVal = dataLimit.toFixed(2);
        const tickLen = plotSize * 0.015;
        const zeroY2 = toCanvasY(0);
        const zeroX2 = toCanvasX(0);
        const xTickPos = toCanvasX(dataLimit / 1.1);
        const xTickNeg = toCanvasX(-dataLimit / 1.1);
        const yTickPos = toCanvasY(dataLimit / 1.1);
        const yTickNeg = toCanvasY(-dataLimit / 1.1);

        ctx.strokeStyle = "rgba(128,128,128,0.8)";
        ctx.lineWidth = 1.5 * dpr;
        ctx.setLineDash([]);

        ctx.beginPath();
        ctx.moveTo(xTickPos, zeroY2 - tickLen);
        ctx.lineTo(xTickPos, zeroY2);
        ctx.stroke();
        ctx.beginPath();
        ctx.moveTo(xTickNeg, zeroY2 - tickLen);
        ctx.lineTo(xTickNeg, zeroY2);
        ctx.stroke();

        ctx.textAlign = "center";
        ctx.textBaseline = "top";
        ctx.fillText(
          `${limitVal} ${params.x_unit}`,
          xTickPos,
          zeroY2 + 3 * dpr,
        );
        ctx.fillText(
          `-${limitVal} ${params.x_unit}`,
          xTickNeg,
          zeroY2 + 3 * dpr,
        );

        ctx.beginPath();
        ctx.moveTo(zeroX2, yTickPos);
        ctx.lineTo(zeroX2 + tickLen, yTickPos);
        ctx.stroke();
        ctx.beginPath();
        ctx.moveTo(zeroX2, yTickNeg);
        ctx.lineTo(zeroX2 + tickLen, yTickNeg);
        ctx.stroke();

        ctx.textAlign = "right";
        ctx.textBaseline = "middle";
        ctx.fillText(
          `${limitVal} ${params.y_unit}`,
          zeroX2 - 4 * dpr,
          yTickPos,
        );
        ctx.fillText(
          `-${limitVal} ${params.y_unit}`,
          zeroX2 - 4 * dpr,
          yTickNeg,
        );

        ctx.restore();
      }

      let trailLen =
        params.trail_len > 0
          ? Math.min(params.trail_len, trajLen)
          : Math.max(1, Math.floor(trajLen / 2));
      const start = Math.max(0, frame - trailLen);
      const end = frame + 1;
      if (end - start > 1) {
        const segCount = end - start - 1;
        ctx.lineWidth = 3 * dpr;
        ctx.lineCap = "round";
        ctx.lineJoin = "round";
        for (let i = 0; i < segCount; i++) {
          const idx = start + i;
          const t = segCount > 1 ? i / (segCount - 1) : 1;
          ctx.strokeStyle = coolwarmColor(t);
          ctx.beginPath();
          ctx.moveTo(toCanvasX(trajX[idx]), toCanvasY(trajY[idx]));
          ctx.lineTo(toCanvasX(trajX[idx + 1]), toCanvasY(trajY[idx + 1]));
          ctx.stroke();
        }
      }

      const px = toCanvasX(trajX[frame]);
      const py = toCanvasY(trajY[frame]);
      ctx.beginPath();
      ctx.arc(px, py, 5 * dpr, 0, Math.PI * 2);
      ctx.fillStyle = "#ef4444";
      ctx.fill();
      ctx.lineWidth = 1.5 * dpr;
      ctx.strokeStyle = "#fff";
      ctx.stroke();

      if (params.show_timebar) {
        const barY =
          oy + plotSize + (params.show_axis_labels ? 22 * dpr : 8 * dpr);
        const barH = 8 * dpr;
        const barW = (plotSize * 3) / 4;
        const barX = ox + (plotSize - barW) / 2;

        for (let i = 0; i < barW; i++) {
          ctx.fillStyle = coolwarmColor(i / barW);
          ctx.fillRect(barX + i, barY, 1, barH);
        }

        ctx.strokeStyle = "#aaa";
        ctx.lineWidth = 0.6 * dpr;
        ctx.strokeRect(barX, barY, barW, barH);

        const progX = barX + (frame / Math.max(1, trajLen - 1)) * barW;
        ctx.beginPath();
        ctx.moveTo(progX, barY - 2 * dpr);
        ctx.lineTo(progX, barY + barH + 2 * dpr);
        ctx.strokeStyle = "#333";
        ctx.lineWidth = 1.5 * dpr;
        ctx.stroke();

        const fontSize2 = Math.round(7 * dpr);
        ctx.font = `italic 600 ${fontSize2}px sans-serif`;
        ctx.fillStyle = "#000";
        ctx.textAlign = "center";
        ctx.fillText(
          `Trail: ${trailLen} frames`,
          barX + barW / 2,
          barY - 4 * dpr,
        );
      }

      if (frameLbl) frameLbl.textContent = `${frame + 1} / ${trajLen}`;
      if (frameSlider) frameSlider.value = frame;
    }

    function animLoop(ts) {
      if (!animPlaying) return;
      const params = getAnimParams();
      const interval = 1000 / params.fps;
      if (ts - lastFrameTime >= interval) {
        lastFrameTime = ts;
        animFrame++;
        if (animFrame >= trajLen) animFrame = 0;
        drawFrame(animFrame);
      }
      animRAF = requestAnimationFrame(animLoop);
    }

    function startAnim() {
      if (trajLen < 2) return;
      animPlaying = true;
      if (playPauseBtn) playPauseBtn.textContent = "⏸";
      lastFrameTime = performance.now();
      animRAF = requestAnimationFrame(animLoop);
    }

    function stopAnim() {
      animPlaying = false;
      if (playPauseBtn) playPauseBtn.textContent = "▶";
      if (animRAF) {
        cancelAnimationFrame(animRAF);
        animRAF = null;
      }
    }

    function loadTrajectoryData(index) {
      if (!window.pywebview) return;
      const scale = scaleInput ? parseFloat(scaleInput.value) || 1.0 : 1.0;
      const zeroStart = zeroStartSwitch ? zeroStartSwitch.checked : false;
      loading.style.display = "block";
      canvas.style.display = "none";

      window.pywebview.api
        .get_trajectory_data(index, scale, zeroStart)
        .then((res) => {
          loading.style.display = "none";
          if (res.error) {
            errorMsg.textContent = res.error;
            errorMsg.style.display = "block";
            return;
          }
          trajX = res.x;
          trajY = res.y;
          trajLen = res.length;
          animFrame = 0;

          if (trajLen < 2) {
            errorMsg.textContent = "Trajectory too short to animate";
            errorMsg.style.display = "block";
            return;
          }

          resizeCanvas();
          canvas.style.display = "block";
          errorMsg.style.display = "none";

          if (frameSlider) {
            frameSlider.max = trajLen - 1;
            frameSlider.value = 0;
          }
          if (animControls) animControls.style.display = "flex";

          drawFrame(0);
          startAnim();
        })
        .catch((err) => {
          loading.style.display = "none";
          errorMsg.textContent = "Error: " + err;
          errorMsg.style.display = "block";
        });
    }

    if (playPauseBtn) {
      playPauseBtn.addEventListener("click", () => {
        if (animPlaying) stopAnim();
        else startAnim();
      });
    }

    if (frameSlider) {
      frameSlider.addEventListener("input", () => {
        stopAnim();
        animFrame = parseInt(frameSlider.value) || 0;
        drawFrame(animFrame);
      });
    }

    const ro = new ResizeObserver(() => {
      if (canvas.style.display !== "none") {
        resizeCanvas();
        drawFrame(animFrame);
      }
    });
    if (canvas && canvas.parentElement) ro.observe(canvas.parentElement);

    function onVisualChange() {
      if (trajLen > 0) drawFrame(animFrame);
    }
    if (fpsInput) fpsInput.addEventListener("change", onVisualChange);
    if (trailLenInput) trailLenInput.addEventListener("change", onVisualChange);
    if (timebarSwitch) timebarSwitch.addEventListener("change", onVisualChange);
    if (showAxisLabelsSwitch)
      showAxisLabelsSwitch.addEventListener("change", onVisualChange);
    if (showGridSwitch)
      showGridSwitch.addEventListener("change", onVisualChange);

    function onDataChange() {
      if (!isFileLoaded) return;
      stopAnim();
      loadTrajectoryData(parseInt(slider.value) || 0);
    }
    if (scaleInput) scaleInput.addEventListener("change", onDataChange);
    if (unitInput) unitInput.addEventListener("change", onVisualChange);
    if (zeroStartSwitch)
      zeroStartSwitch.addEventListener("change", onDataChange);

    if (slider) {
      slider.addEventListener("input", () => {
        indexLbl.textContent = parseInt(slider.value) + 1;
      });
      slider.addEventListener("change", () => {
        stopAnim();
        loadTrajectoryData(parseInt(slider.value) || 0);
      });
    }

    if (uploadBtn)
      uploadBtn.addEventListener("click", () => {
        if (!window.pywebview) {
          alert("Please run in the Pywebview environment!");
          return;
        }
        placeholder.style.display = "none";
        canvas.style.display = "none";
        errorMsg.style.display = "none";
        loading.style.display = "block";
        stopAnim();

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
                loadTrajectoryData(0);
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
        if (!isFileLoaded || trajLen < 2) {
          alert("Please load data first!");
          return;
        }
        if (!window.pywebview) return;
        const fps = fpsInput ? parseInt(fpsInput.value) || 20 : 20;
        const originalText = saveBtn.innerHTML;
        saveBtn.innerHTML = "<span>⏳</span> Saving...";
        saveBtn.disabled = true;

        window.pywebview.api
          .select_gif_save_path(parseInt(slider.value) || 0)
          .then((pathRes) => {
            if (!pathRes || pathRes.cancelled) {
              saveBtn.innerHTML = originalText;
              saveBtn.disabled = false;
              return;
            }
            const savePath = pathRes.path;

            const gifScale = 2;
            const baseW = canvas.width / (window.devicePixelRatio || 1);
            const baseH = canvas.height / (window.devicePixelRatio || 1);
            const offscreen = document.createElement("canvas");
            offscreen.width = Math.round(baseW * gifScale);
            offscreen.height = Math.round(baseH * gifScale);
            const frames = [];
            for (let fi = 0; fi < trajLen; fi++) {
              drawFrame(fi, offscreen, gifScale);
              frames.push(offscreen.toDataURL("image/png"));
            }
            window.pywebview.api
              .save_canvas_gif(savePath, frames, fps)
              .then((res) => {
                saveBtn.innerHTML = originalText;
                saveBtn.disabled = false;
                if (res.success) {
                  alert("Saved successfully!\nPath: " + res.path);
                } else if (res.error) {
                  alert("Save failed: " + res.error);
                }
              });
          });
      });

    if (batchSaveBtn)
      batchSaveBtn.addEventListener("click", () => {
        if (!isFileLoaded) {
          alert("Please load data first!");
          return;
        }
        if (!window.pywebview) return;
        const totalTrajs = parseInt(slider.max) + 1;
        const scale = scaleInput ? parseFloat(scaleInput.value) || 1.0 : 1.0;
        const zeroStart = zeroStartSwitch ? zeroStartSwitch.checked : false;
        const progressBar = batchSaveBtn.querySelector(".batch-progress");
        const batchLabel = batchSaveBtn.querySelector(".batch-label");
        window.pywebview.api.select_folder().then((folderRes) => {
          if (!folderRes || folderRes.cancelled) return;
          const folder = folderRes.path;
          batchSaveBtn.disabled = true;
          progressBar.style.width = "0%";
          batchLabel.textContent = "0 / " + totalTrajs;
          let completed = 0;
          const hiresScale = 3;
          const baseW = canvas.width / (window.devicePixelRatio || 1);
          const baseH = canvas.height / (window.devicePixelRatio || 1);

          function saveNext(idx) {
            if (idx >= totalTrajs) {
              batchLabel.innerHTML =
                '<i data-lucide="files" class="icon-btn"></i> Batch';
              if (typeof lucide !== "undefined") lucide.createIcons();
              progressBar.style.width = "0%";
              batchSaveBtn.disabled = false;
              alert(
                "Batch save complete!\n" +
                  totalTrajs +
                  " files saved to:\n" +
                  folder,
              );
              return;
            }
            window.pywebview.api
              .get_trajectory_data(idx, scale, zeroStart)
              .then((res) => {
                if (res.error || res.length < 2) {
                  completed++;
                  const pct = (completed / totalTrajs) * 100;
                  progressBar.style.width = pct + "%";
                  batchLabel.textContent = completed + " / " + totalTrajs;
                  saveNext(idx + 1);
                  return;
                }
                const origX = trajX,
                  origY = trajY,
                  origLen = trajLen;
                trajX = res.x;
                trajY = res.y;
                trajLen = res.length;
                const offscreen = document.createElement("canvas");
                offscreen.width = Math.round(baseW * hiresScale);
                offscreen.height = Math.round(baseH * hiresScale);
                const fps = fpsInput ? parseInt(fpsInput.value) || 20 : 20;

                const frames = [];
                for (let f = 0; f < trajLen; f++) {
                  drawFrame(f, offscreen, hiresScale);
                  frames.push(offscreen.toDataURL("image/png"));
                }
                trajX = origX;
                trajY = origY;
                trajLen = origLen;
                const savePath = folder + "\\anim_" + idx + ".gif";
                window.pywebview.api
                  .save_canvas_gif(savePath, frames, fps)
                  .then(() => {
                    completed++;
                    const pct = (completed / totalTrajs) * 100;
                    progressBar.style.width = pct + "%";
                    batchLabel.textContent = completed + " / " + totalTrajs;
                    saveNext(idx + 1);
                  })
                  .catch(() => {
                    completed++;
                    saveNext(idx + 1);
                  });
              })
              .catch(() => {
                completed++;
                saveNext(idx + 1);
              });
          }
          saveNext(0);
        });
      });

    root._cleanup = stopAnim;
  };
});



(function () {
  let _updateInfo = null;
  let _pollTimer = null;

  function _removeToast() {
    const t = document.getElementById("update-toast");
    if (t) t.remove();
    if (_pollTimer) { clearInterval(_pollTimer); _pollTimer = null; }
  }

  function _showToast(info, alreadyDownloaded) {
    _removeToast();
    _updateInfo = info;
    const dlLabel = alreadyDownloaded ? "Install now" : "Download update";
    const toast = document.createElement("div");
    toast.id = "update-toast";
    toast.innerHTML = `
      <div class="ut-header">
        <span class="ut-badge">UPDATE</span>
        <span class="ut-title">v${info.version} available</span>
      </div>
      <div class="ut-body">A new version is available. Current v${info.current_version}. Download and install now?</div>
      <div class="ut-actions">
        <button class="ut-btn primary" id="ut-dl">${dlLabel}</button>
        <button class="ut-btn secondary" id="ut-dismiss">Later</button>
      </div>
      <div class="ut-progress-wrap" id="ut-prog" style="display:none">
        <div class="ut-progress-bg"><div class="ut-progress-fill" id="ut-fill"></div></div>
        <div class="ut-progress-text" id="ut-pct">0%</div>
      </div>
    `;
    document.body.appendChild(toast);
    document.getElementById("ut-dismiss").onclick = _removeToast;
    if (alreadyDownloaded && info.download_path) {
      document.getElementById("ut-dl").onclick = () => _install(info.download_path);
    } else {
      document.getElementById("ut-dl").onclick = _startDownload;
    }
  }

  function _startDownload() {
    if (!_updateInfo || !window.pywebview) return;
    const dlBtn = document.getElementById("ut-dl");
    const dimBtn = document.getElementById("ut-dismiss");
    const prog = document.getElementById("ut-prog");
    if (dlBtn) { dlBtn.disabled = true; dlBtn.textContent = "Downloading..."; }
    if (dimBtn) dimBtn.disabled = true;
    if (prog) prog.style.display = "";

    window.pywebview.api
      .start_download(_updateInfo.url, _updateInfo.filename)
      .then(() => {
        _pollTimer = setInterval(_poll, 600);
      })
      .catch((err) => {
        if (dlBtn) { dlBtn.disabled = false; dlBtn.textContent = "Retry"; }
        if (dimBtn) dimBtn.disabled = false;
        console.error("[Update] start_download failed:", err);
      });
  }

  function _poll() {
    if (!window.pywebview) return;
    window.pywebview.api.get_download_progress().then((s) => {
      const fill = document.getElementById("ut-fill");
      const pct  = document.getElementById("ut-pct");
      const dlBtn = document.getElementById("ut-dl");
      const pct_val = s.progress || 0;
      if (fill) fill.style.width = pct_val + "%";
      if (pct)  pct.textContent  = pct_val + "%";

      if (s.status === "done") {
        clearInterval(_pollTimer); _pollTimer = null;
        if (fill) fill.style.width = "100%";
        if (pct)  pct.textContent  = "Download complete";
        if (dlBtn) {
          dlBtn.disabled = false;
          dlBtn.textContent = "Install now";
          dlBtn.onclick = () => _install(s.path);
        }
      } else if (s.status === "error") {
        clearInterval(_pollTimer); _pollTimer = null;
        if (pct) pct.textContent = "Download failed: " + (s.error || "");
        const dimBtn = document.getElementById("ut-dismiss");
        if (dimBtn) dimBtn.disabled = false;
      }
    }).catch(() => {});
  }

  function _install(path) {
    if (!window.pywebview || !path) return;
    window.pywebview.api.install_update(path)
      .then(() => _removeToast())
      .catch((err) => alert("Failed to start installer: " + err));
  }

  
  window.checkForUpdates = async function (silent) {
    if (!window.pywebview) {
      if (!silent) alert("Not running in pywebview environment.");
      return;
    }
    try {
      const res = await window.pywebview.api.check_update();
      if (res.has_update) {
        if (res.has_downloaded && res.download_path) {
          _showToast(res, true);
        } else {
          _showToast(res, false);
        }
      } else if (!silent) {
        const cur = res.current_version || "?";
        const msg = res.error
          ? "Failed to check for updates: " + res.error
          : `visualSPT is already up to date (v${cur}).`;
        alert(msg);
      }
    } catch (e) {
      if (!silent) alert("Failed to check for updates: " + e);
    }
  };
})();

