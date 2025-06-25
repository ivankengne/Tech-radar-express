import React from 'react';
import { Metadata } from 'next';
import NotificationCenter from '../../../components/admin/NotificationCenter';

export const metadata: Metadata = {
  title: 'Notifications - Tech Radar Express',
  description: 'Centre de notifications WebSocket avec seuils de pertinence configurables',
};

export default function NotificationsPage() {
  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">
          Centre de Notifications
        </h1>
        <p className="text-gray-600">
          Gérez vos notifications WebSocket en temps réel avec des seuils de pertinence configurables
        </p>
      </div>
      
      <NotificationCenter />
    </div>
  );
} 