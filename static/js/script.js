/* =========================================================
   FitTrack AI - Vanilla JavaScript
   ========================================================= */

/* ---------- Public navbar toggle ---------- */
document.addEventListener("DOMContentLoaded", () => {
  const navToggle = document.getElementById("navToggle");
  const navLinks = document.getElementById("navLinks");
  if (navToggle && navLinks) {
    navToggle.addEventListener("click", () => navLinks.classList.toggle("open"));
  }

  const sidebarToggle = document.getElementById("sidebarToggle");
  const sidebar = document.getElementById("sidebar");
  if (sidebarToggle && sidebar) {
    sidebarToggle.addEventListener("click", () => sidebar.classList.toggle("open"));
  }

  // Set default dates on any empty date inputs (today)
  const today = new Date().toISOString().split("T")[0];
  document.querySelectorAll('input[type="date"]').forEach((input) => {
    if (!input.value) input.value = today;
  });

  // Run initial BMI calc if the elements exist (fitness page)
  if (document.getElementById("bmiHeight") && document.getElementById("bmiWeight")) {
    calculateBMI();
  }

  // Signup validation wiring
  const signupForm = document.getElementById("signupForm");
  if (signupForm) {
    signupForm.addEventListener("submit", handleSignupValidation);
  }
  const loginForm = document.getElementById("loginForm");
  if (loginForm) {
    loginForm.addEventListener("submit", handleLoginValidation);
  }
});

/* ---------- Auth tab switching ---------- */
function showAuthTab(tab) {
  document.querySelectorAll(".auth-form").forEach((f) => f.classList.remove("active"));
  document.querySelectorAll(".auth-tab").forEach((t) => t.classList.remove("active"));

  if (tab === "login") {
    document.getElementById("loginForm").classList.add("active");
    document.getElementById("loginTabBtn").classList.add("active");
  } else {
    document.getElementById("signupForm").classList.add("active");
    document.getElementById("signupTabBtn").classList.add("active");
  }
}

function showForgotPassword(e) {
  e.preventDefault();
  document.querySelectorAll(".auth-form").forEach((f) => f.classList.remove("active"));
  document.querySelectorAll(".auth-tab").forEach((t) => t.classList.remove("active"));
  document.getElementById("forgotForm").classList.add("active");
}

/* ---------- Field error helper ---------- */
function setFieldError(inputId, message) {
  const input = document.getElementById(inputId);
  const errorSpan = document.getElementById(inputId + "_error");
  if (input) input.classList.toggle("invalid", !!message);
  if (errorSpan) errorSpan.textContent = message || "";
}

/* ---------- Login validation ---------- */
function handleLoginValidation(e) {
  let valid = true;
  const email = document.getElementById("login_email").value.trim();
  const password = document.getElementById("login_password").value;

  if (!validateEmail(email)) {
    setFieldError("login_email", "Enter a valid email address.");
    valid = false;
  } else {
    setFieldError("login_email", "");
  }

  if (!password) {
    setFieldError("login_password", "Password is required.");
    valid = false;
  } else {
    setFieldError("login_password", "");
  }

  if (!valid) e.preventDefault();
}

/* ---------- Signup validation ---------- */
function handleSignupValidation(e) {
  let valid = true;

  const fullName = document.getElementById("full_name").value.trim();
  const email = document.getElementById("signup_email").value.trim();
  const age = document.getElementById("age").value;
  const height = document.getElementById("height").value;
  const weight = document.getElementById("initial_weight").value;
  const password = document.getElementById("signup_password").value;
  const confirmPassword = document.getElementById("confirm_password").value;

  if (!fullName) {
    setFieldError("full_name", "Full name is required.");
    valid = false;
  } else setFieldError("full_name", "");

  if (!validateEmail(email)) {
    setFieldError("signup_email", "Enter a valid email address.");
    valid = false;
  } else setFieldError("signup_email", "");

  if (!age || parseInt(age) <= 0 || parseInt(age) > 120) {
    setFieldError("age", "Enter a valid age.");
    valid = false;
  } else setFieldError("age", "");

  if (!height || parseFloat(height) <= 0) {
    setFieldError("height", "Height must be a positive number.");
    valid = false;
  } else setFieldError("height", "");

  if (!weight || parseFloat(weight) <= 0) {
    setFieldError("initial_weight", "Weight must be a positive number.");
    valid = false;
  } else setFieldError("initial_weight", "");

  if (!password || password.length < 6) {
    setFieldError("signup_password", "Password must be at least 6 characters.");
    valid = false;
  } else setFieldError("signup_password", "");

  if (password !== confirmPassword) {
    setFieldError("confirm_password", "Passwords do not match.");
    valid = false;
  } else setFieldError("confirm_password", "");

  if (!valid) e.preventDefault();
}

