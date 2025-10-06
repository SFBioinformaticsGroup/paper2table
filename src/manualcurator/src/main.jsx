import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App.jsx'; // Asegúrate que importa App y no App_v2
import './index.css';

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
