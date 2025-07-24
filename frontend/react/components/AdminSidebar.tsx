import { NavLink } from 'react-router-dom';

function AdminSidebar() {
  return (
    <div className="sidebar">
      <ul>
        {/* Diğer menü öğeleri */}
        <li>
          <NavLink to="/admin/plans" className={({ isActive }) => (isActive ? 'active' : undefined)}>
            Plan Yönetimi
          </NavLink>
        </li>
      </ul>
    </div>
  );
}

export default AdminSidebar;
