import React from 'react';
import { NavLink } from 'react-router-dom';

const AdminSidebar = () => {
  const navItems = [
    { name: 'Dashboard', path: '/admin' },
    { name: 'Kullanıcılar', path: '/admin/users' },
    { name: 'Promosyonlar', path: '/admin/promos' },
    { name: 'Tahminler', path: '/admin/predictions' },
    { name: 'Plan Yönetimi', path: '/admin/plans' },
    { name: 'Kullanım Limitleri', path: '/admin/limits' },
    { name: 'İçerik Yönetimi', path: '/admin/content' },
    { name: 'Sistem İzleme', path: '/admin/monitoring' },
    { name: 'Loglar', path: '/admin/logs' },
  ];

  return (
    <aside className="w-64 h-screen p-4 bg-gray-100 border-r">
      <nav>
        <ul className="space-y-2">
          {navItems.map((item) => (
            <li key={item.path}>
              <NavLink
                to={item.path}
                className={({ isActive }) =>
                  isActive
                    ? 'block px-4 py-2 rounded bg-blue-100 text-blue-700 font-semibold'
                    : 'block px-4 py-2 rounded hover:bg-gray-200 text-gray-800'}
              >
                {item.name}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>
    </aside>
  );
};

export default AdminSidebar;
