// jadwal_bulanan.js - JavaScript untuk halaman jadwal bulanan

let currentEditingDay = null;
let scheduleChanges = {};

// Function untuk switch tab antara jadwal bulanan dan jadwal umum
function switchTab(tabName) {
  // Update tab buttons
  const monthlyTab = document.getElementById("monthlyTab");
  const generalTab = document.getElementById("generalTab");

  // Update tab content
  const monthlySchedule = document.getElementById("monthlySchedule");
  const generalSchedule = document.getElementById("generalSchedule");

  if (tabName === "monthly") {
    // Activate monthly tab
    monthlyTab.className = "tab-button px-8 py-4 text-sm font-medium text-indigo-600 bg-indigo-50 border-b-2 border-indigo-500";
    generalTab.className = "tab-button px-8 py-4 text-sm font-medium text-gray-500 hover:text-gray-700 hover:bg-gray-50 border-b-2 border-transparent";

    // Show monthly content, hide general
    monthlySchedule.classList.remove("hidden");
    generalSchedule.classList.add("hidden");
  } else if (tabName === "general") {
    // Activate general tab
    generalTab.className = "tab-button px-8 py-4 text-sm font-medium text-indigo-600 bg-indigo-50 border-b-2 border-indigo-500";
    monthlyTab.className = "tab-button px-8 py-4 text-sm font-medium text-gray-500 hover:text-gray-700 hover:bg-gray-50 border-b-2 border-transparent";

    // Show general content, hide monthly
    generalSchedule.classList.remove("hidden");
    monthlySchedule.classList.add("hidden");
  }
}

// Function untuk validasi form jadwal umum
function validateGeneralScheduleForm() {
  const form = document.getElementById("generalScheduleForm");
  const timeInputs = form.querySelectorAll('input[type="time"]');
  let isValid = true;
  let errorMessage = "";

  // Validasi setiap input waktu
  timeInputs.forEach((input) => {
    if (!input.value || input.value === "") {
      isValid = false;
      input.classList.add("border-red-500");
      errorMessage = "Harap isi semua waktu yang diperlukan";
    } else {
      input.classList.remove("border-red-500");
    }
  });

  // Validasi logika waktu untuk setiap hari
  const days = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu"];

  days.forEach((day) => {
    const startArrival = form.querySelector(`input[name="start_arrival_${day}"]`);
    const lateArrival = form.querySelector(`input[name="late_arrival_${day}"]`);
    const departureTime = form.querySelector(`input[name="departure_time_${day}"]`);

    if (startArrival && lateArrival && departureTime) {
      const startTime = startArrival.value;
      const lateTime = lateArrival.value;
      const endTime = departureTime.value;

      // Validasi urutan waktu
      if (startTime >= lateTime) {
        isValid = false;
        startArrival.classList.add("border-red-500");
        lateArrival.classList.add("border-red-500");
        errorMessage = `Jam mulai absensi harus lebih awal dari batas terlambat untuk hari ${day}`;
      }

      if (lateTime >= endTime) {
        isValid = false;
        lateArrival.classList.add("border-red-500");
        departureTime.classList.add("border-red-500");
        errorMessage = `Batas terlambat harus lebih awal dari jam pulang untuk hari ${day}`;
      }
    }
  });

  if (!isValid) {
    showNotification(errorMessage, "error");
    return false;
  }

  return true;
}

// Function untuk membuka modal edit jadwal
function openScheduleModal(day) {
  currentEditingDay = day;
  const modal = document.getElementById("scheduleModal");
  const modalDate = document.getElementById("modalDate");
  const isHolidayCheckbox = document.getElementById("isHoliday");
  const scheduleInputs = document.getElementById("scheduleInputs");

  modalDate.textContent = day;

  // Load existing data jika ada
  const existingData = window.scheduleData[day] || {};

  // Set checkbox libur
  isHolidayCheckbox.checked = existingData.is_holiday || false;

  // Set input values
  document.getElementById("startArrival").value = (existingData.start_arrival || "06:00:00").substring(0, 5);
  document.getElementById("lateArrival").value = (existingData.late_arrival || "07:00:00").substring(0, 5);
  document.getElementById("departureTime").value = (existingData.departure_time || "15:00:00").substring(0, 5);
  document.getElementById("keterangan").value = existingData.keterangan || "";

  // Toggle visibility berdasarkan status libur
  toggleScheduleInputs();

  modal.classList.remove("hidden");

  // Add event listener untuk checkbox
  isHolidayCheckbox.addEventListener("change", toggleScheduleInputs);
}

