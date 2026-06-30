// Task 1 Updated/frontend/src/utils/validation.js
const NAME_RE = /^[A-Za-z\s\-]{3,120}$/
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

export function validateForm({ full_name, date_of_birth, email, glucose, haemoglobin, cholesterol }) {
  const errors = {}

  if (!full_name || !NAME_RE.test(full_name.trim())) {
    errors.full_name = 'Name must be at least 3 letters and contain only letters, spaces, or hyphens.'
  }

  if (!date_of_birth) {
    errors.date_of_birth = 'Date of birth is required.'
  } else {
    const dob = new Date(date_of_birth)
    const today = new Date()
    today.setHours(0, 0, 0, 0)
    if (dob >= today) {
      errors.date_of_birth = 'Date of birth cannot be today or a future date.'
    }
  }

  if (!email || !EMAIL_RE.test(email.trim())) {
    errors.email = 'Please enter a valid email address.'
  }

  const g = Number(glucose)
  if (glucose === '' || glucose === undefined || isNaN(g) || g <= 0 || g > 1000) {
    errors.glucose = 'Glucose must be a number between 1 and 1000 mg/dL.'
  }

  const h = Number(haemoglobin)
  if (haemoglobin === '' || haemoglobin === undefined || isNaN(h) || h <= 0 || h > 30) {
    errors.haemoglobin = 'Haemoglobin must be a number between 1 and 30 g/dL.'
  }

  const c = Number(cholesterol)
  if (cholesterol === '' || cholesterol === undefined || isNaN(c) || c <= 0 || c > 1000) {
    errors.cholesterol = 'Cholesterol must be a number between 1 and 1000 mg/dL.'
  }

  return errors
}
