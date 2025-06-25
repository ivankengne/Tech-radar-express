import React from 'react'
import { Metadata } from 'next'
import CrawlMonitoring from '@/components/admin/CrawlMonitoring'

export const metadata: Metadata = {
  title: 'Monitoring des Crawls | Tech Radar Express',
  description: 'Surveillance temps réel des crawls MCP avec statuts et gestion d\'erreurs',
}

export default function MonitoringPage() {
  return (
    <div className="container mx-auto px-4 py-8">
      <CrawlMonitoring />
    </div>
  )
} 