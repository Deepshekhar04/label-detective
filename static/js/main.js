/*
 * Label Detective - Interactive UI JavaScript
 */

// Form validation
document.addEventListener("DOMContentLoaded", function () {
  const scanForm = document.getElementById("scanForm");
  if (scanForm) {
    scanForm.addEventListener("submit", function (e) {
      const inputType = document.getElementById("input_type").value;

      if (inputType === "text") {
        const text = document.getElementById("ingredient_text").value.trim();
        if (!text) {
          e.preventDefault();
          alert("Please enter an ingredient list");
          return false;
        }
      } else if (inputType === "image") {
        const file = document.getElementById("ingredient_image").files[0];
        if (!file) {
          e.preventDefault();
          alert("Please select an image");
          return false;
        }
      }
    });
  }
});

// Tab switching
function switchTab(tabName) {
  // Hide all tab contents
  document.querySelectorAll(".tab-content").forEach((content) => {
    content.classList.remove("active");
  });

  // Deactivate all tab buttons
  document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.classList.remove("active");
  });

  // Show selected tab
  const selectedTab = document.getElementById(`tab-${tabName}`);
  if (selectedTab) {
    selectedTab.classList.add("active");
  }

  // Activate selected button
  event.target.classList.add("active");

  // Update hidden input
  const inputTypeField = document.getElementById("input_type");
  if (inputTypeField) {
    inputTypeField.value = tabName;
  }
}

// Image preview
function previewImage(input) {
  const preview = document.getElementById("imagePreview");
  if (!preview) return;

  if (input.files && input.files[0]) {
    const reader = new FileReader();

    reader.onload = function (e) {
      preview.innerHTML = `<img src="${e.target.result}" alt="Preview" style="max-width: 100%; border-radius: 0.5rem; margin-top: 1rem;">`;
    };

    reader.readAsDataURL(input.files[0]);
  } else {
    preview.innerHTML = "";
  }
}

// Accordion toggle
function toggleAccordion(id) {
  const content = document.getElementById(`${id}-content`);
  if (content) {
    content.classList.toggle("active");
  }
}

// Fill example text
function fillExample(text) {
  const textArea = document.getElementById("ingredient_text");
  if (textArea) {
    textArea.value = text;

    // Switch to text tab
    const textTab = document.getElementById("tab-text");
    const textButton = document.querySelector(
      "[onclick=\"switchTab('text')\"]"
    );

    if (textTab && textButton) {
      document
        .querySelectorAll(".tab-content")
        .forEach((t) => t.classList.remove("active"));
      document
        .querySelectorAll(".tab-btn")
        .forEach((b) => b.classList.remove("active"));

      textTab.classList.add("active");
      textButton.classList.add("active");

      document.getElementById("input_type").value = "text";
    }

    // Scroll to top
    window.scrollTo({ top: 0, behavior: "smooth" });
  }
}

// Save to history (API call)
function saveToHistory() {
  const sessionId = "{{ session_id }}"; // This will be replaced by Jinja in template
  const verdict = "{{ verdict.verdict }}";
  const summary = "{{ verdict.summary }}";

  fetch("/api/save_to_history", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      session_id: sessionId,
      summary: summary,
      verdict: verdict,
      timestamp: new Date().toISOString(),
    }),
  })
    .then((response) => response.json())
    .then((data) => {
      if (data.success) {
        showToast("✓ Saved to history!");
      } else {
        showToast("✗ Failed to save");
      }
    })
    .catch((error) => {
      console.error("Error:", error);
      showToast("✗ Error saving to history");
    });
}

// Block ingredient (API call)
function blockIngredient() {
  const select = document.getElementById("blockIngredientSelect");
  if (!select) return;

  const ingredient = select.value;

  fetch("/api/block_ingredient", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ ingredient: ingredient }),
  })
    .then((response) => response.json())
    .then((data) => {
      if (data.success) {
        showToast(`✓ Blocked "${ingredient}"`);
        closeModal();
      } else {
        showToast("✗ Failed to block ingredient");
      }
    })
    .catch((error) => {
      console.error("Error:", error);
      showToast("✗ Error blocking ingredient");
    });
}

// Show/hide modal
function showBlockModal() {
  const modal = document.getElementById("blockModal");
  if (modal) {
    modal.style.display = "flex";
  }
}

function closeModal() {
  const modal = document.getElementById("blockModal");
  if (modal) {
    modal.style.display = "none";
  }
}

// Report wrong (placeholder)
function reportWrong() {
  showToast("⚠️ Thank you! Feedback feature coming soon.");
}

// Toast notification
function showToast(message) {
  // Remove existing toast if any
  const existingToast = document.querySelector(".toast");
  if (existingToast) {
    existingToast.remove();
  }

  // Create new toast
  const toast = document.createElement("div");
  toast.className = "toast";
  toast.textContent = message;
  document.body.appendChild(toast);

  // Show toast with animation
  setTimeout(() => {
    toast.classList.add("show");
  }, 100);

  // Hide and remove toast after 3 seconds
  setTimeout(() => {
    toast.classList.remove("show");
    setTimeout(() => {
      toast.remove();
    }, 300);
  }, 3000);
}

// Profile form - allergy management
function addAllergy() {
  const container = document.getElementById("allergies-container");
  if (!container) return;

  const row = document.createElement("div");
  row.className = "allergy-row";
  row.style.display = "flex";
  row.style.gap = "1rem";
  row.style.marginBottom = "1rem";

  row.innerHTML = `
        <input type="text" name="allergy_name" placeholder="Ingredient name" class="form-control">
        <select name="allergy_severity" class="form-control" style="max-width: 150px;">
            <option value="low">Low</option>
            <option value="moderate">Moderate</option>
            <option value="high">High</option>
        </select>
        <button type="button" onclick="removeRow(this)" class="btn btn-secondary btn-small">✕</button>
    `;

  container.appendChild(row);
}

function removeRow(button) {
  button.parentElement.remove();
}

// Accept disclaimer
function acceptDisclaimer() {
  fetch("/api/accept_disclaimer", { method: "POST" })
    .then(() => {
      const banner = document.getElementById("disclaimer");
      if (banner) {
        banner.style.display = "none";
      }
    })
    .catch((error) => console.error("Error accepting disclaimer:", error));
}

// Close modal on outside click
window.addEventListener("click", function (event) {
  const modal = document.getElementById("blockModal");
  if (modal && event.target === modal) {
    closeModal();
  }
});

// Keyboard shortcuts
document.addEventListener("keydown", function (e) {
  // Escape key closes modals
  if (e.key === "Escape") {
    closeModal();
  }
});

// Smooth scroll for anchor links
document.querySelectorAll('a[href^="#"]').forEach((anchor) => {
  anchor.addEventListener("click", function (e) {
    e.preventDefault();
    const target = document.querySelector(this.getAttribute("href"));
    if (target) {
      target.scrollIntoView({ behavior: "smooth" });
    }
  });
});

console.log("🔍 Label Detective - Client-side JavaScript loaded");
