// static/js/templates/index.js
let detectedName = "";
let lastNotified = "";

function fetchDetectedName() {
  fetch("/get_detected_name")
    .then((response) => response.json())
    .then((data) => {
      detectedName = data.detected_name || "";
      const absenStatus = data.absen_status;
      document.getElementById("detectedName").textContent = detectedName || "Tidak ada deteksi";

      if (detectedName && absenStatus && detectedName !== lastNotified) {
        showPopup(`Absensi berhasil untuk: ${detectedName}`);
        lastNotified = detectedName;
      }
    })
    .catch((error) => console.error("Error fetching detected name:", error));
}

function manualAttendance() {
  if (detectedName) {
    // Cek status hari libur terlebih dahulu
    fetch("/check_holiday_status")
      .then((response) => response.json())
      .then((holidayData) => {
        if (holidayData.is_holiday) {
          showPopup(`❌ ${holidayData.message}\nTidak dapat melakukan absensi hari ini.`, "error");
          return;
        }

        // Jika bukan hari libur, lanjutkan absensi
        fetch("/absen_manual", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ nama: detectedName }),
        })
          .then((response) => response.json())
          .then((data) => {
            if (data.is_holiday) {
              showPopup(`❌ ${data.message}`, "error");
            } else {
              showPopup(`✅ ${data.message}`, "success");
            }
          })
          .catch((error) => {
            console.error("Error:", error);
            showPopup("❌ Terjadi kesalahan saat mencatat absensi.", "error");
          });
      })
      .catch((error) => {
        console.error("Error checking holiday status:", error);
        showPopup("❌ Terjadi kesalahan saat mengecek status hari libur.", "error");
      });
  } else {
    showPopup("❌ Tidak ada nama yang terdeteksi untuk absensi.", "warning");
  }
}

function checkHolidayStatus() {
  fetch("/check_holiday_status")
    .then((response) => response.json())
    .then((data) => {
      if (data.is_holiday) {
        // Tampilkan notifikasi hari libur yang persisten
        showHolidayNotification(data.message);

        // Disable tombol absensi manual jika ada
        const manualBtn = document.querySelector(".manual-attendance-btn");
        if (manualBtn) {
          manualBtn.disabled = true;
          manualBtn.classList.add("opacity-50", "cursor-not-allowed");
          manualBtn.title = data.message;
        }
      }
    })
    .catch((error) => {
      console.error("Error checking holiday status:", error);
    });
}

function showHolidayNotification(message) {
  // Buat atau update notifikasi hari libur yang persisten
  let holidayAlert = document.getElementById("holiday-alert");

  if (!holidayAlert) {
    holidayAlert = document.createElement("div");
    holidayAlert.id = "holiday-alert";
    holidayAlert.className = "fixed top-4 left-1/2 transform -translate-x-1/2 z-50 bg-red-500 text-white px-6 py-3 rounded-lg shadow-lg max-w-md text-center";

    // Tambahkan icon
    holidayAlert.innerHTML = `
      <div class="flex items-center justify-center space-x-2">
        <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
          <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clip-rule="evenodd"></path>
        </svg>
        <span>${message}</span>
      </div>
    `;

    document.body.appendChild(holidayAlert);
  } else {
    holidayAlert.querySelector("span").textContent = message;
  }
}

// Initialize interval for name detection
document.addEventListener("DOMContentLoaded", function () {
  // Cek status hari libur saat halaman dimuat
  checkHolidayStatus();

  setInterval(fetchDetectedName, 1000);

  // No loading overlay needed - direct video feed
  console.log("Video feed initialized without loading overlay");

  // Keyboard shortcut for manual attendance
  document.addEventListener("keydown", function (event) {
    if (event.key === "Enter") {
      manualAttendance();
    }
  });

  // Admin dropdown functionality
  document.getElementById("adminMenu")?.addEventListener("click", function (e) {
    if (e.target.closest("#adminMenu") && !e.target.closest("#adminMenuDropdown")) {
      document.getElementById("adminMenuDropdown")?.classList.toggle("hidden");
    }
  });

  // Close dropdown on outside click
  window.addEventListener("click", function (e) {
    if (document.getElementById("adminMenu") && !document.getElementById("adminMenu").contains(e.target)) {
      document.getElementById("adminMenuDropdown")?.classList.add("hidden");
    }
  });
});
