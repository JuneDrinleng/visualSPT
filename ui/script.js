document.addEventListener("DOMContentLoaded", () => {
  // --- 1. 导航栏切换逻辑 ---
  const navBtns = document.querySelectorAll(".nav-btn");
  const pages = document.querySelectorAll(".page");

  navBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      // 移除所有激活状态
      navBtns.forEach((b) => b.classList.remove("active"));
      pages.forEach((p) => p.classList.remove("active"));

      // 激活当前按钮
      btn.classList.add("active");

      // 获取目标页面 ID (HTML中已添加 data-target)
      const targetId = btn.getAttribute("data-target");
      const targetPage = document.getElementById(targetId);
      if (targetPage) {
        targetPage.classList.add("active");
      }
    });
  });

  // --- 2. 核心元素引用 (确保这些ID在HTML中存在) ---
  const uploadBtn = document.getElementById("uploadBtn");
  const filePathDisplay = document.getElementById("file-path-display");
  const plotImg = document.getElementById("plot-image");
  const loading = document.getElementById("loading");
  const errorMsg = document.getElementById("error-msg");
  const placeholder = document.getElementById("placeholder");

  // 滑块区域
  const controlPanel = document.getElementById("control-panel");
  const slider = document.getElementById("traj-slider");
  const indexLbl = document.getElementById("traj-index-lbl"); // 当前索引数字
  const totalLbl = document.getElementById("total-traj-lbl"); // 总数标签

  // 右侧设置区域
  const scaleInput = document.getElementById("scale-input");
  const zeroStartSwitch = document.getElementById("zero-start-switch");
  const xUnitInput = document.getElementById("x-unit-input");
  const yUnitInput = document.getElementById("y-unit-input");

  // 【新增引用】
  const titleInput = document.getElementById("title-input");
  const markersSwitch = document.getElementById("markers-switch");

  const saveBtn = document.getElementById("saveBtn");

  // 状态变量
  let isFileLoaded = false;

  // --- 3. 辅助函数：获取当前设置参数 ---
  function getPlotParams() {
    return {
      index: parseInt(slider.value) || 0,
      scale: parseFloat(scaleInput.value) || 1.0,
      zero_start: zeroStartSwitch.checked,
      x_unit: xUnitInput.value || "px",
      y_unit: yUnitInput.value || "px",
      // 【新增参数】
      custom_title: titleInput ? titleInput.value : "",
      show_markers: markersSwitch ? markersSwitch.checked : true,
    };
  }

  // --- 4. 辅助函数：刷新图表 ---
  function updatePlot() {
    if (!isFileLoaded) return;

    const params = getPlotParams();
    indexLbl.textContent = params.index; // 更新显示的数字

    // 检查 pywebview 是否存在 (防止在普通浏览器打开报错)
    if (window.pywebview) {
      window.pywebview.api
        .change_trajectory(
          params.index,
          params.scale,
          params.zero_start,
          params.x_unit,
          params.y_unit,
          params.custom_title, // 【新增传参】
          params.show_markers, // 【新增传参】
        )
        .then((res) => {
          if (res.image) {
            plotImg.src = res.image; // 假设返回的是 base64 或 路径
            errorMsg.style.display = "none";
            plotImg.style.display = "block";
          } else if (res.error) {
            console.error(res.error);
            errorMsg.textContent = res.error;
            errorMsg.style.display = "block";
          }
        });
    } else {
      console.warn("Pywebview API not found (running in browser mode?)");
    }
  }

  // --- 5. 事件监听：控件变化自动刷新 ---

  // 滑块拖动时只更新数字，不请求后端（防止卡顿）
  slider.addEventListener("input", () => {
    indexLbl.textContent = slider.value;
  });

  // 滑块拖动结束（松手）时才请求后端
  slider.addEventListener("change", updatePlot);

  // 设置项变化
  scaleInput.addEventListener("change", updatePlot);
  zeroStartSwitch.addEventListener("change", updatePlot);
  xUnitInput.addEventListener("change", updatePlot);
  yUnitInput.addEventListener("change", updatePlot);

  // 【新增监听】
  if (titleInput) {
    titleInput.addEventListener("change", updatePlot); // 输入框失焦或回车后刷新
  }
  if (markersSwitch) {
    markersSwitch.addEventListener("change", updatePlot); // 开关切换后刷新
  }

  // --- 6. 上传逻辑 ---
  uploadBtn.addEventListener("click", () => {
    if (!window.pywebview) {
      alert("请在 Pywebview 环境下运行！");
      return;
    }

    // UI 重置
    placeholder.style.display = "none";
    plotImg.style.display = "none";
    errorMsg.style.display = "none";
    loading.style.display = "block";

    window.pywebview.api
      .process_file_dialog()
      .then((res) => {
        loading.style.display = "none";

        if (res.cancelled) {
          if (!isFileLoaded) placeholder.style.display = "flex"; // Flex布局保持居中
          return;
        }

        if (res.error) {
          errorMsg.textContent = "错误: " + res.error;
          errorMsg.style.display = "block";
          filePathDisplay.textContent = "读取失败";
          isFileLoaded = false;
        } else {
          // 成功加载
          isFileLoaded = true;
          // 截取文件名
          filePathDisplay.textContent = res.file_path.split(/[/\\]/).pop();

          // 初始化滑块
          if (res.total_trajs > 0) {
            controlPanel.style.display = "flex"; // 显示控制条
            slider.max = res.total_trajs - 1;
            slider.value = 0;
            indexLbl.textContent = "0";
            totalLbl.textContent = `/ 共 ${res.total_trajs} 条`;

            // 显示第一张图 (带默认参数)
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
    // 按钮变更为“保存中...”
    const originalText = saveBtn.innerHTML; // 使用 innerHTML 保留图标
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
          params.custom_title, // 【新增传参】
          params.show_markers, // 【新增传参】
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
