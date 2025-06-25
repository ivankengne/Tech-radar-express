/**
 * Tech Radar Express - Composant QueryCitation
 * Citations cliquables avec permaliens vers chunks MCP
 * Volet latéral avec source complète et navigation
 */

'use client'

import React, { useState, useCallback, useMemo } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  ExternalLink, 
  FileText, 
  Code,
  ChevronRight,
  ChevronDown,
  Link,
  Copy
} from 'lucide-react'

export interface CitationData {
  id: string
  text: string
  source: string
  url?: string
  type: 'document' | 'code'
  chunk_id: string
  title?: string
  score: number
  metadata?: {
    word_count?: number
    char_count?: number
    rerank_score?: number
    headers?: string
    summary?: string
    [key: string]: any
  }
}

export interface QueryCitationProps {
  citations: CitationData[]
  onCitationClick?: (citation: CitationData) => void
  className?: string
  maxVisible?: number
  showScores?: boolean
  groupBySource?: boolean
}

export interface CitationDetailsProps {
  citation: CitationData
  isOpen: boolean
  onClose: () => void
}

// ===================================
// COMPOSANT DÉTAILS DE CITATION
// ===================================

const CitationDetails: React.FC<CitationDetailsProps> = ({ 
  citation, 
  isOpen, 
  onClose 
}) => {
  const [copied, setCopied] = useState(false)
  
  const handleCopyPermalink = useCallback(async () => {
    try {
      const permalink = `${window.location.origin}/citation/${citation.chunk_id}`
      await navigator.clipboard.writeText(permalink)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch (error) {
      console.error('Erreur copie permalien:', error)
    }
  }, [citation.chunk_id])
  
  const handleCopyContent = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(citation.text)
    } catch (error) {
      console.error('Erreur copie contenu:', error)
    }
  }, [citation.text])
  
  const formatScore = (score: number) => {
    return (score * 100).toFixed(1) + '%'
  }
  
  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Overlay */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/20 backdrop-blur-sm z-40"
            onClick={onClose}
          />
          
          {/* Panel latéral */}
          <motion.div
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', damping: 25, stiffness: 200 }}
            className="fixed right-0 top-0 h-full w-full max-w-2xl bg-white dark:bg-gray-900 shadow-2xl z-50 overflow-hidden"
          >
            <div className="flex flex-col h-full">
              {/* Header */}
              <div className="flex-shrink-0 bg-gray-50 dark:bg-gray-800 p-6 border-b border-gray-200 dark:border-gray-700">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      {citation.type === 'code' ? (
                        <Code className="h-5 w-5 text-blue-500" />
                      ) : (
                        <FileText className="h-5 w-5 text-green-500" />
                      )}
                      <span className="text-sm font-medium text-gray-600 dark:text-gray-300">
                        {citation.type === 'code' ? 'Code' : 'Document'}
                      </span>
                      <span className="text-xs bg-gray-200 dark:bg-gray-700 px-2 py-1 rounded">
                        Score: {formatScore(citation.score)}
                      </span>
                    </div>
                    
                    <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-1">
                      {citation.title || 'Citation'}
                    </h2>
                    
                    <p className="text-sm text-gray-600 dark:text-gray-400">
                      Source: {citation.source}
                    </p>
                    
                    {citation.metadata?.summary && (
                      <p className="text-sm text-gray-500 dark:text-gray-400 mt-2 italic">
                        {citation.metadata.summary}
                      </p>
                    )}
                  </div>
                  
                  <button
                    onClick={onClose}
                    className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 
                             hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
                  >
                    <ChevronRight className="h-5 w-5" />
                  </button>
                </div>
                
                {/* Actions */}
                <div className="flex items-center gap-2 mt-4">
                  <button
                    onClick={handleCopyPermalink}
                    className="flex items-center gap-2 px-3 py-2 text-xs bg-blue-100 dark:bg-blue-900/30 
                             text-blue-700 dark:text-blue-300 rounded-lg hover:bg-blue-200 
                             dark:hover:bg-blue-900/50 transition-colors"
                  >
                    <Link className="h-4 w-4" />
                    {copied ? 'Copié!' : 'Permalien'}
                  </button>
                  
                  <button
                    onClick={handleCopyContent}
                    className="flex items-center gap-2 px-3 py-2 text-xs bg-gray-100 dark:bg-gray-800 
                             text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-200 
                             dark:hover:bg-gray-700 transition-colors"
                  >
                    <Copy className="h-4 w-4" />
                    Copier
                  </button>
                  
                  {citation.url && (
                    <a
                      href={citation.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-2 px-3 py-2 text-xs bg-green-100 dark:bg-green-900/30 
                               text-green-700 dark:text-green-300 rounded-lg hover:bg-green-200 
                               dark:hover:bg-green-900/50 transition-colors"
                    >
                      <ExternalLink className="h-4 w-4" />
                      Source
                    </a>
                  )}
                </div>
              </div>
              
              {/* Contenu */}
              <div className="flex-1 overflow-y-auto p-6">
                <div className="prose prose-sm max-w-none dark:prose-invert">
                  {citation.type === 'code' ? (
                    <pre className="bg-gray-100 dark:bg-gray-800 p-4 rounded-lg overflow-x-auto">
                      <code className="text-sm">{citation.text}</code>
                    </pre>
                  ) : (
                    <div className="whitespace-pre-wrap text-gray-700 dark:text-gray-300 leading-relaxed">
                      {citation.text}
                    </div>
                  )}
                </div>
                
                {/* Métadonnées */}
                {citation.metadata && Object.keys(citation.metadata).length > 0 && (
                  <div className="mt-8 pt-6 border-t border-gray-200 dark:border-gray-700">
                    <h3 className="text-sm font-medium text-gray-900 dark:text-white mb-3">
                      Métadonnées
                    </h3>
                    <div className="grid grid-cols-2 gap-3 text-xs">
                      {citation.metadata.word_count && (
                        <div>
                          <span className="text-gray-500 dark:text-gray-400">Mots:</span>
                          <span className="ml-2 text-gray-900 dark:text-white">
                            {citation.metadata.word_count}
                          </span>
                        </div>
                      )}
                      {citation.metadata.char_count && (
                        <div>
                          <span className="text-gray-500 dark:text-gray-400">Caractères:</span>
                          <span className="ml-2 text-gray-900 dark:text-white">
                            {citation.metadata.char_count}
                          </span>
                        </div>
                      )}
                      {citation.metadata.rerank_score && (
                        <div>
                          <span className="text-gray-500 dark:text-gray-400">Rerank:</span>
                          <span className="ml-2 text-gray-900 dark:text-white">
                            {formatScore(citation.metadata.rerank_score)}
                          </span>
                        </div>
                      )}
                      <div>
                        <span className="text-gray-500 dark:text-gray-400">Chunk ID:</span>
                        <span className="ml-2 text-gray-900 dark:text-white font-mono text-xs">
                          {citation.chunk_id}
                        </span>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}

// ===================================
// COMPOSANT CITATION INDIVIDUELLE
// ===================================

const CitationItem: React.FC<{
  citation: CitationData
  index: number
  onClick: () => void
  showScore?: boolean
}> = ({ citation, index, onClick, showScore = false }) => {
  const truncatedText = useMemo(() => {
    return citation.text.length > 120 
      ? citation.text.substring(0, 120) + '...'
      : citation.text
  }, [citation.text])
  
  return (
    <motion.button
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.1 }}
      onClick={onClick}
      className="w-full text-left p-3 bg-gray-50 dark:bg-gray-800 rounded-lg 
                 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors 
                 border border-gray-200 dark:border-gray-700 group"
    >
      <div className="flex items-start gap-3">
        <div className="flex-shrink-0 mt-1">
          {citation.type === 'code' ? (
            <Code className="h-4 w-4 text-blue-500" />
          ) : (
            <FileText className="h-4 w-4 text-green-500" />
          )}
        </div>
        
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-medium text-gray-900 dark:text-white">
              [{index + 1}]
            </span>
            <span className="text-xs text-gray-500 dark:text-gray-400 truncate">
              {citation.source}
            </span>
            {showScore && (
              <span className="text-xs bg-blue-100 dark:bg-blue-900/30 text-blue-700 
                             dark:text-blue-300 px-1.5 py-0.5 rounded">
                {(citation.score * 100).toFixed(0)}%
              </span>
            )}
          </div>
          
          <p className="text-sm text-gray-700 dark:text-gray-300 line-clamp-2">
            {truncatedText}
          </p>
          
          {citation.title && (
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 italic">
              {citation.title}
            </p>
          )}
        </div>
        
        <ChevronRight className="h-4 w-4 text-gray-400 group-hover:text-gray-600 
                                   dark:group-hover:text-gray-300 transition-colors flex-shrink-0" />
      </div>
    </motion.button>
  )
}

