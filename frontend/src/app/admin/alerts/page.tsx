import React from 'react';
import AlertsManagement from '@/components/admin/AlertsManagement';

export default function AlertsPage() {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <div className="container mx-auto px-4 py-8">
        <AlertsManagement />
      </div>
    </div>
  );
} 