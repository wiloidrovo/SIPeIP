import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './styles/index.css'
import './styles/menu.css'
import App from './App.tsx'

// Punto de montaje de la aplicación y de los estilos compartidos. StrictMode
// ayuda a detectar efectos con limpieza incorrecta durante el desarrollo.
createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