// ===================================
// COMPOSANT PRINCIPAL
// ===================================

const QueryCitation: React.FC<QueryCitationProps> = ({
  citations,
  onCitationClick,
  className = '',
  maxVisible = 5,
  showScores = false,
  groupBySource = false
}) => {
  const [selectedCitation, setSelectedCitation] = useState<CitationData | null>(null)
  const [showAll, setShowAll] = useState(false)
  
  const groupedCitations = useMemo(() => {
    if (!groupBySource) {
      return { all: citations }
    }
    
    return citations.reduce((groups, citation) => {
      const source = citation.source
      if (!groups[source]) {
        groups[source] = []
      }
      groups[source].push(citation)
      return groups
    }, {} as Record<string, CitationData[]>)
  }, [citations, groupBySource])
  
  const visibleCitations = useMemo(() => {
    if (groupBySource) {
      return groupedCitations
    }
    
    return {
      all: showAll ? citations : citations.slice(0, maxVisible)
    }
  }, [citations, groupedCitations, showAll, maxVisible, groupBySource])
  
  const handleCitationClick = useCallback((citation: CitationData) => {
    setSelectedCitation(citation)
    onCitationClick?.(citation)
  }, [onCitationClick])
  
  const handleCloseDetails = useCallback(() => {
    setSelectedCitation(null)
  }, [])
  
  if (!citations || citations.length === 0) {
    return null
  }
  
  return (
    <>
      <div className={`space-y-4 ${className}`}>
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-medium text-gray-900 dark:text-white flex items-center gap-2">
            <FileText className="h-4 w-4" />
            Citations ({citations.length})
          </h3>
          
          {citations.length > maxVisible && !groupBySource && (
            <button
              onClick={() => setShowAll(!showAll)}
              className="text-xs text-blue-600 dark:text-blue-400 hover:text-blue-800 
                       dark:hover:text-blue-300 transition-colors flex items-center gap-1"
            >
              {showAll ? (
                <>
                  <ChevronDown className="h-3 w-3" />
                  Voir moins
                </>
              ) : (
                <>
                  <ChevronRight className="h-3 w-3" />
                  Voir tout ({citations.length})
                </>
              )}
            </button>
          )}
        </div>
        
        <div className="space-y-3">
          {Object.entries(visibleCitations).map(([source, sourceCitations]) => (
            <div key={source} className="space-y-2">
              {groupBySource && source !== 'all' && (
                <h4 className="text-xs font-medium text-gray-600 dark:text-gray-400 uppercase tracking-wide">
                  {source} ({sourceCitations.length})
                </h4>
              )}
              
              {sourceCitations.map((citation, index) => (
                <CitationItem
                  key={citation.id}
                  citation={citation}
                  index={groupBySource ? index : citations.indexOf(citation)}
                  onClick={() => handleCitationClick(citation)}
                  showScore={showScores}
                />
              ))}
            </div>
          ))}
        </div>
        
        {!showAll && citations.length > maxVisible && !groupBySource && (
          <div className="text-center">
            <button
              onClick={() => setShowAll(true)}
              className="text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 
                       dark:hover:text-gray-300 transition-colors"
            >
              + {citations.length - maxVisible} citations supplémentaires
            </button>
          </div>
        )}
      </div>
      
      {/* Panel de détails */}
      {selectedCitation && (
        <CitationDetails
          citation={selectedCitation}
          isOpen={!!selectedCitation}
          onClose={handleCloseDetails}
        />
      )}
    </>
  )
}

export default QueryCitation 