"use client";

import React, { useState, useEffect, useRef } from 'react';
import { useTheme } from './ThemeProvider';

export function ThemeToggle() {
  const themeContext = useTheme();
  
  // Si le contexte n'est pas disponible (ex: page 404), utiliser des valeurs par défaut
  if (!themeContext) {
    return (
      <div className="p-2 rounded-lg bg-gray-100 dark:bg-gray-800">
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <circle cx="12" cy="12" r="5" />
          <path d="m12 1 1.5 3m-3 0L12 1m9 11-3 1.5m0-3L21 12M1 12l3-1.5m0 3L1 12m11 9-1.5-3m3 0L12 23" />
        </svg>
      </div>
    );
  }
  
  const { theme, setTheme } = themeContext;
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Fermer le dropdown en cliquant à l'extérieur
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isOpen]);

  const themes = [
    {
      value: 'light' as const,
      label: 'Clair',
      icon: (
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <circle cx="12" cy="12" r="5" />
          <path d="m12 1 1.5 3m-3 0L12 1m9 11-3 1.5m0-3L21 12M1 12l3-1.5m0 3L1 12m11 9-1.5-3m3 0L12 23" />
        </svg>
      ),
    },
    {
      value: 'dark' as const,
      label: 'Sombre',
      icon: (
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
        </svg>
      ),
    },
    {
      value: 'system' as const,
      label: 'Système',
      icon: (
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <rect x="2" y="3" width="20" height="14" rx="2" ry="2" />
          <line x1="8" y1="21" x2="16" y2="21" />
          <line x1="12" y1="17" x2="12" y2="21" />
        </svg>
      ),
    },
  ];

  const currentTheme = themes.find(t => t.value === theme);

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="p-2 rounded-lg bg-gray-100 hover:bg-gray-200 dark:bg-gray-800 dark:hover:bg-gray-700 
                   transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
        aria-label="Changer le thème"
        title="Changer le thème"
      >
        {currentTheme?.icon}
      </button>

      {isOpen && (
        <div className="absolute right-0 mt-2 w-40 bg-white dark:bg-gray-800 rounded-lg shadow-lg 
                        border border-gray-200 dark:border-gray-700 py-1 z-50">
          {themes.map((themeOption) => (
            <button
              key={themeOption.value}
              onClick={() => {
                setTheme(themeOption.value);
                setIsOpen(false);
              }}
              className={`w-full px-4 py-2 text-left text-sm hover:bg-gray-100 dark:hover:bg-gray-700 
                         transition-colors duration-150 flex items-center gap-2
                         ${theme === themeOption.value 
                           ? 'text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/20' 
                           : 'text-gray-700 dark:text-gray-300'}`}
            >
              {themeOption.icon}
              {themeOption.label}
              {theme === themeOption.value && (
                <svg className="w-4 h-4 ml-auto" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                </svg>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  );
} 