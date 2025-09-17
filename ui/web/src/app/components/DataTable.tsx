'use client'

import { useState, useEffect } from 'react'
import { 
  Plus, 
  Edit, 
  Trash2, 
  Search, 
  ChevronLeft, 
  ChevronRight,
  Loader2,
  Save,
  X,
  Eye,
  EyeOff
} from 'lucide-react'
import { toast } from 'react-hot-toast'

interface Column {
  key: string
  label: string
  type: 'text' | 'number' | 'date' | 'boolean' | 'select' | 'textarea' | 'vector' | 'json'
  required?: boolean
  options?: string[]
  readonly?: boolean
}

interface DataTableProps {
  title: string
  columns: Column[]
  data: any[]
  loading?: boolean
  onAdd?: (data: any) => Promise<void>
  onEdit?: (id: any, data: any) => Promise<void>
  onDelete?: (id: any) => Promise<void>
  onRefresh?: () => Promise<void>
  primaryKey: string
  searchable?: boolean
  pageSize?: number
}

export default function DataTable({
  title,
  columns,
  data,
  loading = false,
  onAdd,
  onEdit,
  onDelete,
  onRefresh,
  primaryKey,
  searchable = true,
  pageSize = 10
}: DataTableProps) {
  const [searchTerm, setSearchTerm] = useState('')
  const [currentPage, setCurrentPage] = useState(1)
  const [editingRow, setEditingRow] = useState<any>(null)
  const [showAddForm, setShowAddForm] = useState(false)
  const [formData, setFormData] = useState<any>({})
  const [showVector, setShowVector] = useState<{ [key: string]: boolean }>({})

  const filteredData = data.filter(row =>
    searchable ? 
      Object.values(row).some(value => 
        value?.toString().toLowerCase().includes(searchTerm.toLowerCase())
      ) : true
  )

  const totalPages = Math.ceil(filteredData.length / pageSize)
  const startIndex = (currentPage - 1) * pageSize
  const paginatedData = filteredData.slice(startIndex, startIndex + pageSize)

  const handleEdit = (row: any) => {
    setEditingRow(row[primaryKey])
    const formattedRow = columns.reduce((acc, column) => {
      const value = row[column.key]
      if (column.type === 'json') {
        acc[column.key] = value ? JSON.stringify(value, null, 2) : ''
      } else {
        acc[column.key] = value
      }
      return acc
    }, {} as Record<string, any>)
    setFormData(formattedRow)
  }

  const handleCancel = () => {
    setEditingRow(null)
    setShowAddForm(false)
    setFormData({})
  }

  const handleSave = async () => {
    try {
      const preparedData: Record<string, any> = {}

      for (const column of columns) {
        const value = formData[column.key]

        if (column.type === 'json') {
          if (value === '' || value === undefined || value === null) {
            preparedData[column.key] = {}
          } else if (typeof value === 'string') {
            try {
              preparedData[column.key] = JSON.parse(value)
            } catch (error) {
              toast.error(`Invalid JSON for ${column.label}`)
              return
            }
          } else {
            preparedData[column.key] = value
          }
          continue
        }

        if (column.type === 'number') {
          preparedData[column.key] = value === '' || value === undefined ? null : Number(value)
          continue
        }

        preparedData[column.key] = value
      }

      if (editingRow) {
        await onEdit?.(editingRow, preparedData)
        toast.success('Record updated successfully')
      } else {
        await onAdd?.(preparedData)
        toast.success('Record added successfully')
      }
      handleCancel()
      await onRefresh?.()
    } catch (error) {
      toast.error('Failed to save record')
      console.error('Save error:', error)
    }
  }

  const handleDelete = async (id: any) => {
    if (window.confirm('Are you sure you want to delete this record?')) {
      try {
        await onDelete?.(id)
        toast.success('Record deleted successfully')
        await onRefresh?.()
      } catch (error) {
        toast.error('Failed to delete record')
        console.error('Delete error:', error)
      }
    }
  }

  const handleInputChange = (key: string, value: any) => {
    setFormData((prev: any) => ({ ...prev, [key]: value }))
  }

  const renderCell = (row: any, column: Column) => {
    const value = row[column.key]
    
    if (editingRow === row[primaryKey]) {
      return renderEditCell(column, value)
    }

    if (column.type === 'vector') {
      return (
        <div className="flex items-center space-x-2">
          <span className="text-xs text-gray-500">
            Vector ({Array.isArray(value) ? value.length : 0} dimensions)
          </span>
          <button
            onClick={() => setShowVector(prev => ({ ...prev, [row[primaryKey]]: !prev[row[primaryKey]] }))}
            className="text-blue-600 hover:text-blue-800"
          >
            {showVector[row[primaryKey]] ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
          </button>
          {showVector[row[primaryKey]] && (
            <div className="max-w-xs overflow-hidden">
              <code className="text-xs bg-gray-100 p-1 rounded">
                [{Array.isArray(value) ? value.slice(0, 5).map(v => v.toFixed(4)).join(', ') : '[]'}...]
              </code>
            </div>
          )}
        </div>
      )
    }

    if (column.type === 'boolean') {
      return (
        <span className={`px-2 py-1 rounded-full text-xs font-medium ${
          value ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
        }`}>
          {value ? 'Yes' : 'No'}
        </span>
      )
    }

    if (column.type === 'textarea') {
      return (
        <div className="max-w-xs">
          <p className="text-sm truncate" title={value}>
            {value || '-'}
          </p>
        </div>
      )
    }

    if (column.type === 'json' || (value && typeof value === 'object')) {
      return (
        <div className="max-w-xs">
          <pre className="text-xs bg-gray-100 p-2 rounded overflow-x-auto" title={JSON.stringify(value, null, 2)}>
            {JSON.stringify(value, null, 2)}
          </pre>
        </div>
      )
    }

    return (
      <span className="text-sm">
        {value || '-'}
      </span>
    )
  }

  const renderEditCell = (column: Column, value: any) => {
    if (column.readonly) {
      return <span className="text-sm text-gray-500">{value || '-'}</span>
    }

    switch (column.type) {
      case 'select':
        return (
          <select
            value={formData[column.key] || ''}
            onChange={(e) => handleInputChange(column.key, e.target.value)}
            className="w-full px-2 py-1 border border-gray-300 rounded text-sm"
          >
            <option value="">Select...</option>
            {column.options?.map(option => (
              <option key={option} value={option}>{option}</option>
            ))}
          </select>
        )
      case 'textarea':
      case 'json': {
        const isJson = column.type === 'json'
        const value = formData[column.key] ?? ''
        const className = `w-full px-2 py-1 border border-gray-300 rounded text-sm${isJson ? ' font-mono' : ''}`
        return (
          <textarea
            value={value}
            onChange={(e) => handleInputChange(column.key, e.target.value)}
            className={className}
            rows={isJson ? 3 : 2}
            placeholder={isJson ? '{\n  "key": "value"\n}' : undefined}
          />
        )
      }
      case 'boolean':
        return (
          <select
            value={formData[column.key] ? 'true' : 'false'}
            onChange={(e) => handleInputChange(column.key, e.target.value === 'true')}
            className="w-full px-2 py-1 border border-gray-300 rounded text-sm"
          >
            <option value="false">No</option>
            <option value="true">Yes</option>
          </select>
        )
      case 'vector':
        return (
          <div className="text-xs text-gray-500">
            Vector editing not supported
          </div>
        )
      default:
        return (
          <input
            type={column.type === 'number' ? 'number' : 'text'}
            value={formData[column.key] || ''}
            onChange={(e) => handleInputChange(column.key, e.target.value)}
            className="w-full px-2 py-1 border border-gray-300 rounded text-sm"
            required={column.required}
          />
        )
    }
  }

  const renderAddForm = () => {
    if (!showAddForm) return null

    return (
      <tr className="bg-blue-50">
        {columns.map(column => (
          <td key={column.key} className="px-4 py-3">
            {renderEditCell(column, '')}
          </td>
        ))}
        <td className="px-4 py-3">
          <div className="flex space-x-2">
            <button
              onClick={handleSave}
              className="p-1 text-green-600 hover:text-green-800"
              title="Save"
            >
              <Save className="h-4 w-4" />
            </button>
            <button
              onClick={handleCancel}
              className="p-1 text-red-600 hover:text-red-800"
              title="Cancel"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </td>
      </tr>
    )
  }

  return (
    <div className="bg-white rounded-lg shadow-lg border-2 border-gray-200">
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-gray-900">{title}</h3>
          <div className="flex items-center space-x-4">
            {searchable && (
              <div className="relative">
                <Search className="h-4 w-4 absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
                <input
                  type="text"
                  placeholder="Search..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-10 pr-4 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>
            )}
            {onAdd && (
              <button
                onClick={() => {
                  setEditingRow(null)
                  setFormData({})
                  setShowAddForm(true)
                }}
                className="flex items-center space-x-2 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors"
              >
                <Plus className="h-4 w-4" />
                <span>Add Record</span>
              </button>
            )}
            {onRefresh && (
              <button
                onClick={onRefresh}
                disabled={loading}
                className="p-2 text-gray-600 hover:text-gray-800 disabled:opacity-50"
              >
                <Loader2 className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-gray-50">
            <tr>
              {columns.map(column => (
                <th key={column.key} className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  {column.label}
                  {column.required && <span className="text-red-500 ml-1">*</span>}
                </th>
              ))}
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {renderAddForm()}
            {loading ? (
              <tr>
                <td colSpan={columns.length + 1} className="px-4 py-8 text-center">
                  <Loader2 className="h-6 w-6 animate-spin mx-auto text-gray-400" />
                  <p className="mt-2 text-sm text-gray-500">Loading data...</p>
                </td>
              </tr>
            ) : paginatedData.length === 0 ? (
              <tr>
                <td colSpan={columns.length + 1} className="px-4 py-8 text-center text-gray-500">
                  No data found
                </td>
              </tr>
            ) : (
              paginatedData.map((row, index) => (
                <tr key={row[primaryKey] || index} className="hover:bg-gray-50">
                  {columns.map(column => (
                    <td key={column.key} className="px-4 py-3">
                      {renderCell(row, column)}
                    </td>
                  ))}
                  <td className="px-4 py-3">
                    <div className="flex space-x-2">
                      {editingRow === row[primaryKey] ? (
                        <>
                          <button
                            onClick={handleSave}
                            className="p-1 text-green-600 hover:text-green-800"
                            title="Save"
                          >
                            <Save className="h-4 w-4" />
                          </button>
                          <button
                            onClick={handleCancel}
                            className="p-1 text-red-600 hover:text-red-800"
                            title="Cancel"
                          >
                            <X className="h-4 w-4" />
                          </button>
                        </>
                      ) : (
                        <>
                          {onEdit && (
                            <button
                              onClick={() => handleEdit(row)}
                              className="p-1 text-blue-600 hover:text-blue-800"
                              title="Edit"
                            >
                              <Edit className="h-4 w-4" />
                            </button>
                          )}
                          {onDelete && (
                            <button
                              onClick={() => handleDelete(row[primaryKey])}
                              className="p-1 text-red-600 hover:text-red-800"
                              title="Delete"
                            >
                              <Trash2 className="h-4 w-4" />
                            </button>
                          )}
                        </>
                      )}
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="px-6 py-4 border-t border-gray-200">
          <div className="flex items-center justify-between">
            <div className="text-sm text-gray-700">
              Showing {startIndex + 1} to {Math.min(startIndex + pageSize, filteredData.length)} of {filteredData.length} results
            </div>
            <div className="flex items-center space-x-2">
              <button
                onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                disabled={currentPage === 1}
                className="p-2 text-gray-600 hover:text-gray-800 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <ChevronLeft className="h-4 w-4" />
              </button>
              <span className="text-sm text-gray-700">
                Page {currentPage} of {totalPages}
              </span>
              <button
                onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
                disabled={currentPage === totalPages}
                className="p-2 text-gray-600 hover:text-gray-800 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <ChevronRight className="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
