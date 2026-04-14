// static/js/common.js

// Show modal with animation
function showModal(modalId, contentId) {
  const modal = document.getElementById(modalId);
  const modalContent = document.getElementById(contentId);
  modal.classList.remove("hidden");
  setTimeout(() => {
    modalContent.classList.remove("scale-95");
    modalContent.classList.add("scale-100");
  }, 10);
}

// Hide modal with animation
function hideModal(modalId, contentId) {
  const modal = document.getElementById(modalId);
  const modalContent = document.getElementById(contentId);
  modalContent.classList.remove("scale-100");
  modalContent.classList.add("scale-95");
  setTimeout(() => {
    modal.classList.add("hidden");
  }, 300);
}

// Show notification toast
function showPopup(message, isError = false) {
  const popup = document.getElementById("popup");
  if (!popup) return;
  
  if (popup.querySelector("span")) {
    popup.querySelector("span").textContent = message;
  }
  
  if (isError && popup.classList.contains("bg-green-500")) {
    popup.classList.remove("bg-green-500");
    popup.classList.add("bg-red-500");
  } else if (!isError && popup.classList.contains("bg-red-500")) {
    popup.classList.remove("bg-red-500");
    popup.classList.add("bg-green-500");
  }
  
  popup.classList.remove("hidden");
  setTimeout(() => {
    popup.classList.add("hidden");
  }, 3000);
}

// Logout functionality
function showLogoutModal() {
  showModal("logoutModal", "modalContent");
}

function hideLogoutModal() {
  hideModal("logoutModal", "modalContent");
}

document.addEventListener('DOMContentLoaded', function() {
  const mobileMenuToggle = document.getElementById('mobileMenuToggle');
  const navLinks = document.getElementById('navLinks');
  
  if (mobileMenuToggle && navLinks) {
    mobileMenuToggle.addEventListener('click', function() {
      navLinks.classList.toggle('hidden');
      navLinks.classList.toggle('flex');
    });
  }
});