function toggleScheduleInputs() {
  const isHolidayCheckbox = document.getElementById("isHoliday");
  const scheduleInputs = document.getElementById("scheduleInputs");

  if (isHolidayCheckbox.checked) {
    scheduleInputs.style.opacity = "0.5";
    scheduleInputs.style.pointerEvents = "none";
  } else {
    scheduleInputs.style.opacity = "1";
    scheduleInputs.style.pointerEvents = "auto";
  }
}

function closeScheduleModal() {
  const modal = document.getElementById("scheduleModal");
  modal.classList.add("hidden");
  currentEditingDay = null;
}

function saveSchedule() {
  if (!currentEditingDay) return;

  const isHoliday = document.getElementById("isHoliday").checked;
  const startArrival = document.getElementById("startArrival").value + ":00";
  const lateArrival = document.getElementById("lateArrival").value + ":00";
  const departureTime = document.getElementById("departureTime").value + ":00";
  const keterangan = document.getElementById("keterangan").value;

  // Validasi waktu jika bukan libur
  if (!isHoliday) {
    if (!startArrival || !lateArrival || !departureTime) {
      showNotification("Semua field waktu harus diisi", "error");
      return;
    }

    if (startArrival >= lateArrival || lateArrival >= departureTime) {
      showNotification("Urutan waktu tidak valid", "error");
      return;
    }
  }

  // Buat data dalam format yang sesuai dengan backend
  const scheduleData = {
    year: window.currentYear,
    month: window.currentMonth,
    schedule_data: {
      [currentEditingDay]: {
        start_arrival: startArrival,
        late_arrival: lateArrival,
        departure_time: departureTime,
        is_holiday: isHoliday,
        keterangan: keterangan || null,
      },
    },
  };

  // Kirim ke server
  fetch("/simpan_jadwal_bulanan", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(scheduleData),
  })
    .then((response) => response.json())
    .then((data) => {
      if (data.success) {
        // Update data lokal
        window.scheduleData[currentEditingDay] = {
          start_arrival: startArrival,
          late_arrival: lateArrival,
          departure_time: departureTime,
          is_holiday: isHoliday,
          keterangan: keterangan,
        };

        // Update tampilan calendar
        updateCalendarDay(currentEditingDay, window.scheduleData[currentEditingDay]);

        closeScheduleModal();
        showNotification("Jadwal berhasil disimpan", "success");
      } else {
        showNotification(data.message || "Gagal menyimpan jadwal", "error");
      }
    })
    .catch((error) => {
      console.error("Error:", error);
      showNotification("Gagal menyimpan jadwal", "error");
    });
}

// Function untuk reset jadwal ke default
function resetToDefault() {
  if (!currentEditingDay) return;

  // Konfirmasi dari user
  if (!confirm(`Apakah Anda yakin ingin mereset jadwal tanggal ${currentEditingDay} ke pengaturan default?`)) {
    return;
  }

  // Kirim request untuk delete jadwal khusus tanggal ini
  fetch("/delete_daily_schedule", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      day: currentEditingDay,
      year: window.currentYear,
      month: window.currentMonth,
    }),
  })
    .then((response) => response.json())
    .then((data) => {
      if (data.success) {
        // Update UI
        showNotification("Jadwal berhasil direset ke default", "success");

        // Remove data dari window.scheduleData
        delete window.scheduleData[currentEditingDay];

        // Update tampilan calendar day
        updateCalendarDay(currentEditingDay, null);

        // Close modal
        closeScheduleModal();
      } else {
        showNotification(data.message || "Gagal mereset jadwal", "error");
      }
    })
    .catch((error) => {
      console.error("Error:", error);
      showNotification("Gagal mereset jadwal", "error");
    });
}

