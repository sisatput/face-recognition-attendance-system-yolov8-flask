function exportData() {
  const start = document.getElementById("start_date").value;
  const end = document.getElementById("end_date").value;
  if (start && end) {
    window.location.href = `/export_excel/${start}_${end}`;
  } else {
    showPopup("Pilih rentang tanggal terlebih dahulu untuk ekspor data.");
  }
}

function showDeleteFilterModal() {
  const start = document.getElementById("start_date").value;
  const end = document.getElementById("end_date").value;
  if (start && end) {
    const modal = document.getElementById("deleteFilterModal");
    const modalContent = document.getElementById("deleteFilterModalContent");
    modal.classList.remove("hidden");
    setTimeout(() => {
      modalContent.classList.remove("scale-95");
      modalContent.classList.add("scale-100");
    }, 10);
  } else {
    showPopup("Pilih rentang tanggal untuk menghapus data filter.");
  }
}

function hideDeleteFilterModal() {
  const modal = document.getElementById("deleteFilterModal");
  const modalContent = document.getElementById("deleteFilterModalContent");
  modalContent.classList.remove("scale-100");
  modalContent.classList.add("scale-95");
  setTimeout(() => {
    modal.classList.add("hidden");
  }, 300);
}
function deleteFilterDataConfirmed() {
  const start = document.getElementById("start_date").value;
  const end = document.getElementById("end_date").value;
  fetch("/delete_absensi", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ date_range: start + "_" + end }),
  })
    .then((response) => response.json())
    .then((data) => {
      showPopup(data.message);
      hideDeleteFilterModal();
      setTimeout(() => {
        location.reload();
      }, 1500);
    })
    .catch((error) => {
      console.error("Error:", error);
      showPopup("Terjadi kesalahan saat menghapus data.");
    });
}

function showDeleteAllModal() {
  const modal = document.getElementById("deleteAllModal");
  const modalContent = document.getElementById("deleteAllModalContent");
  modal.classList.remove("hidden");
  setTimeout(() => {
    modalContent.classList.remove("scale-95");
    modalContent.classList.add("scale-100");
  }, 10);
}

function hideDeleteAllModal() {
  const modal = document.getElementById("deleteAllModal");
  const modalContent = document.getElementById("deleteAllModalContent");
  modalContent.classList.remove("scale-100");
  modalContent.classList.add("scale-95");
  setTimeout(() => {
    modal.classList.add("hidden");
  }, 300);
}
// Modifikasi fungsi ini untuk menampilkan modal kedua
function deleteAllDataConfirmed() {
  // Sembunyikan modal pertama
  hideDeleteAllModal();

  // Tampilkan modal konfirmasi kedua
  setTimeout(() => {
    const modal = document.getElementById("finalDeleteAllModal");
    const modalContent = document.getElementById("finalDeleteAllModalContent");
    modal.classList.remove("hidden");
    setTimeout(() => {
      modalContent.classList.remove("scale-95");
      modalContent.classList.add("scale-100");
    }, 10);
  }, 300); // Tunggu hingga modal pertama selesai tertutup
}

// Fungsi untuk menyembunyikan modal konfirmasi kedua
function hideFinalDeleteAllModal() {
  const modal = document.getElementById("finalDeleteAllModal");
  const modalContent = document.getElementById("finalDeleteAllModalContent");
  modalContent.classList.remove("scale-100");
  modalContent.classList.add("scale-95");
  setTimeout(() => {
    modal.classList.add("hidden");
  }, 300);
}

// Fungsi untuk benar-benar menghapus semua data
function finalDeleteAllConfirmed() {
  fetch("/delete_absensi_all", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  })
    .then((response) => response.json())
    .then((data) => {
      showPopup(data.message);
      hideFinalDeleteAllModal();
      setTimeout(() => {
        location.reload();
      }, 1500);
    })
    .catch((error) => {
      console.error("Error:", error);
      showPopup("Terjadi kesalahan saat menghapus semua data.");
    });
}

function showPopup(message) {
  const popup = document.getElementById("popup");
  popup.textContent = message;
  popup.classList.remove("hidden");
  setTimeout(() => {
    popup.classList.add("hidden");
  }, 3000);
}

// Fungsi untuk modal logout
function showLogoutModal() {
  const modal = document.getElementById("logoutModal");
  const modalContent = document.getElementById("logoutModalContent");
  modal.classList.remove("hidden");
  setTimeout(() => {
    modalContent.classList.remove("scale-95");
    modalContent.classList.add("scale-100");
  }, 10);
}

