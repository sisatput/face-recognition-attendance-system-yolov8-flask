// static/js/templates/simple_absensi.js
document.addEventListener("DOMContentLoaded", function () {
  // Cek status hari libur saat halaman dimuat
  checkHolidayStatus();

  // Auto-refresh untuk update status
  setInterval(checkHolidayStatus, 30000); // Cek setiap 30 detik
});

function checkHolidayStatus() {
  fetch("/check_holiday_status")
    .then((response) => response.json())
    .then((data) => {
      if (data.is_holiday) {
        showHolidayNotification(data.message);
      } else {
        hideHolidayNotification();
      }
    })
    .catch((error) => {
      console.error("Error checking holiday status:", error);
    });
}

function showHolidayNotification(message) {
  let holidayAlert = document.getElementById("holiday-alert-simple");

  if (!holidayAlert) {
    holidayAlert = document.createElement("div");
    holidayAlert.id = "holiday-alert-simple";
    holidayAlert.className = "bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4";

    holidayAlert.innerHTML = `
      <div class="flex items-center">
        <svg class="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 20 20">
          <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clip-rule="evenodd"></path>
        </svg>
        <strong>Pemberitahuan: </strong>
        <span class="holiday-message">${message}</span>
      </div>
    `;

    // Insert di awal konten halaman
    const container = document.querySelector(".container") || document.body;
    const firstChild = container.firstElementChild;
    if (firstChild) {
      container.insertBefore(holidayAlert, firstChild);
    } else {
      container.appendChild(holidayAlert);
    }
  } else {
    holidayAlert.querySelector(".holiday-message").textContent = message;
  }
}

function hideHolidayNotification() {
  const holidayAlert = document.getElementById("holiday-alert-simple");
  if (holidayAlert) {
    holidayAlert.remove();
  }
}
