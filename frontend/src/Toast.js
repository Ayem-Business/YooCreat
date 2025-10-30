import React from 'react';

const Toast = ({ message, type = 'success', onClose }) => {
  React.useEffect(() => {
    const timer = setTimeout(() => {
      onClose();
    }, 5000);
    return () => clearTimeout(timer);
  }, [onClose]);

  const bgColor = {
    success: 'bg-green-500',
    error: 'bg-red-500',
    info: 'bg-blue-500',
    warning: 'bg-yellow-500'
  }[type] || 'bg-gray-500';

  const icon = {
    success: '✓',
    error: '✗',
    info: 'ℹ',
    warning: '⚠'
  }[type] || 'ℹ';

  return (
    <div className={`${bgColor} text-white px-6 py-4 rounded-lg shadow-lg flex items-center space-x-3 min-w-[300px] max-w-md animate-slide-in`}>
      <span className="text-2xl">{icon}</span>
      <span className="flex-1">{message}</span>
      <button onClick={onClose} className="text-white hover:text-gray-200 font-bold text-xl">
        ×
      </button>
    </div>
  );
};

export default Toast;
