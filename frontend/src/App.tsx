import React from 'react';
import ReportPage from './components/ReportPage';
import { CookiesProvider } from 'react-cookie';

const App: React.FC = () => {
  return (
    <CookiesProvider>
      <div className="App">
        <ReportPage />
      </div>
    </CookiesProvider>
  );
};

export default App;