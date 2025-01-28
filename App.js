import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import Home from './pages/Home';
import RecordInstallation from './pages/RecordInstallation';
import RecordSale from './pages/RecordSale';
import UpdateStock from './pages/UpdateStock';
import ReturnProduct from './pages/ReturnProduct';

const App = () => {
    const apiPages = [
        { path: '/record-installation', name: 'Record Installation', component: <RecordInstallation /> },
        { path: '/record-sale', name: 'Record Sale', component: <RecordSale /> },
        { path: '/update-stock', name: 'Update Stock', component: <UpdateStock /> },
        { path: '/return-product', name: 'Return Product', component: <ReturnProduct /> },
    ];

    return (
        <Router>
            <div>
                <nav style={{ padding: '20px' }}>
                    <Link to="/" style={{ marginRight: '15px' }}>Home</Link>
                    {apiPages.map((page, index) => (
                        <Link 
                            key={index} 
                            to={page.path} 
                            style={{ marginRight: '15px' }}
                        >
                            {page.name}
                        </Link>
                    ))}
                </nav>

                <Routes>
                    <Route path="/" element={<Home />} />
                    {apiPages.map((page, index) => (
                        <Route key={index} path={page.path} element={page.component} />
                    ))}
                </Routes>
            </div>
        </Router>
    );
};

export default App;
