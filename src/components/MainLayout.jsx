import Navbar from './Navbar';
import { Outlet } from 'react-router-dom';

function MainLayout() {
  return (

    <div>
      <div className='background'>
      </div>
      <Navbar />
      <Outlet />
    </div>
  );
}

export default MainLayout;
