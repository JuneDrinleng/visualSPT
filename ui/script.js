document.addEventListener("DOMContentLoaded", () => {
  // --- 1. 导航栏切换逻辑 ---
  const navBtns = document.querySelectorAll(".nav-btn");
  const pages = document.querySelectorAll(".page");

  navBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      navBtns.forEach((b) => b.classList.remove("active"));
      pages.forEach((p) => p.classList.remove("active"));
      btn.classList.add("active");
      const targetId = btn.getAttribute("data-target");
      document.getElementById(targetId).classList.add("active");
    });
  });

  // --- 2. 核心逻辑 ---
  const uploadBtn = document.getElementById("uploadBtn");
  const filePathDisplay = document.getElementById("file-path-display");
  const plotImg = document.getElementById("plot-image");
  const loading = document.getElementById("loading");
  const errorMsg = document.getElementById("error-msg");
  const placeholder = document.getElementById("placeholder");

  // 新增控件引用
  const controlPanel = document.getElementById("control-panel");
  const slider = document.getElementById("traj-slider");
  const indexLbl = document.getElementById("traj-index-lbl");
  const totalLbl = document.getElementById("total-traj-lbl");

  uploadBtn.addEventListener("click", () => {
    // UI 状态重置
    placeholder.style.display = "none";
    plotImg.style.display = "none";
    errorMsg.style.display = "none";
    controlPanel.style.display = "none"; // 重新加载时先隐藏滑块

    if (!window.pywebview) {
      alert("请在 Pywebview 环境下运行！");
      return;
    }

    loading.style.display = "block";

    window.pywebview.api
      .process_file_dialog()
      .then((res) => {
        loading.style.display = "none";

        if (res.cancelled) {
          if (
            placeholder.style.display === "none" &&
            plotImg.style.display === "none"
          ) {
            placeholder.style.display = "flex"; // flex for centering
          }
          return;
        }

        if (res.error) {
          errorMsg.textContent = "错误: " + res.error;
          errorMsg.style.display = "block";
          filePathDisplay.textContent = "读取失败";
        } else {
          // 成功加载
          plotImg.src = res.image;
          plotImg.style.display = "block";
          filePathDisplay.textContent = res.file_path.split(/[/\\]/).pop();
          // --- 设置滑块 ---
          if (res.total_trajs > 0) {
            controlPanel.style.display = "block";
            slider.max = res.total_trajs - 1;
            slider.value = 0;
            indexLbl.textContent = "0"; // 对应第1条，索引为0
            totalLbl.textContent = `/ 共 ${res.total_trajs} 条`;
          }
        }
      })
      .catch((err) => {
        loading.style.display = "none";
        errorMsg.textContent = "系统异常: " + err;
        errorMsg.style.display = "block";
      });
  });

  // --- 3. 滑块拖动事件 ---
  slider.addEventListener("input", (e) => {
    const index = parseInt(e.target.value);
    indexLbl.textContent = index; // 显示当前索引

    // 为了防止拖动过快导致卡顿，可以加防抖(debounce)，这里简单处理直接调用
    window.pywebview.api.change_trajectory(index).then((res) => {
      if (res.image) {
        plotImg.src = res.image;
      } else if (res.error) {
        console.error(res.error);
      }
    });
  });
});