function validateEmail(email) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

/* ---------- Delete confirmation ---------- */
function confirmDelete(itemLabel) {
  return confirm(`Are you sure you want to delete this ${itemLabel}? This cannot be undone.`);
}

/* ---------- Tracker section tabs (fitness.html / diet-profile.html) ---------- */
function showSection(sectionId, btn) {
  document.querySelectorAll(".tracker-section").forEach((s) => s.classList.remove("active"));
  document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
  document.getElementById(sectionId).classList.add("active");
  btn.classList.add("active");
}

/* ---------- BMI Calculator ---------- */
function calculateBMI() {
  const heightInput = document.getElementById("bmiHeight");
  const weightInput = document.getElementById("bmiWeight");
  if (!heightInput || !weightInput) return;

  const heightCm = parseFloat(heightInput.value);
  const weightKg = parseFloat(weightInput.value);
  const valueEl = document.getElementById("bmiValue");
  const categoryEl = document.getElementById("bmiCategory");
  const pointerEl = document.getElementById("bmiPointer");

  if (!heightCm || !weightKg || heightCm <= 0 || weightKg <= 0) {
    valueEl.textContent = "--";
    categoryEl.textContent = "Enter your height and weight";
    return;
  }

  const heightM = heightCm / 100;
  const bmi = weightKg / (heightM * heightM);
  const rounded = Math.round(bmi * 10) / 10;

  valueEl.textContent = rounded;

  let category, pct;
  if (bmi < 18.5) { category = "Underweight"; pct = mapRange(bmi, 10, 18.5, 0, 25); }
  else if (bmi < 25) { category = "Normal weight"; pct = mapRange(bmi, 18.5, 25, 25, 50); }
  else if (bmi < 30) { category = "Overweight"; pct = mapRange(bmi, 25, 30, 50, 75); }
  else { category = "Obesity"; pct = mapRange(bmi, 30, 45, 75, 100); }

  categoryEl.textContent = category;
  pct = Math.min(100, Math.max(0, pct));
  if (pointerEl) pointerEl.style.setProperty("--pos", pct + "%");
}

function mapRange(value, inMin, inMax, outMin, outMax) {
  const clamped = Math.min(Math.max(value, inMin), inMax);
  return ((clamped - inMin) / (inMax - inMin)) * (outMax - outMin) + outMin;
}

/* ---------- Dashboard Charts (Chart.js, real data from Flask/MySQL) ---------- */
function loadDashboardCharts() {
  fetch("/api/chart-data")
    .then((res) => res.json())
    .then((data) => {
      const shortLabels = data.labels.map((d) => d.slice(5)); // MM-DD

      new Chart(document.getElementById("weightChart"), {
        type: "line",
        data: {
          labels: shortLabels,
          datasets: [{
            label: "Weight (kg)",
            data: data.weight,
            borderColor: "#16a34a",
            backgroundColor: "rgba(22,163,74,0.1)",
            spanGaps: true,
            tension: 0.3,
            fill: true,
          }],
        },
        options: { responsive: true, plugins: { legend: { display: false } } },
      });

      new Chart(document.getElementById("activityChart"), {
        type: "bar",
        data: {
          labels: shortLabels,
          datasets: [
            { label: "Steps (÷100)", data: data.steps.map((s) => Math.round(s / 100)), backgroundColor: "#0891b2" },
            { label: "Workout min", data: data.workout_minutes, backgroundColor: "#16a34a" },
          ],
        },
        options: { responsive: true, plugins: { legend: { position: "bottom" } } },
      });

      new Chart(document.getElementById("calorieChart"), {
        type: "line",
        data: {
          labels: shortLabels,
          datasets: [
            { label: "Consumed", data: data.calories_consumed, borderColor: "#f59e0b", tension: 0.3 },
            {
              label: "Target",
              data: data.labels.map(() => data.calorie_target),
              borderColor: "#dc2626",
              borderDash: [6, 4],
              pointRadius: 0,
            },
          ],
        },
        options: { responsive: true, plugins: { legend: { position: "bottom" } } },
      });
    })
    .catch((err) => console.error("Failed to load chart data:", err));
}