// Function untuk update tampilan calendar day
function updateCalendarDay(day, scheduleData) {
  const calendarDays = document.querySelectorAll(".calendar-day");

  calendarDays.forEach((dayElement) => {
    const dayText = dayElement.querySelector(".font-semibold");
    if (dayText && dayText.textContent.trim() == day) {
      const scheduleInfo = dayElement.querySelector(".text-xs");

      if (scheduleData === null) {
        // Reset ke default
        scheduleInfo.innerHTML = '<div class="text-xs text-gray-400">Default</div>';
        dayElement.className = "calendar-day p-3 border rounded-lg cursor-pointer transition-all duration-300 hover:bg-gray-50 bg-white border-gray-200";
      } else if (scheduleData.is_holiday) {
        // Set sebagai libur
        scheduleInfo.innerHTML = '<span class="text-red-600 font-semibold">Libur</span>';
        dayElement.className = "calendar-day p-3 border rounded-lg cursor-pointer transition-all duration-300 hover:bg-gray-50 bg-red-100 border-red-300 ring-2 ring-blue-300";
      } else {
        // Set jadwal khusus
        scheduleInfo.innerHTML = `<div>${scheduleData.start_arrival.substring(0, 5)} - ${scheduleData.departure_time.substring(0, 5)}</div>`;
        dayElement.className = "calendar-day p-3 border rounded-lg cursor-pointer transition-all duration-300 hover:bg-gray-50 bg-white border-gray-200 ring-2 ring-blue-300";
      }
    }
  });
}

// Function untuk show notification
function showNotification(message, type = "success") {
  const notification = document.getElementById("notification");
  const notificationText = document.getElementById("notification-text");

  notificationText.textContent = message;

  // Set warna berdasarkan type
  notification.className = notification.className.replace(/bg-\w+-\d+/, "");
  if (type === "error") {
    notification.classList.add("bg-red-500");
  } else {
    notification.classList.add("bg-green-500");
  }

  notification.classList.remove("hidden");

  setTimeout(() => {
    notification.classList.add("hidden");
  }, 3000);
}

// Function untuk logout modal
function showLogoutModal() {
  document.getElementById("logoutModal").classList.remove("hidden");
}

function hideLogoutModal() {
  document.getElementById("logoutModal").classList.add("hidden");
}

// Close modal when clicking outside
document.addEventListener("click", function (event) {
  const modal = document.getElementById("scheduleModal");
  const modalContent = document.getElementById("scheduleModalContent");

  if (event.target === modal && !modalContent.contains(event.target)) {
    closeScheduleModal();
  }

  const logoutModal = document.getElementById("logoutModal");
  const logoutModalContent = document.getElementById("logoutModalContent");

  if (event.target === logoutModal && !logoutModalContent.contains(event.target)) {
    hideLogoutModal();
  }
});

// ESC key untuk close modal
document.addEventListener("keydown", function (event) {
  if (event.key === "Escape") {
    closeScheduleModal();
    hideLogoutModal();
  }
});

// Initialize
document.addEventListener("DOMContentLoaded", function () {
  console.log("Jadwal Bulanan loaded");
  console.log("Current data:", window.scheduleData);

  // Set tab aktif pertama kali (monthly)
  switchTab("monthly");

  // Add event listeners untuk form jadwal umum
  const generalForm = document.getElementById("generalScheduleForm");
  if (generalForm) {
    // Add time input validation on change
    const timeInputs = generalForm.querySelectorAll('input[type="time"]');
    timeInputs.forEach((input) => {
      input.addEventListener("change", function () {
        // Remove error styling when user corrects input
        this.classList.remove("border-red-500");
      });

      input.addEventListener("blur", function () {
        // Validate time format
        if (this.value && !this.value.match(/^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$/)) {
          this.classList.add("border-red-500");
          showNotification("Format waktu tidak valid", "error");
        }
      });
    });
  }

  // Add keyboard shortcuts
  document.addEventListener("keydown", function (e) {
    // Alt+1 untuk tab bulanan
    if (e.altKey && e.key === "1") {
      e.preventDefault();
      switchTab("monthly");
    }
    // Alt+2 untuk tab umum
    if (e.altKey && e.key === "2") {
      e.preventDefault();
      switchTab("general");
    }
  });
});

