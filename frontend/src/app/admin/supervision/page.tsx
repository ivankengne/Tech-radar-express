import { Metadata } from 'next'
import SourceSupervision from '@/components/admin/SourceSupervision'

export const metadata: Metadata = {
  title: 'Supervision Sources | Tech Radar Express',
  description: 'Dashboard de supervision des sources avec intégration MCP',
}

export default function SupervisionPage() {
  return (
    <div className="container mx-auto py-6">
      <SourceSupervision />
    </div>
  )
} 