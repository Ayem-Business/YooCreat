import React from 'react';

const ProgressBar = ({ progress, message, details }) => {
  return (
    <div className="w-full max-w-2xl mx-auto p-6 bg-white rounded-lg shadow-lg">
      {/* Message principal */}
      <div className="mb-4 text-center">
        <h3 className="text-xl font-bold text-gray-800 mb-2">{message}</h3>
        {details && <p className="text-sm text-gray-600">{details}</p>}
      </div>

      {/* Barre de progression */}
      <div className="relative w-full h-8 bg-gray-200 rounded-full overflow-hidden">
        <div
          className="absolute top-0 left-0 h-full bg-gradient-to-r from-blue-500 via-purple-500 to-pink-500 transition-all duration-500 ease-out flex items-center justify-center"
          style={{ width: `${progress}%` }}
        >
          {progress > 10 && (
            <span className="text-white font-bold text-sm">{progress}%</span>
          )}
        </div>
        
        {/* Animation shimmer */}
        <div 
          className="absolute top-0 left-0 h-full w-full bg-gradient-to-r from-transparent via-white to-transparent opacity-20"
          style={{
            animation: 'shimmer 2s infinite',
            transform: `translateX(${progress - 100}%)`
          }}
        />
      </div>

      {/* Pourcentage en dessous si trop petit dans la barre */}
      {progress <= 10 && (
        <div className="mt-2 text-center">
          <span className="text-sm font-semibold text-gray-700">{progress}%</span>
        </div>
      )}

      {/* Spinner animé */}
      <div className="flex justify-center items-center mt-4">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-500"></div>
        <span className="ml-3 text-sm text-gray-600">Génération en cours...</span>
      </div>
    </div>
  );
};

export default ProgressBar;