function hideLogoutModal() {
  const modal = document.getElementById("logoutModal");
  const modalContent = document.getElementById("logoutModalContent");
  modalContent.classList.remove("scale-100");
  modalContent.classList.add("scale-95");
  setTimeout(() => {
    modal.classList.add("hidden");
  }, 300);
}

// Variabel untuk menyimpan data yang dipilih
let selectedItems = [];

// Fungsi untuk toggle semua checkbox
function toggleAllCheckboxes(source) {
  const checkboxes = document.querySelectorAll(".row-checkbox");
  checkboxes.forEach((checkbox) => {
    checkbox.checked = source.checked;
    updateSelectedItems(checkbox);
  });
  updateDeleteButtonState();
}

// Event listener untuk checkbox individual
document.addEventListener("DOMContentLoaded", function () {
  document.querySelectorAll(".row-checkbox").forEach((checkbox) => {
    checkbox.addEventListener("change", function () {
      updateSelectedItems(this);
      updateDeleteButtonState();
    });
  });
});

// Fungsi untuk memperbarui array data yang dipilih
function updateSelectedItems(checkbox) {
  const id = checkbox.getAttribute("data-id");
  const name = checkbox.getAttribute("data-name");
  const date = checkbox.getAttribute("data-date");

  if (checkbox.checked) {
    if (!selectedItems.some((item) => item.id === id)) {
      selectedItems.push({ id, name, date });
    }
  } else {
    selectedItems = selectedItems.filter((item) => item.id !== id);
  }

  // Update tampilan counter
  document.getElementById("selectedCount").textContent = selectedItems.length;
}

// Fungsi untuk mengaktifkan/menonaktifkan tombol hapus
function updateDeleteButtonState() {
  const deleteButton = document.getElementById("deleteSelectedBtn");
  deleteButton.disabled = selectedItems.length === 0;
}

// Fungsi untuk menampilkan modal konfirmasi penghapusan
function showDeleteSelectedModal() {
  if (selectedItems.length === 0) return;

  const modal = document.getElementById("deleteSelectedModal");
  const modalContent = document.getElementById("deleteSelectedModalContent");
  const previewContainer = document.getElementById("selectedItemsPreview");
  const countSpan = document.getElementById("selectedItemsCount");

  // Update jumlah item yang dipilih
  countSpan.textContent = selectedItems.length;

  // Buat preview item yang akan dihapus
  previewContainer.innerHTML = "";
  selectedItems.forEach((item, index) => {
    if (index < 5) {
      // Batasi tampilan preview
      const itemEl = document.createElement("div");
      itemEl.className = "py-1 border-b border-gray-200 last:border-0";
      itemEl.innerHTML = `<span class="font-medium">${item.name}</span> (${item.date})`;
      previewContainer.appendChild(itemEl);
    } else if (index === 5) {
      const moreEl = document.createElement("div");
      moreEl.className = "py-1 text-center italic";
      moreEl.textContent = `... dan ${selectedItems.length - 5} data lainnya`;
      previewContainer.appendChild(moreEl);
    }
  });

  // Tampilkan modal
  modal.classList.remove("hidden");
  setTimeout(() => {
    modalContent.classList.remove("scale-95");
    modalContent.classList.add("scale-100");
  }, 10);
}

// Fungsi untuk menyembunyikan modal
function hideDeleteSelectedModal() {
  const modal = document.getElementById("deleteSelectedModal");
  const modalContent = document.getElementById("deleteSelectedModalContent");
  modalContent.classList.remove("scale-100");
  modalContent.classList.add("scale-95");
  setTimeout(() => {
    modal.classList.add("hidden");
  }, 300);
}

// Fungsi untuk menghapus data yang dipilih
function deleteSelectedData() {
  const ids = selectedItems.map((item) => item.id);

  fetch("/delete_selected_absensi", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ids: ids }),
  })
    .then((response) => response.json())
    .then((data) => {
      showPopup(data.message);
      hideDeleteSelectedModal();

      // Reset pilihan
      selectedItems = [];
      document.getElementById("selectAll").checked = false;

      // Reload halaman setelah berhasil
      setTimeout(() => {
        location.reload();
      }, 1500);
    })
    .catch((error) => {
      console.error("Error:", error);
      showPopup("Terjadi kesalahan saat menghapus data.");
    });
}
