import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export type AxisType = 'frontend' | 'backend' | 'ai-ml' | 'devops' | 'mobile' | 'data' | 'security' | 'cloud';
export type PriorityType = 'low' | 'medium' | 'high' | 'critical';
export type ImpactType = 'disruptive' | 'emerging' | 'incremental' | 'declining';
export type SourceType = string;

export interface TimeRange {
  start: Date;
  end: Date;
  preset: '24h' | '7d' | '30d' | '90d' | 'custom';
}

export interface DashboardFilters {
  // Filtres par axe technologique
  selectedAxes: AxisType[];
  allAxes: boolean;
  
  // Filtres temporels
  timeRange: TimeRange;
  
  // Filtres par source
  selectedSources: SourceType[];
  allSources: boolean;
  
  // Filtres par priorité
  selectedPriorities: PriorityType[];
  allPriorities: boolean;
  
  // Filtres par impact
  selectedImpacts: ImpactType[];
  allImpacts: boolean;
  
  // Recherche textuelle
  searchQuery: string;
  
  // Vue active
  activeView: 'overview' | 'timeline' | 'radar' | 'sources';
  
  // Paramètres d'affichage
  itemsPerPage: number;
  sortBy: 'timestamp' | 'priority' | 'impact' | 'source';
  sortOrder: 'asc' | 'desc';
}

export interface DashboardActions {
  // Actions pour les axes
  toggleAxis: (axis: AxisType) => void;
  selectAllAxes: () => void;
  deselectAllAxes: () => void;
  setSelectedAxes: (axes: AxisType[]) => void;
  
  // Actions pour les sources
  toggleSource: (source: SourceType) => void;
  selectAllSources: () => void;
  deselectAllSources: () => void;
  setSelectedSources: (sources: SourceType[]) => void;
  
  // Actions pour les priorités
  togglePriority: (priority: PriorityType) => void;
  selectAllPriorities: () => void;
  deselectAllPriorities: () => void;
  
  // Actions pour les impacts
  toggleImpact: (impact: ImpactType) => void;
  selectAllImpacts: () => void;
  deselectAllImpacts: () => void;
  
  // Actions temporelles
  setTimeRange: (range: TimeRange) => void;
  setTimePreset: (preset: TimeRange['preset']) => void;
  
  // Actions de recherche
  setSearchQuery: (query: string) => void;
  clearSearch: () => void;
  
  // Actions d'affichage
  setActiveView: (view: DashboardFilters['activeView']) => void;
  setItemsPerPage: (count: number) => void;
  setSorting: (sortBy: DashboardFilters['sortBy'], sortOrder: DashboardFilters['sortOrder']) => void;
  
  // Actions globales
  resetFilters: () => void;
  resetToDefaults: () => void;
}

export type DashboardStore = DashboardFilters & DashboardActions;

// Valeurs par défaut
const getDefaultTimeRange = (): TimeRange => {
  const now = new Date();
  const sevenDaysAgo = new Date();
  sevenDaysAgo.setDate(now.getDate() - 7);
  
  return {
    start: sevenDaysAgo,
    end: now,
    preset: '7d',
  };
};

const defaultFilters: DashboardFilters = {
  selectedAxes: [],
  allAxes: true,
  timeRange: getDefaultTimeRange(),
  selectedSources: [],
  allSources: true,
  selectedPriorities: [],
  allPriorities: true,
  selectedImpacts: [],
  allImpacts: true,
  searchQuery: '',
  activeView: 'overview',
  itemsPerPage: 10,
  sortBy: 'timestamp',
  sortOrder: 'desc',
};

