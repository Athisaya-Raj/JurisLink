/**
 * Progress note API service
 */
import client from './client.js'

export async function addProgressNote(caseId, noteContent, noteType = 'progress') {
  const { data } = await client.post(`/progress/cases/${caseId}/progress`, {
    note: noteContent,
    note_type: noteType,
  })
  return data.progress_note
}

export async function getProgressNotes(caseId) {
  try {
    const { data } = await client.get(`/progress/cases/${caseId}/progress`)
    return data.progress_notes || []
  } catch (err) {
    // Progress notes may not exist yet, or lawyer may not be assigned
    // Return empty array gracefully
    if (err.response?.status === 403 || err.response?.status === 404) {
      return []
    }
    throw err
  }
}
