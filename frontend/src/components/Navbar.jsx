// HealthChecker/frontend/src/components/Navbar.jsx
import { Link } from 'react-router-dom'
import logo from "../assets/Logo.png";

export default function Navbar() {
  return (
    <nav className="navbar">
      <Link to="/" className="navbar-brand">
        <span className="logo-dot" />
        <img
          src={logo}
          alt="HealthPredict"
          style={{
            height: "1.5em",
            width: "auto",
          }}
        />
        HealthChecker
      </Link>
      <div className="navbar-links">
        <Link to="/new" className="btn btn-primary btn-sm">+ New Application</Link>
      </div>
    </nav>
  )
}