export const useDashboardStore = create<DashboardStore>()(
  persist(
    (set, get) => ({
      ...defaultFilters,
      
      // Actions pour les axes
      toggleAxis: (axis: AxisType) => {
        const { selectedAxes, allAxes } = get();
        if (allAxes) {
          set({ selectedAxes: [axis], allAxes: false });
        } else {
          const newAxes = selectedAxes.includes(axis)
            ? selectedAxes.filter(a => a !== axis)
            : [...selectedAxes, axis];
          
          if (newAxes.length === 0) {
            set({ allAxes: true, selectedAxes: [] });
          } else {
            set({ selectedAxes: newAxes });
          }
        }
      },
      
      selectAllAxes: () => set({ allAxes: true, selectedAxes: [] }),
      
      deselectAllAxes: () => set({ allAxes: false, selectedAxes: [] }),
      
      setSelectedAxes: (axes: AxisType[]) => 
        set({ selectedAxes: axes, allAxes: axes.length === 0 }),
      
      // Actions pour les sources
      toggleSource: (source: SourceType) => {
        const { selectedSources, allSources } = get();
        if (allSources) {
          set({ selectedSources: [source], allSources: false });
        } else {
          const newSources = selectedSources.includes(source)
            ? selectedSources.filter(s => s !== source)
            : [...selectedSources, source];
          
          if (newSources.length === 0) {
            set({ allSources: true, selectedSources: [] });
          } else {
            set({ selectedSources: newSources });
          }
        }
      },
      
      selectAllSources: () => set({ allSources: true, selectedSources: [] }),
      
      deselectAllSources: () => set({ allSources: false, selectedSources: [] }),
      
      setSelectedSources: (sources: SourceType[]) => 
        set({ selectedSources: sources, allSources: sources.length === 0 }),
      
      // Actions pour les priorités
      togglePriority: (priority: PriorityType) => {
        const { selectedPriorities, allPriorities } = get();
        if (allPriorities) {
          set({ selectedPriorities: [priority], allPriorities: false });
        } else {
          const newPriorities = selectedPriorities.includes(priority)
            ? selectedPriorities.filter(p => p !== priority)
            : [...selectedPriorities, priority];
          
          if (newPriorities.length === 0) {
            set({ allPriorities: true, selectedPriorities: [] });
          } else {
            set({ selectedPriorities: newPriorities });
          }
        }
      },
      
      selectAllPriorities: () => set({ allPriorities: true, selectedPriorities: [] }),
      
      deselectAllPriorities: () => set({ allPriorities: false, selectedPriorities: [] }),
      
      // Actions pour les impacts
      toggleImpact: (impact: ImpactType) => {
        const { selectedImpacts, allImpacts } = get();
        if (allImpacts) {
          set({ selectedImpacts: [impact], allImpacts: false });
        } else {
          const newImpacts = selectedImpacts.includes(impact)
            ? selectedImpacts.filter(i => i !== impact)
            : [...selectedImpacts, impact];
          
          if (newImpacts.length === 0) {
            set({ allImpacts: true, selectedImpacts: [] });
          } else {
            set({ selectedImpacts: newImpacts });
          }
        }
      },
      
      selectAllImpacts: () => set({ allImpacts: true, selectedImpacts: [] }),
      
      deselectAllImpacts: () => set({ allImpacts: false, selectedImpacts: [] }),
      
      // Actions temporelles
      setTimeRange: (range: TimeRange) => set({ timeRange: range }),
      
      setTimePreset: (preset: TimeRange['preset']) => {
        const now = new Date();
        let start = new Date();
        
        switch (preset) {
          case '24h':
            start.setHours(now.getHours() - 24);
            break;
          case '7d':
            start.setDate(now.getDate() - 7);
            break;
          case '30d':
            start.setDate(now.getDate() - 30);
            break;
          case '90d':
            start.setDate(now.getDate() - 90);
            break;
          default:
            start = get().timeRange.start;
        }
        
        set({
          timeRange: {
            start,
            end: now,
            preset,
          },
        });
      },
      
      // Actions de recherche
      setSearchQuery: (query: string) => set({ searchQuery: query }),
      
      clearSearch: () => set({ searchQuery: '' }),
      
      // Actions d'affichage
      setActiveView: (view: DashboardFilters['activeView']) => set({ activeView: view }),
      
      setItemsPerPage: (count: number) => set({ itemsPerPage: count }),
      
      setSorting: (sortBy: DashboardFilters['sortBy'], sortOrder: DashboardFilters['sortOrder']) => 
        set({ sortBy, sortOrder }),
      
      // Actions globales
      resetFilters: () => {
        const currentTimeRange = get().timeRange;
        set({
          selectedAxes: [],
          allAxes: true,
          selectedSources: [],
          allSources: true,
          selectedPriorities: [],
          allPriorities: true,
          selectedImpacts: [],
          allImpacts: true,
          searchQuery: '',
          timeRange: currentTimeRange, // Garde la période actuelle
        });
      },
      
      resetToDefaults: () => set({ ...defaultFilters, timeRange: getDefaultTimeRange() }),
    }),
    {
      name: 'tech-radar-dashboard-filters',
      partialize: (state) => ({
        // Persister seulement certaines données
        selectedAxes: state.selectedAxes,
        allAxes: state.allAxes,
        timeRange: state.timeRange,
        selectedSources: state.selectedSources,
        allSources: state.allSources,
        activeView: state.activeView,
        itemsPerPage: state.itemsPerPage,
        sortBy: state.sortBy,
        sortOrder: state.sortOrder,
      }),
    }
  )
); 