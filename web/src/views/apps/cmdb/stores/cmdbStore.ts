/**
 * CMDB Pinia Store
 */
import { defineStore } from 'pinia'

interface CmdbState {
  // Schema
  classifications: any[]
  modelDefinitions: any[]
  modelFields: any[]
  associationTypes: any[]
  modelAssociations: any[]
  selectedModelCode: string | null

  // 拓扑
  topology: { nodes: any[]; edges: any[] }
  topologyLoading: boolean
  impactResult: any | null
  searchResults: any[]
  searchQuery: string

  // UI
  loading: boolean
  activeView: string
}

export const useCmdbStore = defineStore('cmdb', {
  state: (): CmdbState => ({
    classifications: [],
    modelDefinitions: [],
    modelFields: [],
    associationTypes: [],
    modelAssociations: [],
    selectedModelCode: null,

    topology: { nodes: [], edges: [] },
    topologyLoading: false,
    impactResult: null,
    searchResults: [],
    searchQuery: '',

    loading: false,
    activeView: 'schema',
  }),

  getters: {
    selectedModelDef: (state) =>
      state.modelDefinitions.find((m: any) => m.code === state.selectedModelCode) || null,
    currentFields: (state) =>
      state.selectedModelCode
        ? state.modelFields.filter((f: any) => f.model_definition === state.selectedModelDef?.id)
        : [],
  },

  actions: {
    setActiveView(view: string) {
      this.activeView = view
    },

    async fetchClassifications() {
      const { classificationsApi } = await import('/@/api/cmdb/index')
      const res = await classificationsApi.list()
      this.classifications = res.data || []
    },

    async fetchModelDefinitions() {
      const { modelDefinitionsApi } = await import('/@/api/cmdb/index')
      const res = await modelDefinitionsApi.list()
      this.modelDefinitions = res.data || []
    },

    async fetchModelFields() {
      const { modelFieldsApi } = await import('/@/api/cmdb/index')
      const res = await modelFieldsApi.list()
      this.modelFields = res.data || []
    },

    async fetchAssociationTypes() {
      const { associationTypesApi } = await import('/@/api/cmdb/index')
      const res = await associationTypesApi.list()
      this.associationTypes = res.data || []
    },

    async fetchModelAssociations() {
      const { modelAssociationsApi } = await import('/@/api/cmdb/index')
      const res = await modelAssociationsApi.list()
      this.modelAssociations = res.data || []
    },

    async fetchTopology() {
      const { getTopology } = await import('/@/api/cmdb/index')
      this.topologyLoading = true
      try {
        const res = await getTopology()
        this.topology = res.data || { nodes: [], edges: [] }
      } finally {
        this.topologyLoading = false
      }
    },

    async doSearch(q: string) {
      const { globalSearch } = await import('/@/api/cmdb/index')
      if (!q) {
        this.searchResults = []
        return
      }
      const res = await globalSearch(q)
      this.searchResults = res.data || []
      this.searchQuery = q
    },

    clearSearch() {
      this.searchResults = []
      this.searchQuery = ''
    },
  },
})