// Function untuk switch tab antara jadwal bulanan dan jadwal umum
function switchTab(tabName) {
  // Update tab buttons
  const monthlyTab = document.getElementById("monthlyTab");
  const generalTab = document.getElementById("generalTab");

  // Update tab content
  const monthlySchedule = document.getElementById("monthlySchedule");
  const generalSchedule = document.getElementById("generalSchedule");

  if (tabName === "monthly") {
    // Activate monthly tab
    monthlyTab.className = "tab-button px-8 py-4 text-sm font-medium text-indigo-600 bg-indigo-50 border-b-2 border-indigo-500";
    generalTab.className = "tab-button px-8 py-4 text-sm font-medium text-gray-500 hover:text-gray-700 hover:bg-gray-50 border-b-2 border-transparent";

    // Show monthly content, hide general
    monthlySchedule.classList.remove("hidden");
    generalSchedule.classList.add("hidden");
  } else if (tabName === "general") {
    // Activate general tab
    generalTab.className = "tab-button px-8 py-4 text-sm font-medium text-indigo-600 bg-indigo-50 border-b-2 border-indigo-500";
    monthlyTab.className = "tab-button px-8 py-4 text-sm font-medium text-gray-500 hover:text-gray-700 hover:bg-gray-50 border-b-2 border-transparent";

    // Show general content, hide monthly
    generalSchedule.classList.remove("hidden");
    monthlySchedule.classList.add("hidden");
  }
}

// Function untuk validasi form jadwal umum
function validateGeneralScheduleForm() {
  const form = document.getElementById("generalScheduleForm");
  const timeInputs = form.querySelectorAll('input[type="time"]');
  let isValid = true;
  let errorMessage = "";

  // Validasi setiap input waktu
  timeInputs.forEach((input) => {
    if (!input.value || input.value === "") {
      isValid = false;
      input.classList.add("border-red-500");
      errorMessage = "Harap isi semua waktu yang diperlukan";
    } else {
      input.classList.remove("border-red-500");
    }
  });

  // Validasi logika waktu untuk setiap hari
  const days = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu"];

  days.forEach((day) => {
    const startArrival = form.querySelector(`input[name="start_arrival_${day}"]`);
    const lateArrival = form.querySelector(`input[name="late_arrival_${day}"]`);
    const departureTime = form.querySelector(`input[name="departure_time_${day}"]`);

    if (startArrival && lateArrival && departureTime) {
      const startTime = startArrival.value;
      const lateTime = lateArrival.value;
      const endTime = departureTime.value;

      // Validasi urutan waktu
      if (startTime >= lateTime) {
        isValid = false;
        startArrival.classList.add("border-red-500");
        lateArrival.classList.add("border-red-500");
        errorMessage = `Jam mulai absensi harus lebih awal dari batas terlambat untuk hari ${day}`;
      }

      if (lateTime >= endTime) {
        isValid = false;
        lateArrival.classList.add("border-red-500");
        departureTime.classList.add("border-red-500");
        errorMessage = `Batas terlambat harus lebih awal dari jam pulang untuk hari ${day}`;
      }
    }
  });

  if (!isValid) {
    showNotification(errorMessage, "error");
    return false;
  }

  return true;
}

// Function untuk reset jadwal ke default
function resetToDefault() {
  if (!currentEditingDay) return;

  // Konfirmasi dari user
  if (!confirm(`Apakah Anda yakin ingin mereset jadwal tanggal ${currentEditingDay} ke pengaturan default?`)) {
    return;
  }

  // Kirim request untuk delete jadwal khusus tanggal ini
  fetch("/delete_daily_schedule", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      day: currentEditingDay,
      year: window.currentYear,
      month: window.currentMonth,
    }),
  })
    .then((response) => response.json())
    .then((data) => {
      if (data.success) {
        // Update UI
        showNotification("Jadwal berhasil direset ke default", "success");

        // Remove data dari window.scheduleData
        delete window.scheduleData[currentEditingDay];

        // Update tampilan calendar day
        updateCalendarDay(currentEditingDay, null);

        // Close modal
        closeScheduleModal();
      } else {
        showNotification(data.message || "Gagal mereset jadwal", "error");
      }
    })
    .catch((error) => {
      console.error("Error:", error);
      showNotification("Gagal mereset jadwal", "error");
    });
}

