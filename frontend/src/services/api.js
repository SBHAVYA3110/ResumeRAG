/**
 * API Client Service for ResumeRAG Backend.
 * Encapsulates all HTTP communication with the FastAPI endpoints.
 */

const API_BASE = '/api';

/**
 * Helper to handle fetch responses and extract meaningful error messages.
 */
async function handleResponse(response) {
  if (!response.ok) {
    let errorDetail = `Request failed with status ${response.status}`;
    try {
      const errorJson = await response.json();
      if (errorJson.detail) {
        errorDetail = errorJson.detail;
      }
    } catch {
      // Non-JSON response
    }
    throw new Error(errorDetail);
  }
  return response.json();
}

export const api = {
  /**
   * Health check to test backend connectivity.
   */
  async checkHealth() {
    return handleResponse(await fetch(`${API_BASE}/health`));
  },

  /**
   * Upload a PDF file to the backend for text extraction, chunking, and ChromaDB indexing.
   * @param {File} file - The PDF file object from an <input> or dropzone.
   */
  async uploadDocument(file) {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${API_BASE}/documents/upload`, {
      method: 'POST',
      body: formData,
    });
    return handleResponse(response);
  },

  /**
   * Fetch list of all ingested documents from the relational database.
   */
  async listDocuments() {
    return handleResponse(await fetch(`${API_BASE}/documents`));
  },

  /**
   * Delete a document and its indexed vector chunks.
   * @param {string} filename - The name of the file to remove.
   */
  async deleteDocument(filename) {
    const response = await fetch(`${API_BASE}/documents/${encodeURIComponent(filename)}`, {
      method: 'DELETE',
    });
    return handleResponse(response);
  },

  /**
   * Ask a question grounded in the uploaded documents.
   * @param {string} query - The user's question.
   * @param {string|null} documentFilter - Optional document to restrict context to.
   * @param {number} nResults - Number of chunks to retrieve (default: 4).
   */
  async askQuestion(query, documentFilter = null, nResults = 4) {
    const response = await fetch(`${API_BASE}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        query,
        document_filter: documentFilter || null,
        n_results: nResults,
      }),
    });
    return handleResponse(response);
  },

  /**
   * Compare an uploaded resume against a job description.
   * @param {string} resumeFilename - Filename of the uploaded resume.
   * @param {string} jobFilename - Filename of the uploaded job description.
   */
  async compareResumeAndJob(resumeFilename, jobFilename) {
    const response = await fetch(`${API_BASE}/match`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        resume_filename: resumeFilename,
        job_filename: jobFilename,
      }),
    });
    return handleResponse(response);
  },

  /**
   * Retrieve historical skill match comparison reports.
   */
  async getMatchHistory(limit = 10) {
    return handleResponse(await fetch(`${API_BASE}/history/matches?limit=${limit}`));
  },

  /**
   * Retrieve past chat conversation messages and citations.
   */
  async getChatHistory(limit = 25) {
    return handleResponse(await fetch(`${API_BASE}/history/chat?limit=${limit}`));
  },
};
