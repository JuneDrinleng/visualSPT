document.addEventListener("DOMContentLoaded", () => {
  // --- 1. 导航栏切换逻辑 (保持不变) ---
  const navBtns = document.querySelectorAll(".nav-btn");
  const pages = document.querySelectorAll(".page");

  navBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      navBtns.forEach((b) => b.classList.remove("active"));
      pages.forEach((p) => p.classList.remove("active"));
      btn.classList.add("active");
      const targetId = btn.getAttribute("data-target");
      const targetPage = document.getElementById(targetId);
      if (targetPage) targetPage.classList.add("active");
    });
  });

  // --- 2. 核心元素引用 ---
  const uploadBtn = document.getElementById("uploadBtn");
  const filePathDisplay = document.getElementById("file-path-display");
  const plotImg = document.getElementById("plot-image");
  const loading = document.getElementById("loading");
  const errorMsg = document.getElementById("error-msg");
  const placeholder = document.getElementById("placeholder");

  const controlPanel = document.getElementById("control-panel");
  const slider = document.getElementById("traj-slider");
  const indexLbl = document.getElementById("traj-index-lbl");
  const totalLbl = document.getElementById("total-traj-lbl");

  const scaleInput = document.getElementById("scale-input");
  const zeroStartSwitch = document.getElementById("zero-start-switch");
  const xUnitInput = document.getElementById("x-unit-input");
  const yUnitInput = document.getElementById("y-unit-input");

  const titleInput = document.getElementById("title-input");
  const markersSwitch = document.getElementById("markers-switch");

  // 【新增引用】
  const showTitleSwitch = document.getElementById("show-title-switch");
  const showAxisLabelsSwitch = document.getElementById(
    "show-axis-labels-switch",
  );
  const showGridSwitch = document.getElementById("show-grid-switch");

  const saveBtn = document.getElementById("saveBtn");

  let isFileLoaded = false;

  // --- 3. 辅助函数：获取当前设置参数 ---
  function getPlotParams() {
    return {
      index: parseInt(slider.value) || 0,
      scale: parseFloat(scaleInput.value) || 1.0,
      zero_start: zeroStartSwitch.checked,
      x_unit: xUnitInput.value || "px",
      y_unit: yUnitInput.value || "px",
      custom_title: titleInput ? titleInput.value : "",
      show_markers: markersSwitch ? markersSwitch.checked : true,
      // 【新增参数】
      show_title: showTitleSwitch ? showTitleSwitch.checked : true,
      show_axis_labels: showAxisLabelsSwitch
        ? showAxisLabelsSwitch.checked
        : true,
      show_grid: showGridSwitch ? showGridSwitch.checked : true,
    };
  }

  // --- 4. 辅助函数：刷新图表 ---
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
          // 【新增传参】注意顺序
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
            console.error(res.error);
            errorMsg.textContent = res.error;
            errorMsg.style.display = "block";
          }
        });
    }
  }

  // --- 5. 事件监听 ---
  slider.addEventListener("input", () => {
    indexLbl.textContent = parseInt(slider.value) + 1;
  });
  slider.addEventListener("change", updatePlot);

  scaleInput.addEventListener("change", updatePlot);
  zeroStartSwitch.addEventListener("change", updatePlot);
  xUnitInput.addEventListener("change", updatePlot);
  yUnitInput.addEventListener("change", updatePlot);

  if (titleInput) titleInput.addEventListener("change", updatePlot);
  if (markersSwitch) markersSwitch.addEventListener("change", updatePlot);

  // 【新增监听】
  if (showTitleSwitch) showTitleSwitch.addEventListener("change", updatePlot);
  if (showAxisLabelsSwitch)
    showAxisLabelsSwitch.addEventListener("change", updatePlot);
  if (showGridSwitch) showGridSwitch.addEventListener("change", updatePlot);

  // --- 6. 上传逻辑 (保持不变) ---
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

  // --- 7. 保存按钮逻辑 ---
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
      window.pywebview.api
        .save_plot(
          params.index,
          params.scale,
          params.zero_start,
          params.x_unit,
          params.y_unit,
          params.custom_title,
          params.show_markers,
          // 【新增传参】
          params.show_title,
          params.show_axis_labels,
          params.show_grid,
        )
        .then((res) => {
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
});
