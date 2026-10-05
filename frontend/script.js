const API_URL = "";

const table = document.getElementById("studentTable");
const searchInput = document.getElementById("searchInput");
const sortSelect = document.getElementById("sortSelect");
const totalStudents = document.getElementById("totalStudents");
const averageMarks = document.getElementById("averageMarks");
const topScore = document.getElementById("topScore");
const modal = document.getElementById("studentModal");
const addStudentBtn = document.getElementById("addStudentBtn");
const closeModal = document.getElementById("closeModal");
const studentForm = document.getElementById("studentForm");
const studentId = document.getElementById("studentId");
const studentName = document.getElementById("studentName");
const studentCourse = document.getElementById("studentCourse");
const studentMarks = document.getElementById("studentMarks");
const modalTitle = document.getElementById("modalTitle");
const modalEyebrow = document.getElementById("modalEyebrow");
const submitStudentBtn = document.getElementById("submitStudentBtn");
const message = document.getElementById("message");
const modalMessage = document.getElementById("modalMessage");
const deleteModal = document.getElementById("deleteModal");
const deleteName = document.getElementById("deleteName");
const cancelDelete = document.getElementById("cancelDelete");
const confirmDelete = document.getElementById("confirmDelete");
const studentIdHint = document.getElementById("studentIdHint");

let students = [];
let editingId = null;
let pendingDeleteId = null;
let searchTimer = null;

const knownAcronyms = new Set([
  "CSE", "ECE", "EEE", "IT", "AI", "ML", "AIML",
  "BCA", "MCA", "BBA", "MBA", "BSC", "MSC",
  "BTECH", "MTECH", "BE", "ME", "BCOM", "MCOM"
]);

function normalizeName(value) {
  return value.trim().split(/\s+/).map(word =>
    word.charAt(0).toUpperCase() + word.slice(1).toLowerCase()
  ).join(" ");
}

function normalizeCourse(value) {
  return value.trim().split(/\s+/).map(word => {
    const upper = word.toUpperCase();
    return knownAcronyms.has(upper)
      ? upper
      : word.charAt(0).toUpperCase() + word.slice(1).toLowerCase();
  }).join(" ");
}

function validateStudentInput(id, name, course, marks) {
  if (!/^\d{1,12}$/.test(id)) return "Student ID must contain 1–12 digits only.";
  if (!/^[A-Za-z ]+$/.test(name) || !name.trim()) return "Student name must contain alphabets and spaces only.";
  if (!/^[A-Za-z ]+$/.test(course) || !course.trim()) return "Course must contain alphabets and spaces only.";
  if (!Number.isFinite(marks) || marks < 0 || marks > 100) return "Marks must be between 0 and 100.";
  return null;
}

function showMessage(text, type = "error") {
  message.textContent = text;
  message.className = `message ${type}`;
}

function showModalMessage(text, type = "error") {
  modalMessage.textContent = text;
  modalMessage.className = `message ${type}`;
}

function hideMessage() {
  message.className = "message hidden";
  message.textContent = "";
}

function hideModalMessage() {
  modalMessage.className = "message hidden";
  modalMessage.textContent = "";
}

