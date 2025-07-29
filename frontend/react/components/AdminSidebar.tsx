import { NavLink } from 'react-router-dom';

const AdminSidebar = () => {
  const navItems = [
    { name: 'Dashboard', path: '/admin' },
    { name: 'Kullan\u0131c\u0131lar', path: '/admin/users' },
    { name: 'Promosyonlar', path: '/admin/promos' },
    { name: 'Tahminler', path: '/admin/predictions' },
    { name: 'Plan Y\u00f6netimi', path: '/admin/plans' },
    { name: 'Kullan\u0131m Limitleri', path: '/admin/limits' },
    { name: '\u0130\u00e7erik Y\u00f6netimi', path: '/admin/content' },
    { name: 'Sistem \u0130zleme', path: '/admin/monitoring' },
  ];

  return (
    <div className="sidebar">
      <ul>
        {navItems.map((item) => (
          <li key={item.path}>
            <NavLink to={item.path} className={({ isActive }) => (isActive ? 'active' : undefined)}>
              {item.name}
            </NavLink>
          </li>
        ))}
      </ul>
    </div>
  );
};

export default AdminSidebar;