// Function untuk update tampilan calendar day
function updateCalendarDay(day, scheduleData) {
  const calendarDays = document.querySelectorAll(".calendar-day");

  calendarDays.forEach((dayElement) => {
    const dayText = dayElement.querySelector(".font-semibold");
    if (dayText && dayText.textContent.trim() == day) {
      const scheduleInfo = dayElement.querySelector(".text-xs");

      if (scheduleData === null) {
        // Reset ke default
        scheduleInfo.innerHTML = '<div class="text-xs text-gray-400">Default</div>';
        dayElement.className = "calendar-day p-3 border rounded-lg cursor-pointer transition-all duration-300 hover:bg-gray-50 bg-white border-gray-200";
      } else if (scheduleData.is_holiday) {
        // Set sebagai libur
        scheduleInfo.innerHTML = '<span class="text-red-600 font-semibold">Libur</span>';
        dayElement.className = "calendar-day p-3 border rounded-lg cursor-pointer transition-all duration-300 hover:bg-gray-50 bg-red-100 border-red-300 ring-2 ring-blue-300";
      } else {
        // Set jadwal khusus
        scheduleInfo.innerHTML = `<div>${scheduleData.start_arrival.substring(0, 5)} - ${scheduleData.departure_time.substring(0, 5)}</div>`;
        dayElement.className = "calendar-day p-3 border rounded-lg cursor-pointer transition-all duration-300 hover:bg-gray-50 bg-white border-gray-200 ring-2 ring-blue-300";
      }
    }
  });
}

// Function untuk show notification
function showNotification(message, type = "success") {
  const notification = document.getElementById("notification");
  const notificationText = document.getElementById("notification-text");

  notificationText.textContent = message;

  // Set warna berdasarkan type
  notification.className = notification.className.replace(/bg-\w+-\d+/, "");
  if (type === "error") {
    notification.classList.add("bg-red-500");
  } else {
    notification.classList.add("bg-green-500");
  }

  notification.classList.remove("hidden");

  setTimeout(() => {
    notification.classList.add("hidden");
  }, 3000);
}

// Function untuk logout modal
function showLogoutModal() {
  document.getElementById("logoutModal").classList.remove("hidden");
}

function hideLogoutModal() {
  document.getElementById("logoutModal").classList.add("hidden");
}

// Close modal when clicking outside
document.addEventListener("click", function (event) {
  const modal = document.getElementById("scheduleModal");
  const modalContent = document.getElementById("scheduleModalContent");

  if (event.target === modal && !modalContent.contains(event.target)) {
    closeScheduleModal();
  }

  const logoutModal = document.getElementById("logoutModal");
  const logoutModalContent = document.getElementById("logoutModalContent");

  if (event.target === logoutModal && !logoutModalContent.contains(event.target)) {
    hideLogoutModal();
  }
});

// ESC key untuk close modal
document.addEventListener("keydown", function (event) {
  if (event.key === "Escape") {
    closeScheduleModal();
    hideLogoutModal();
  }
});

// Initialize
document.addEventListener("DOMContentLoaded", function () {
  console.log("Jadwal Bulanan loaded");
  console.log("Current data:", window.scheduleData);

  // Set tab aktif pertama kali (monthly)
  switchTab("monthly");

  // Add event listeners untuk form jadwal umum
  const generalForm = document.getElementById("generalScheduleForm");
  if (generalForm) {
    // Add time input validation on change
    const timeInputs = generalForm.querySelectorAll('input[type="time"]');
    timeInputs.forEach((input) => {
      input.addEventListener("change", function () {
        // Remove error styling when user corrects input
        this.classList.remove("border-red-500");
      });

      input.addEventListener("blur", function () {
        // Validate time format
        if (this.value && !this.value.match(/^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$/)) {
          this.classList.add("border-red-500");
          showNotification("Format waktu tidak valid", "error");
        }
      });
    });
  }

  // Add keyboard shortcuts
  document.addEventListener("keydown", function (e) {
    // Alt+1 untuk tab bulanan
    if (e.altKey && e.key === "1") {
      e.preventDefault();
      switchTab("monthly");
    }
    // Alt+2 untuk tab umum
    if (e.altKey && e.key === "2") {
      e.preventDefault();
      switchTab("general");
    }
  });
});
