import { NavLink } from "react-router-dom";

const links = [
  { to: "/", label: "Storage", icon: "01" },
  { to: "/media", label: "Media", icon: "02" },
  { to: "/models", label: "Weights", icon: "03" },
  { to: "/chat", label: "Chat", icon: "04" },
];

export default function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="brand">
        <span className="brand-mark">ASTRO</span>
        <span className="brand-sub">vault</span>
      </div>
      <nav className="nav">
        {links.map((link) => (
          <NavLink
            key={link.to}
            to={link.to}
            end={link.to === "/"}
            className={({ isActive }) => `nav-link${isActive ? " active" : ""}`}
          >
            <span className="nav-icon">{link.icon}</span>
            {link.label}
          </NavLink>
        ))}
      </nav>
      <div className="sidebar-footer">local · offline</div>
    </aside>
  );
}