async function apiRequest(url, options = {}) {
  try {
    const headers = { ...(options.headers || {}) };
    if (options.body) {
      headers["Content-Type"] = "application/json";
    }

    const response = await fetch(`${API_URL}${url}`, {
      ...options,
      headers
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.message || "Server request failed.");
    return data;
  } catch (error) {
    if (error instanceof TypeError) {
      throw new Error("Unable to connect to server. Please start the Python backend.");
    }
    throw error;
  }
}

function renderStudents(list, searched = false) {
  table.innerHTML = "";
  if (list.length === 0) {
    table.innerHTML = `<tr><td colspan="6" class="no-result">${searched ? "Student not found" : "No students added yet"}</td></tr>`;
    return;
  }

  list.forEach(student => {
    const row = document.createElement("tr");
    row.innerHTML = `
      <td>${student.id}</td>
      <td><strong>${student.name}</strong></td>
      <td>${student.course}</td>
      <td>${student.marks}</td>
      <td><span class="status">${Number(student.marks) >= 40 ? "Passing" : "Needs attention"}</span></td>
      <td><div class="action-group">
        <button class="action-btn" onclick="editStudent('${student.id}')">Edit</button>
        <button class="action-btn delete-btn" onclick="deleteStudent('${student.id}')">Delete</button>
      </div></td>`;
    table.appendChild(row);
  });
}

function sortStudents(list) {
  const sorted = [...list];
  if (sortSelect.value === "name") sorted.sort((a, b) => a.name.localeCompare(b.name));
  if (sortSelect.value === "marks") sorted.sort((a, b) => Number(b.marks) - Number(a.marks));
  if (sortSelect.value === "id") sorted.sort((a, b) => Number(a.id) - Number(b.id));
  return sorted;
}

async function loadStudents() {
  const query = searchInput.value.trim();
  try {
    table.innerHTML = `<tr><td colspan="6" class="no-result">Loading students...</td></tr>`;
    students = await apiRequest(`/students?search=${encodeURIComponent(query)}`);
    renderStudents(sortStudents(students), Boolean(query));
    await loadStats();
    if (!query) hideMessage();
  } catch (error) {
    renderStudents([], false);
    showMessage(error.message);
  }
}

async function loadStats() {
  try {
    const stats = await apiRequest("/students/stats");
    totalStudents.textContent = stats.total_students;
    averageMarks.textContent = Number(stats.average_marks).toFixed(1);
    topScore.textContent = stats.top_score;
  } catch (error) {
    totalStudents.textContent = "—";
    averageMarks.textContent = "—";
    topScore.textContent = "—";
  }
}

function openAddModal() {
  editingId = null;
  modalEyebrow.textContent = "NEW RECORD";
  modalTitle.textContent = "Add student";
  submitStudentBtn.textContent = "Save student";
  studentId.disabled = false;
  studentIdHint.textContent = "Digits only";
  studentForm.reset();
  hideModalMessage();
  modal.classList.remove("hidden");
}

function openEditModal(student) {
  editingId = student.id;
  modalEyebrow.textContent = "EDIT RECORD";
  modalTitle.textContent = "Update student";
  submitStudentBtn.textContent = "Update student";
  studentId.value = student.id;
  studentId.disabled = true;
  studentIdHint.textContent = "Student ID is the primary key and cannot be changed.";
  studentName.value = student.name;
  studentCourse.value = student.course;
  studentMarks.value = student.marks;
  hideModalMessage();
  modal.classList.remove("hidden");
}

window.editStudent = function(id) {
  const student = students.find(item => String(item.id) === String(id));
  if (!student) return showMessage("Student not found.");
  openEditModal(student);
};

window.deleteStudent = function(id) {
  const student = students.find(item => String(item.id) === String(id));
  if (!student) return showMessage("Student not found.");
  pendingDeleteId = student.id;
  deleteName.textContent = student.name;
  deleteModal.classList.remove("hidden");
};

confirmDelete.addEventListener("click", async () => {
  if (!pendingDeleteId) return;
  try {
    await apiRequest(`/students/${pendingDeleteId}`, { method: "DELETE" });
    deleteModal.classList.add("hidden");
    pendingDeleteId = null;
    showMessage("Student deleted successfully.", "success");
    await loadStudents();
  } catch (error) {
    deleteModal.classList.add("hidden");
    showMessage(error.message);
  }
});

cancelDelete.addEventListener("click", () => {
  pendingDeleteId = null;
  deleteModal.classList.add("hidden");
});

studentForm.addEventListener("submit", async event => {
  event.preventDefault();
  const id = studentId.value.trim();
  const rawName = studentName.value.trim();
  const rawCourse = studentCourse.value.trim();
  const marks = Number(studentMarks.value);
  const validationError = validateStudentInput(id, rawName, rawCourse, marks);
  if (validationError) return showModalMessage(validationError);

  const payload = { id, name: normalizeName(rawName), course: normalizeCourse(rawCourse), marks };
  submitStudentBtn.disabled = true;
  submitStudentBtn.textContent = editingId ? "Updating..." : "Saving...";

  try {
    if (editingId) {
      await apiRequest(`/students/${editingId}`, {
        method: "PUT",
        body: JSON.stringify({ name: payload.name, course: payload.course, marks: payload.marks })
      });
      showMessage("Student updated successfully.", "success");
    } else {
      await apiRequest("/students", { method: "POST", body: JSON.stringify(payload) });
      showMessage("Student added successfully.", "success");
    }
    modal.classList.add("hidden");
    studentForm.reset();
    await loadStudents();
  } catch (error) {
    showModalMessage(error.message);
  } finally {
    submitStudentBtn.disabled = false;
    submitStudentBtn.textContent = editingId ? "Update student" : "Save student";
  }
});

searchInput.addEventListener("input", () => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(loadStudents, 300);
});
sortSelect.addEventListener("change", () => renderStudents(sortStudents(students), Boolean(searchInput.value.trim())));
addStudentBtn.addEventListener("click", openAddModal);
closeModal.addEventListener("click", () => modal.classList.add("hidden"));
document.getElementById("discoverBtn").addEventListener("click", () => document.getElementById("dashboard").scrollIntoView());

window.addEventListener("keydown", event => {
  if (event.key === "Escape") {
    modal.classList.add("hidden");
    deleteModal.classList.add("hidden");
  }
});

loadStudents();
